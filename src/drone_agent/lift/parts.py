"""Atelier de pièces sur mesure : CAO par script (Gmsh/OpenCASCADE), propriétés, fabrication, thermique.

Une pièce = un dossier workspace/parts/<nom>/ :
  part.py    définit build(occ) : crée des solides avec l'API gmsh.model.occ, unités en millimètres
  part.json  {"material", "process", "role", "interfaces": [...], "load_cases": [...], "heat": {...}}
Le calcul par éléments finis est dans partfem.py (exécuté sur la RTX 5090).
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import subprocess
import sys
from pathlib import Path

from ..spec import REPO_ROOT, load_spec

MATERIALS_PATH = REPO_ROOT / "spec" / "materials.yaml"
ROLES = ("frame", "mount", "gear", "payload", "other")

BUILD_SCRIPT = r'''
import json, sys, runpy
import gmsh
part_dir = sys.argv[1]
gmsh.initialize(interruptible=False)
gmsh.option.setNumber("General.Terminal", 0)
gmsh.model.add("part")
module = runpy.run_path(part_dir + "/part.py")
if "build" not in module:
    raise SystemExit("part.py doit définir build(occ)")
module["build"](gmsh.model.occ)
occ = gmsh.model.occ
occ.synchronize()
vols = gmsh.model.getEntities(3)
if not vols:
    raise SystemExit("aucun solide créé")
if len(vols) > 1:
    occ.fuse([vols[0]], vols[1:])
    occ.synchronize()
    vols = gmsh.model.getEntities(3)
volume = sum(occ.getMass(3, v[1]) for v in vols)
com = occ.getCenterOfMass(3, vols[0][1]) if len(vols) == 1 else [0, 0, 0]
inertia = occ.getMatrixOfInertia(3, vols[0][1]) if len(vols) == 1 else [0] * 9
area = sum(occ.getMass(2, s[1]) for s in gmsh.model.getEntities(2))
box = gmsh.model.getBoundingBox(-1, -1)
gmsh.write(part_dir + "/part.step")
gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 20)
gmsh.option.setNumber("Mesh.MeshSizeMax", 4.0)
gmsh.option.setNumber("Mesh.Binary", 1)
gmsh.model.mesh.generate(2)
gmsh.write(part_dir + "/part.stl")
gmsh.finalize()
print("PROPS_JSON " + json.dumps({"solids": len(vols), "volume_mm3": volume, "area_mm2": area, "com_mm": list(com),
                                  "inertia_mm5": list(inertia), "bbox_mm": list(box)}))
'''


def materials() -> dict:
    return load_spec(MATERIALS_PATH)


def part_hash(part_dir: Path) -> str:
    h = hashlib.sha1()
    for name in ("part.py", "part.json"):
        h.update((part_dir / name).read_bytes())
    return h.hexdigest()[:10]


def resolve_part(root: Path, name: str) -> Path:
    base = (root / "workspace" / "parts").resolve()
    base.mkdir(parents=True, exist_ok=True)
    path = (base / name).resolve()
    if base not in path.parents:
        raise ValueError("la pièce doit être dans workspace/parts/")
    if not (path / "part.py").exists() or not (path / "part.json").exists():
        raise FileNotFoundError(f"part.py et part.json attendus dans {path}")
    return path


def build(root: Path, name: str) -> dict:
    path = resolve_part(root, name)
    spec = json.loads((path / "part.json").read_text(encoding="utf-8"))
    lib = materials()
    issues = []
    material = lib["materials"].get(spec.get("material"))
    process = lib["processes"].get(spec.get("process"))
    if material is None:
        issues.append(f"matériau inconnu : {spec.get('material')} (disponibles : {sorted(lib['materials'])})")
    if process is None:
        issues.append(f"procédé inconnu : {spec.get('process')} (disponibles : {sorted(lib['processes'])})")
    if material and process and spec["process"] not in material["processes"]:
        issues.append(f"{spec['material']} ne se met pas en œuvre par {spec['process']}")
    if spec.get("role") not in ROLES:
        issues.append(f"role parmi {ROLES}")
    if not spec.get("load_cases"):
        issues.append("au moins un cas de charge (load_cases) pour dimensionner la pièce")
    proc = subprocess.run([sys.executable, "-c", BUILD_SCRIPT, str(path)], capture_output=True, text=True, timeout=300)
    line = next((l for l in reversed(proc.stdout.splitlines()) if l.startswith("PROPS_JSON ")), None)
    if line is None:
        return {"ok": False, "part": name, "issues": issues + [f"script CAO en erreur : {(proc.stderr or proc.stdout)[-600:]}"]}
    props = json.loads(line[len("PROPS_JSON "):])
    xmin, ymin, zmin, xmax, ymax, zmax = props["bbox_mm"]
    size = sorted([xmax - xmin, ymax - ymin, zmax - zmin])
    report = {"ok": False, "part": name, "hash": part_hash(path), "material": spec.get("material"),
              "process": spec.get("process"), "role": spec.get("role"), "size_mm": [round(v, 1) for v in size],
              "volume_cm3": round(props["volume_mm3"] / 1000, 2), "com_mm": [round(v, 2) for v in props["com_mm"]]}
    if material and process:
        mass = props["volume_mm3"] * 1e-9 * material["density_kg_m3"]
        report["mass_kg"] = round(mass, 4)
        if any(a > b + 0.5 for a, b in zip(size, sorted(process["build_volume_mm"]))):  # dimensions triées, tolérance 0,5 mm
            issues.append(f"hors volume de fabrication {process['build_volume_mm']} mm pour {spec['process']}")
        heat = spec.get("heat") or {}
        if heat.get("heat_w"):
            # Modèle d'ailette : la chaleur conduite dans la pièce s'évacue par sa surface, avec une efficacité
            # d'ailette qui dépend de la conductivité et de l'épaisseur caractéristique (volume / surface × 2).
            rules = lib["design_rules"]
            h = rules["film_coefficient_w_m2k"]
            area = props["area_mm2"] * 1e-6
            thickness = max(2 * props["volume_mm3"] / max(props["area_mm2"], 1e-9) * 1e-3, 1e-4)
            fin_length = max(size) / 2 / 1000
            m = math.sqrt(2 * h / (material["thermal_conductivity"] * thickness))
            efficiency = math.tanh(m * fin_length) / (m * fin_length)
            temp = rules["ambient_c"] + heat["heat_w"] / (h * area * efficiency)
            report["thermal"] = {"heat_w": heat["heat_w"], "fin_efficiency": round(efficiency, 3),
                                 "estimated_interface_temp_c": round(temp, 1),
                                 "max_service_temp_c": material["max_service_temp_c"],
                                 "method": "modèle d'ailette (convection h = %d W/m²K), ordre de grandeur" % h}
            if temp > material["max_service_temp_c"]:
                issues.append(f"thermique : ~{temp:.0f} °C estimés à l'interface > {material['max_service_temp_c']} °C "
                              f"admissibles pour {spec['material']}")
    report["issues"] = issues
    report["ok"] = not issues
    report["fem_required"] = [c.get("name") for c in spec.get("load_cases", [])]
    report["fem_done"] = fem_status(path, report["hash"])
    report["image"] = render_part(path)
    (path / "build.json").write_text(json.dumps({**report, **props}, indent=2, ensure_ascii=False), encoding="utf-8")
    return report


def fem_status(path: Path, current_hash: str) -> dict:
    status = {}
    for f in path.glob("fem-*.json"):
        r = json.loads(f.read_text())
        status[r.get("load_case")] = {"sf": r.get("sf"), "ok": r.get("sf_ok"), "up_to_date": r.get("part_hash") == current_hash}
    return status


def render_part(path: Path) -> str | None:
    """Image de la pièce (maillage STL rendu par MuJoCo, EGL)."""
    xml = f"""<mujoco><asset><mesh name="p" file="{path / 'part.stl'}" scale="0.001 0.001 0.001"/>
    <texture name="sky" type="skybox" builtin="gradient" rgb1="1 1 1" rgb2=".82 .86 .9" width="32" height="32"/></asset>
    <visual><global offwidth="800" offheight="600"/><headlight ambient=".35 .35 .35"/></visual>
    <worldbody><light pos="0.3 -0.3 0.6" dir="-0.4 0.4 -1"/><light pos="-0.3 0.3 0.6" dir="0.4 -0.4 -1"/>
    <geom type="mesh" mesh="p" rgba=".55 .6 .7 1"/></worldbody></mujoco>"""
    (path / "view.xml").write_text(xml, encoding="utf-8")
    code = ("import mujoco, sys; from PIL import Image; m = mujoco.MjModel.from_xml_path(sys.argv[1]); d = mujoco.MjData(m); "
            "mujoco.mj_forward(m, d); r = mujoco.Renderer(m, 600, 800); c = mujoco.MjvCamera(); "
            "c.lookat[:] = d.geom_xpos[0]; c.distance = 3.2 * m.geom_rbound[0]; c.elevation = -30; c.azimuth = 135; "
            "r.update_scene(d, c); Image.fromarray(r.render()).save(sys.argv[2])")
    from .gl import run_render

    out = path / "view.png"
    out.unlink(missing_ok=True)
    run_render([sys.executable, "-c", code, str(path / "view.xml"), str(out)], out, timeout=120)
    return str(out) if out.exists() else None


def fem(root: Path, name: str, load_case: str) -> dict:
    from ..remote import run_module

    path = resolve_part(root, name)
    spec = json.loads((path / "part.json").read_text(encoding="utf-8"))
    built = json.loads((path / "build.json").read_text()) if (path / "build.json").exists() else None
    current = part_hash(path)
    if not built or built.get("hash") != current:
        return {"ok": False, "reason": "reconstruire la pièce (part_build) avant le calcul"}
    case = next((c for c in spec.get("load_cases", []) if c.get("name") == load_case), None)
    if case is None:
        return {"ok": False, "reason": f"cas inconnu ; cas déclarés : {[c.get('name') for c in spec.get('load_cases', [])]}"}
    lib = materials()
    material, process = lib["materials"][spec["material"]], lib["processes"][spec["process"]]
    job = {"step": (path / "part.step").read_text(encoding="utf-8", errors="replace"),
           "young_mpa": material["young_gpa"] * 1000, "poisson": 0.33, "fixed_box_mm": case["fixed_box_mm"],
           "load_box_mm": case["load_box_mm"], "force_n": case["force_n"], "mesh_mm": case.get("mesh_mm")}
    result = run_module("drone_agent.lift.partfem", job, timeout_s=900)
    if not result.get("ok"):
        return {"ok": False, "reason": result.get("reason"), "ran_on": result.get("ran_on")}
    usable = material["strength_mpa"] * process["strength_knockdown"]
    sf = usable / result["von_mises_max_mpa"] if result["von_mises_max_mpa"] > 0 else None
    required = lib["design_rules"]["safety_factor_min"]
    out = {"ok": True, "part": name, "load_case": load_case, "part_hash": current, **result,
           "usable_strength_mpa": round(usable, 1), "sf": round(sf, 2) if sf else None,
           "sf_required": required, "sf_ok": bool(sf and sf >= required)}
    (path / f"fem-{load_case}.json").write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    return out
