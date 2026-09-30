"""Atelier de l'épreuve v3 : catalogue sourcé, pièces sur mesure (CAO, FEM, thermique), assemblage compilé.

Le drone assemblé ici est une fixture de test, jamais fournie à l'agent. Calculs FEM en local (pas de SSH).
"""

from __future__ import annotations

import copy
import json
import math

import pytest

from drone_agent.lift import assembly, catalog, parts
from drone_agent.lift.exam import check_package, exam_spec, load_assets, run_exam

OK_PAGE = lambda url: {"reachable": True, "status": 200, "text": "fiche technique 0.7 kg 3000 W"}
R = 0.62  # rayon des rotors (m)

CATALOG = [
    ("motor", "M3000", "TestMotors", {"mass_kg": 0.7, "max_continuous_power_w": 3000, "diameter_m": 0.08, "height_m": 0.04,
                                      "mount_pattern_mm": 16, "max_prop_diameter_m": 0.82}),
    ("propeller", "P32", "TestProps", {"mass_kg": 0.18, "diameter_m": 0.8}),
    ("battery", "B1080", "TestCells", {"mass_kg": 6.0, "energy_wh": 1080, "max_continuous_power_w": 16000, "dims_m": [0.3, 0.15, 0.08]}),
    ("esc", "E80", "TestESC", {"mass_kg": 0.25, "max_continuous_power_w": 3500, "dims_m": [0.08, 0.04, 0.02]}),
    ("tube", "T30", "TestTubes", {"mass_per_m_kg": 0.215, "outer_diameter_m": 0.03, "wall_m": 0.0015, "material": "CFRP"}),
    ("avionics", "FC", "TestFC", {"mass_kg": 0.5, "dims_m": [0.1, 0.1, 0.04]}),
    ("wiring", "AWG10", "TestCable", {"mass_per_m_kg": 0.1}),
    ("landing_gear", "G1", "TestGear", {"mass_kg": 1.0, "dims_m": [0.5, 0.5, 0.3]}),
]


def _ids(root):
    return {e["category"]: e["id"] for e in catalog.entries(root).values()}


def _write_part(root, name, script, spec):
    folder = root / "workspace" / "parts" / name
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "part.py").write_text(script, encoding="utf-8")
    (folder / "part.json").write_text(json.dumps(spec), encoding="utf-8")


@pytest.fixture
def lab(tmp_path, monkeypatch):
    monkeypatch.setenv("DRONE_AGENT_REMOTE", "0")
    root = tmp_path / "lift"
    for category, name, maker, specs in CATALOG:
        assert catalog.add(root, category, name, maker, specs, f"https://example.org/{name}", "Fiche : masse et puissance 0.7 kg 3000 W",
                           url_checker=OK_PAGE)["ok"]
    _write_part(root, "hub", "def build(occ):\n    occ.addBox(-150, -150, -3, 300, 300, 6)\n",
                {"material": "AL6061-T6", "process": "cnc", "role": "frame", "interfaces": [],
                 "load_cases": [{"name": "bras", "fixed_box_mm": [-40, -40, -4, 40, 40, 4], "load_box_mm": [130, -150, -4, 150, 150, 4],
                                 "force_n": [0, 0, 150]}]})
    _write_part(root, "mount",
                "def build(occ):\n    plate = occ.addBox(-30, -30, 0, 60, 60, 5)\n    boss = occ.addCylinder(-45, 0, -12, 90, 0, 0, 18)\n"
                "    body, _ = occ.fuse([(3, plate)], [(3, boss)])\n    occ.cut(body, [(3, occ.addCylinder(-46, 0, -12, 92, 0, 0, 15.1))])\n",
                {"material": "AL6061-T6", "process": "cnc", "role": "mount",
                 "interfaces": [{"name": "tube", "type": "tube_socket", "params": {"tube_od_m": 0.03}},
                                {"name": "motor", "type": "motor_bolts", "params": {"pattern_mm": 16}}],
                 "load_cases": [{"name": "poussee", "fixed_box_mm": [-46, -19, -31, 46, 19, -8], "load_box_mm": [-30, -30, 4.9, 30, 30, 5.1],
                                 "force_n": [0, 0, 200]}], "heat": {"heat_w": 10}})
    for name, case in (("hub", "bras"), ("mount", "poussee")):
        assert parts.build(root, name)["ok"]
        assert parts.fem(root, name, case)["sf_ok"]
    return root


def _assembly(root, stagger=None, radius=R):
    ids = _ids(root)
    inst, rotors, cons = [], [], []
    for i in range(4):
        a = math.pi / 4 + i * math.pi / 2
        c, s = math.cos(a), math.sin(a)
        z = (stagger if i % 2 else 0.0) if stagger else 0.0
        inst += [
            {"id": f"arm{i}", "ref": f"catalog:{ids['tube']}", "fromto_m": [0.12 * c, 0.12 * s, 0, (radius - 0.03) * c, (radius - 0.03) * s, 0]},
            {"id": f"mount{i}", "ref": "part:mount", "pos_m": [radius * c, radius * s, 0.012], "euler_deg": [0, 0, math.degrees(a)]},
            {"id": f"m{i}", "ref": f"catalog:{ids['motor']}", "pos_m": [radius * c, radius * s, 0.04 + z]},
            {"id": f"p{i}", "ref": f"catalog:{ids['propeller']}", "pos_m": [radius * c, radius * s, 0.07 + z]},
            {"id": f"esc{i}", "ref": f"catalog:{ids['esc']}", "pos_m": [0.35 * c, 0.35 * s, -0.03]},
        ]
        rotors.append({"prop": f"p{i}", "motor": f"m{i}", "spin": 1 if i % 2 == 0 else -1})
        cons += [{"a": f"arm{i}", "b": f"mount{i}", "interface": "tube"}, {"a": f"m{i}", "b": f"mount{i}", "interface": "motor"}]
    inst += [{"id": "hub", "ref": "part:hub", "pos_m": [0, 0, 0]},
             {"id": "bat", "ref": f"catalog:{ids['battery']}", "pos_m": [0, 0, 0.05]},
             {"id": "fc", "ref": f"catalog:{ids['avionics']}", "pos_m": [0, 0, 0.12]},
             {"id": "cables", "ref": f"catalog:{ids['wiring']}", "length_m": 3, "pos_m": [0, 0, -0.02]},
             {"id": "gear", "ref": f"catalog:{ids['landing_gear']}", "pos_m": [0, 0, -0.2]}]
    folder = root / "workspace" / "assemblies" / "quad"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "assembly.json").write_text(json.dumps({"hub_radius_m": 0.12, "cruise_speed_m_s": 12,
                                                      "payload_attach_m": [0, 0, -0.4], "instances": inst,
                                                      "rotors": rotors, "connections": cons}), encoding="utf-8")


def test_catalog_rejects_unsourced_or_implausible_parts(tmp_path):
    root = tmp_path / "lift"
    dead = lambda url: {"reachable": False, "status": 404, "reason": "HTTP 404"}
    motor = {"mass_kg": 1.1, "max_continuous_power_w": 5500, "diameter_m": 0.1, "height_m": 0.05, "mount_pattern_mm": 25}
    out = catalog.add(root, "motor", "U15", "T-Motor", motor, "https://store.example.com/p/618", "Weight 1100 g, 5500 W", url_checker=dead)
    assert not out["ok"] and any("inaccessible" in i for i in out["issues"])
    home = catalog.check_url("https://www.tattu.com/")
    assert not home["reachable"] and "accueil" in home["reason"]
    greedy = {**motor, "max_continuous_power_w": 9000}
    assert any("W/kg" in i for i in catalog.add(root, "motor", "X", "Y", greedy, "https://e.org/x", "x" * 25, url_checker=OK_PAGE)["issues"])
    dense = {"mass_kg": 10, "energy_wh": 3000, "max_continuous_power_w": 20000, "dims_m": [0.3, 0.2, 0.1]}
    assert any("Wh/kg" in i for i in catalog.add(root, "battery", "B", "Y", dense, "https://e.org/b", "x" * 25, url_checker=OK_PAGE)["issues"])


def test_part_thermal_estimate_favours_aluminium(lab):
    folder = lab / "workspace" / "parts" / "mount"
    spec = json.loads((folder / "part.json").read_text())
    spec.update(material="PA12-CF", process="fdm", heat={"heat_w": 30})
    (folder / "part.json").write_text(json.dumps(spec))
    plastic = parts.build(lab, "mount")
    assert not plastic["ok"] and any("thermique" in i for i in plastic["issues"])
    spec.update(material="AL6061-T6", process="cnc")
    (folder / "part.json").write_text(json.dumps(spec))
    metal = parts.build(lab, "mount")
    assert metal["ok"] and metal["mass_kg"] > plastic["mass_kg"]
    assert metal["fem_done"]["poussee"]["up_to_date"] is False  # la pièce a changé : recalcul requis


def test_assembly_compiles_with_computed_masses_and_flies(lab):
    _assembly(lab)
    report = assembly.compile_assembly(lab, "quad")
    assert report["ok"], report["issues"]
    masses = report["masses_by_family_kg"]
    assert masses["motor"] == pytest.approx(2.8) and masses["battery"] == pytest.approx(6.0)
    assert masses["frame"] > 0.9  # moyeu + supports usinés, masses issues de la CAO
    assert report["image"] and report["usda"].endswith(".usda")
    assert len(report["resonance"]) == 4 and all(r["f1_hz"] > 0 for r in report["resonance"])
    design_dir = lab / "workspace" / "designs" / "quad"
    xml = (design_dir / "drone.xml").read_text()
    design = json.loads((design_dir / "design.json").read_text())
    spec = copy.deepcopy(exam_spec())
    spec["rules"].update(loaded_distance_m=120, unloaded_distance_m=60, cruise_altitude_m=15)
    assets = load_assets(design_dir)
    assert assets and all(name.startswith("meshes/") for name in assets)  # chemins relatifs, transportables
    assert "/workspace/parts/" not in xml
    result = run_exam(xml, design, 10.0, spec=spec, assets=assets)
    assert result["passed"], result["failure"]

    tampered = xml.replace('mass="6.00000"', 'mass="4.00000"')
    assert any("non compilé" in i for i in check_package(tampered, design, assets=assets)["issues"])


def test_assembly_checks_interfaces_and_part_validation(lab):
    _assembly(lab)
    asm_file = lab / "workspace" / "assemblies" / "quad" / "assembly.json"
    asm = json.loads(asm_file.read_text())
    asm["instances"][0]["ref"] = "catalog:tube:inconnu"
    asm_file.write_text(json.dumps(asm))
    assert any("inconnue" in i for i in assembly.compile_assembly(lab, "quad")["issues"])
    _assembly(lab)
    spec_file = lab / "workspace" / "parts" / "mount" / "part.json"
    spec = json.loads(spec_file.read_text())
    spec["interfaces"][0]["params"]["tube_od_m"] = 0.025
    spec_file.write_text(json.dumps(spec))
    parts.build(lab, "mount")
    issues = assembly.compile_assembly(lab, "quad")["issues"]
    assert any("non calculé" in i for i in issues)  # pièce modifiée : FEM à refaire


def test_staggered_propellers_are_allowed_with_a_power_penalty(lab):
    _assembly(lab, radius=0.5)  # hélices de 0,8 m trop proches, même plan : refusé
    flat = assembly.compile_assembly(lab, "quad")
    assert not flat["ok"] and any("même plan" in i for i in flat["issues"])
    _assembly(lab, radius=0.5, stagger=0.12)  # une hélice sur deux surélevée de 12 cm
    staggered = assembly.compile_assembly(lab, "quad")
    assert not any("chevauchent" in i for i in staggered["issues"])
    factors = [r["power_factor"] for r in staggered["rotors"]]
    assert all(1.0 < f < 1.4 for f in factors)
