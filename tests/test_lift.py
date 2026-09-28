"""Tests de l'épreuve simulée et du vérificateur (parcours raccourci pour la vitesse)."""

from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def loose_exam(monkeypatch):
    """Le drone de test est écrit à la main : on lève ici l'obligation de dossier compilé (épreuve v3)."""
    import copy

    from drone_agent.lift import exam

    spec = copy.deepcopy(exam.exam_spec())
    spec["plausibility"]["require_compiled"] = False
    monkeypatch.setattr(exam, "exam_spec", lambda: spec)

from drone_agent.lift.exam import check_package, exam_spec, load_package, run_exam

FIXTURE = Path(__file__).parent / "fixtures" / "lift_quad"  # drone de test, jamais fourni à l'agent


@pytest.fixture
def short_spec():
    from drone_agent.lift import exam

    spec = copy.deepcopy(exam.exam_spec())
    spec["rules"]["loaded_distance_m"] = 120
    spec["rules"]["unloaded_distance_m"] = 60
    spec["rules"]["cruise_altitude_m"] = 15
    return spec


def test_package_check_reports_structure_and_plausibility():
    xml, design = load_package(FIXTURE)
    from drone_agent.lift import exam

    report = check_package(xml, design, exam.exam_spec())
    assert report["ok"] and report["aircraft_mass_kg"] == pytest.approx(20.44)
    assert report["thrust_to_weight_empty"] > 3
    greedy = {**design, "rotors": [{**r, "motor_max_power_w": 40000} for r in design["rotors"]]}
    assert any("W/kg" in i for i in check_package(xml, greedy)["issues"])
    no_site = xml.replace('name="payload_attach"', 'name="hook"')
    assert any("payload_attach" in i for i in check_package(no_site, design)["issues"])


def test_exam_flies_and_logs_telemetry(short_spec):
    xml, design = load_package(FIXTURE)
    result = run_exam(xml, design, 25.0, spec=short_spec)
    assert result["passed"], result["failure"]
    assert result["payload_kg"] == pytest.approx(55 * 0.45359237, abs=1e-3)  # multiple de 2,5 lb inférieur
    rows = result["telemetry_csv"].splitlines()
    assert rows[0].startswith("t,phase,x") and len(rows) > 100
    assert {"climb", "cruise_loaded", "hover_drop", "cruise_empty", "descent"} <= set(result["phases"])
    assert result["score"] < 0  # parcours réussi mais charge non qualifiante (< 110 lb)


def test_exam_detects_battery_depletion(short_spec):
    xml, design = load_package(FIXTURE)
    tiny = {**design, "battery": {**design["battery"], "energy_wh": 60, "max_power_w": 1200}}
    result = run_exam(xml, tiny, 20.0, spec=short_spec)
    assert not result["passed"]
    assert result["failure"]["context"]["battery_power_limited"] or result["failure"]["reason"] == "batterie épuisée"
    assert -1 < result["score"] < 0


def test_auditor_sees_what_the_engineer_did(tmp_path, monkeypatch):
    monkeypatch.delenv("DRONE_AGENT_NOTIFY_TARGET", raising=False)
    from drone_agent.agent import toolbox

    toolbox.init("lift_challenge", tmp_path / "lift")
    shutil.copytree(FIXTURE, tmp_path / "lift" / "workspace" / "designs" / "quad")
    ws = toolbox._ws()
    state = ws.state()
    state["cycle"] = 1
    ws.save_state(state)
    assert toolbox.check_design("designs/quad")["ok"]
    assert toolbox.check_design("../../outside")["ok"] is False  # hors de l'espace de travail
    toolbox.notebook_write(hypothesis="h", tests="check_design", result="masse 18,4 kg", conclusion="c", next_step="n")
    evidence = toolbox.cycle_evidence(1)
    assert evidence["notebook"][0]["result"] == "masse 18,4 kg"
    assert any('"check_design"' in call for call in evidence["tool_calls"])
    assert toolbox.record_audit(1, "peut-être", "x")["ok"] is False
    assert toolbox.record_audit(1, "ok", "Masse confirmée par check_design.")["ok"]
    assert ws.audits()[-1]["verdict"] == "ok"
    names = [fn.__name__ for fn in toolbox.tools_for("auditor", "lift_challenge")]
    assert "record_audit" in names and "run_exam" not in names and "decide_proposal" not in names


def test_v2_rules_catch_the_audited_exploits():
    """Failles relevées par l'audit du 28/09 : hélices qui se chevauchent, pièces manquantes, batterie optimiste,
    bras faibles, marge de poussée."""
    xml, design = load_package(FIXTURE)
    close = xml
    for i in range(4):  # rapproche les rotors : bras de 0,9 m -> 0,6 m (hélices de 1 m qui se chevauchent)
        close = close.replace(f'name="rotor_{i}" pos="', f'name="rotor_{i}" data-old="')
    import re
    close = re.sub(r'<site name="rotor_(\d)" data-old="([-\d.]+) ([-\d.]+) ([-\d.]+)"/>',
                   lambda m: f'<site name="rotor_{m[1]}" pos="{float(m[2]) * 0.6:.4f} {float(m[3]) * 0.6:.4f} {m[4]}"/>', close)
    assert any("se chevauchent" in i for i in check_package(close, design)["issues"])

    no_esc = re.sub(r'\s*<geom name="esc_\d"[^>]*/>', "", xml)
    assert any("« esc »" in i for i in check_package(no_esc, design)["issues"])

    dense = {**design, "battery": {**design["battery"], "energy_wh": 1800, "max_power_w": 9000}}  # 300 Wh/kg
    assert any("Wh/kg" in i for i in check_package(xml, dense)["issues"])
    fast = {**design, "battery": {**design["battery"], "energy_wh": 1500, "max_power_w": 15000}}  # 250 Wh/kg, 10 C
    assert any("C pour un pack" in i for i in check_package(xml, fast)["issues"])

    thin = {**design, "structure": {**design["structure"], "arm_tube_od_m": 0.012, "arm_tube_wall_m": 0.0008}}
    assert any("bras trop faibles" in i for i in check_package(xml, thin)["issues"])

    report = check_package(xml, design, payload_kg=50.0)
    assert not report["ok"] and any("marge de poussée" in i for i in report["issues"])


def test_coaxial_pair_is_allowed_but_penalised():
    xml, design = load_package(FIXTURE)
    report = check_package(xml, design)
    assert not any(r["coaxial"] for r in report["rotors"])


def test_scenarios_and_motor_heating(short_spec):
    xml, design = load_package(FIXTURE)
    calm = run_exam(xml, design, 20.0, spec=short_spec)
    hot = run_exam(xml, design, 20.0, spec=short_spec, scenario="chaleur")
    windy = run_exam(xml, design, 20.0, spec=short_spec, scenario="vent")
    assert calm["scenario"] == "nominal" and calm["score"] is not None
    assert hot["score"] is None and hot["scenario_score"] is not None  # banc d'essai hors score
    assert calm["ambient_c"] < calm["max_motor_temp_c"] < 150
    assert hot["max_motor_temp_c"] > calm["max_motor_temp_c"]
    assert hot["energy_used_wh"] > calm["energy_used_wh"]  # air moins dense : plus de puissance
    assert windy["passed"] and "motor_temp_max_c" in windy["telemetry_csv"].splitlines()[0]
    assert run_exam(xml, design, 20.0, spec=short_spec, scenario="tempête")["ok"] is False
