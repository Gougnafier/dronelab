"""Tests des outils sans LLM. Les tests marqués « fem » lancent Gmsh et CalculiX (~40 s)."""

from __future__ import annotations

import math
import shutil

import pytest

from drone_agent.fem import calculix
from drone_agent.spec import load_spec

REFERENCE = load_spec()["reference"]["params"]
needs_solver = pytest.mark.skipif(shutil.which("ccx") is None, reason="CalculiX absent")


@pytest.fixture(autouse=True)
def isolated_runs(tmp_path, monkeypatch):
    monkeypatch.setenv("DRONE_AGENT_RUNS", str(tmp_path / "runs"))
    return tmp_path / "runs"


def test_generate_part_rejects_interface_change_without_raising():
    from drone_agent.tools.generate_part import generate_part

    result = generate_part("arm", {**REFERENCE, "motor_pattern_mm": 19.0})
    assert result["ok"] is False and result["valid"] is False
    assert "interface" in result["reason"]


def test_unknown_design_and_case_return_invalid_results():
    from drone_agent.tools.run_fem import run_fem, run_modal

    assert run_fem("arm-inexistant", "max_thrust")["valid"] is False
    assert run_fem("arm-inexistant", "hover")["valid"] is False
    assert run_modal("arm-inexistant")["valid"] is False


def test_manufacturability_flags_thin_walls_between_holes():
    from drone_agent.tools.check_manufacturability import check_manufacturability
    from drone_agent.tools.generate_part import generate_part

    ok = generate_part("arm", REFERENCE)
    assert check_manufacturability(ok["design_id"])["manufacturable"] is True

    thin = generate_part("arm", {**REFERENCE, "thickness_mm": 1.0, "holes": 6, "hole_ratio": 0.8})
    report = check_manufacturability(thin["design_id"])
    assert report["manufacturable"] is False
    assert any("paroi mince" in v for v in report["violations"])


def test_design_id_is_stable_and_cached():
    from drone_agent.tools.generate_part import generate_part

    first = generate_part("arm", REFERENCE)
    second = generate_part("arm", dict(reversed(list(REFERENCE.items()))))
    assert first["design_id"] == second["design_id"]
    assert second.get("cached") is True


def test_parse_frequencies_uses_eigenvalues(tmp_path):
    dat = tmp_path / "case.dat"
    omega = 2 * math.pi * 100.0
    dat.write_text(
        "     E I G E N V A L U E   O U T P U T\n\n MODE NO    EIGENVALUE\n\n"
        f"      1   {omega**2:.6E}   {omega:.6E}   0.1000E+03   0.0000E+00\n\n",
        encoding="utf-8",
    )
    assert calculix.parse_frequencies(dat) == pytest.approx([100.0])


@needs_solver
def test_reference_arm_matches_beam_theory():
    """Section en U de la référence : I = 3000 mm^4, L = 110 mm, E = 2000 MPa -> 1,11 mm."""
    from drone_agent.tools.generate_part import generate_part
    from drone_agent.tools.run_fem import run_fem, run_modal

    spec = load_spec()
    design = generate_part("arm", REFERENCE)
    thrust = run_fem(design["design_id"], "max_thrust")
    assert thrust["valid"], thrust
    force = spec["load_cases"]["max_thrust"]["force_n"][2]
    length = spec["interfaces"]["arm_free_length_mm"]
    analytic = force * length**3 / (3 * spec["materials"]["PETG"]["young_mpa"] * 3000.0)
    assert thrust["deflection_mm"] == pytest.approx(analytic, rel=0.08)

    # Masse ponctuelle au bout d'un ressort de raideur F/flèche, masse du bras négligée à 25 %.
    modal = run_modal(design["design_id"])
    stiffness_n_m = force / (thrust["deflection_mm"] * 1e-3)
    moving_mass_kg = (spec["drone"]["motor_mass_g"] + 0.25 * design["mass_g"]) * 1e-3
    expected_hz = math.sqrt(stiffness_n_m / moving_mass_kg) / (2 * math.pi)
    assert modal["valid"], modal
    assert min(modal["modal_hz"]) == pytest.approx(expected_hz, rel=0.1)


@needs_solver
def test_solver_timeout_becomes_invalid_result(tmp_path):
    from drone_agent.tools.generate_part import generate_part
    from drone_agent.tools.run_fem import ensure_mesh
    from drone_agent.store import design_dir

    spec = load_spec()
    design = generate_part("arm", REFERENCE)
    mesh_info = ensure_mesh(design["design_id"])
    case_dir = design_dir(design["design_id"]) / "timeout"
    case_dir.mkdir()
    deck = calculix.case_deck("max_thrust", spec, spec["materials"]["PETG"], mesh_info)
    (case_dir / "case.inp").write_text(deck, encoding="ascii")
    result = calculix.run_ccx(case_dir, "case", timeout_s=0.05, threads=1)
    assert result["ok"] is False and "timeout" in result["reason"]
