"""Outils run_fem (statique) et run_modal (fréquences propres) via CalculiX."""

from __future__ import annotations

import math
import os
from pathlib import Path

from ..cad import arm
from ..fem import calculix
from ..spec import load_spec
from ..store import design_dir, read_json, write_json
from .base import tool
from .generate_part import layout_for


def mesh_size(params: dict, spec: dict) -> float:
    """Taille de maille : au plus la paroi la plus fine, bornée par la spec."""
    thin = [params["thickness_mm"]]
    if params["rib"]:
        thin.append(params["rib_width_mm"])
    return max(0.8, min(spec["solver"]["mesh_size_max_mm"], min(thin)))


def ensure_mesh(design_id: str) -> dict:
    folder = design_dir(design_id)
    info = read_json(folder / "mesh.json")
    if info and (folder / "mesh.inp").exists():
        return info
    part = read_json(folder / "part.json")
    if not part or not part.get("valid"):
        raise RuntimeError("design non généré")
    spec = load_spec()
    layout = layout_for(part["params"], spec)

    import gmsh

    gmsh.initialize(interruptible=False)
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        gmsh.model.add(design_id)
        arm.build_geometry(layout)
        size = mesh_size(part["params"], spec)
        gmsh.option.setNumber("Mesh.MeshSizeMax", size)
        gmsh.option.setNumber("Mesh.MeshSizeMin", size / 4)
        gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 12)
        gmsh.option.setNumber("Mesh.ElementOrder", spec["solver"]["mesh_order"])
        gmsh.option.setNumber("Mesh.SecondOrderLinear", 1)  # nœuds milieux sur les arêtes droites
        gmsh.option.setNumber("Mesh.Optimize", 1)
        gmsh.model.mesh.generate(3)
        info = arm.mesh_to_calculix(folder / "mesh.inp", layout, spec["stress_exclusion_band_mm"])
        info["mesh_size_mm"] = size
    finally:
        gmsh.finalize()
    write_json(folder / "mesh.json", info)
    return info


def _solve(design_id: str, case: str) -> tuple[dict, dict, dict]:
    spec = load_spec()
    folder = design_dir(design_id)
    part = read_json(folder / "part.json")
    if not part or not part.get("valid"):
        raise RuntimeError("design non généré")
    material = spec["materials"][part["params"]["material"]]
    mesh_info = ensure_mesh(design_id)
    case_dir = folder / case
    case_dir.mkdir(exist_ok=True)
    (case_dir / "case.inp").write_text(calculix.case_deck(case, spec, material, mesh_info), encoding="ascii")
    run = calculix.run_ccx(case_dir, "case", spec["solver"]["timeout_s"], spec["solver"]["threads"])
    return spec, material, {**run, "mesh_elements": mesh_info["elements"], "case_dir": case_dir}


def prune_fields(case_dir: Path) -> None:
    """Supprime les champs volumineux une fois lus (~80 Mo par design) sauf si DRONE_AGENT_KEEP_FIELDS=1.

    Le fichier case.inp reste : un rendu peut relancer le cas pour retrouver les champs.
    """
    if os.environ.get("DRONE_AGENT_KEEP_FIELDS") == "1":
        return
    for suffix in (".dat", ".frd", ".sta", ".cvg", ".12d"):
        (case_dir / f"case{suffix}").unlink(missing_ok=True)


@tool
def run_fem(design_id: str, load_case: str) -> dict:
    if load_case not in calculix.STATIC_CASES:
        return {"ok": False, "valid": False, "design_id": design_id,
                "reason": f"cas inconnu : {load_case} (disponibles : {list(calculix.STATIC_CASES)})"}
    cache = design_dir(design_id) / f"{load_case}.json"
    cached = read_json(cache)
    if cached:
        return {**cached, "cached": True}
    spec, material, run = _solve(design_id, load_case)
    base = {"design_id": design_id, "load_case": load_case, "solver_seconds": run["seconds"],
            "mesh_elements": run["mesh_elements"]}
    if not run["ok"]:
        return {**base, "ok": False, "valid": False, "reason": run["reason"]}
    parsed = calculix.parse_static_dat(run["case_dir"] / "case.dat")
    prune_fields(run["case_dir"])
    ref = parsed["displacements"].get("NREF", {})
    all_nodes = parsed["displacements"].get("NALL", {})
    if not ref or not all_nodes or parsed["von_mises_max_mpa"] <= 0:
        return {**base, "ok": False, "valid": False, "reason": "résultats absents du fichier .dat"}
    tip = ref[min(ref)]  # nœud de référence du moteur
    vm = parsed["von_mises_max_mpa"]
    result = {
        **base,
        "ok": True,
        "valid": True,
        "von_mises_max_mpa": round(vm, 3),
        "sf": round(material["strength_mpa"] / vm, 3),
        "tip_displacement_mm": [round(v, 4) for v in tip],
        "deflection_mm": round(abs(tip[2]), 4),
        "max_displacement_mm": round(max(math.sqrt(sum(c * c for c in u)) for u in all_nodes.values()), 4),
    }
    write_json(cache, result)
    return result


@tool
def run_modal(design_id: str) -> dict:
    cache = design_dir(design_id) / "modal.json"
    cached = read_json(cache)
    if cached:
        return {**cached, "cached": True}
    spec, _, run = _solve(design_id, "modal")
    base = {"design_id": design_id, "solver_seconds": run["seconds"], "mesh_elements": run["mesh_elements"]}
    if not run["ok"]:
        return {**base, "ok": False, "valid": False, "reason": run["reason"]}
    freqs = calculix.parse_frequencies(run["case_dir"] / "case.dat")
    prune_fields(run["case_dir"])
    modes = int(spec["load_cases"]["modal"]["modes"])
    if len(freqs) < modes:
        return {**base, "ok": False, "valid": False, "reason": f"{len(freqs)} fréquence(s) lue(s) sur {modes}"}
    result = {**base, "ok": True, "valid": True, "modal_hz": [round(f, 1) for f in freqs[:modes]]}
    write_json(cache, result)
    return result
