"""Outil generate_part : paramètres -> design_id, STEP, STL, masse, encombrement."""

from __future__ import annotations

import ctypes
import os
import sys
from contextlib import contextmanager

from ..cad import arm
from ..spec import load_spec, short_hash
from ..store import design_dir, read_json, write_json
from .base import tool


@contextmanager
def quiet_stdout():
    sys.stdout.flush()
    saved = os.dup(1)
    devnull = os.open(os.devnull, os.O_WRONLY)
    try:
        os.dup2(devnull, 1)
        yield
    finally:
        ctypes.CDLL(None).fflush(None)  # vide le tampon C/C++ avant de rétablir la sortie
        os.dup2(saved, 1)
        os.close(saved)
        os.close(devnull)


def design_id_for(part: str, params: dict, spec: dict) -> str:
    key = {"part": part, "params": params, "interfaces": spec["interfaces"]}
    return f"{part}-{short_hash(key)}"


def layout_for(params: dict, spec: dict) -> arm.ArmLayout:
    return arm.ArmLayout(
        params=params,
        interfaces=spec["interfaces"],
        min_pad_thickness=spec["manufacturing"]["pad_min_thickness_mm"],
    )


@tool
def generate_part(part: str, params: dict) -> dict:
    if part != arm.PART:
        return {"ok": False, "valid": False, "reason": f"pièce non disponible : {part} (disponible : arm)"}
    spec = load_spec()
    params = arm.normalize_params(params)
    material = spec["materials"].get(params["material"])
    if material is None:
        return {"ok": False, "valid": False, "reason": f"matériau inconnu : {params['material']}"}
    design_id = design_id_for(part, params, spec)
    folder = design_dir(design_id)
    cached = read_json(folder / "part.json")
    if cached:
        return {**cached, "cached": True}

    import gmsh

    layout = layout_for(params, spec)
    gmsh.initialize(interruptible=False)
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        gmsh.model.add(design_id)
        volumes = arm.build_geometry(layout)
        if len(volumes) != 1:
            return {"ok": False, "valid": False, "design_id": design_id,
                    "reason": f"géométrie en {len(volumes)} morceaux au lieu d'un solide"}
        volume_mm3 = gmsh.model.occ.getMass(3, volumes[0][1])
        xmin, ymin, zmin, xmax, ymax, zmax = gmsh.model.getBoundingBox(3, volumes[0][1])
        with quiet_stdout():  # OpenCASCADE écrit sa trace STEP sur la sortie standard
            gmsh.write(str(folder / "part.step"))
        gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 24)
        gmsh.option.setNumber("Mesh.MeshSizeMax", 2.0)
        gmsh.option.setNumber("Mesh.Binary", 1)
        gmsh.model.mesh.generate(2)
        gmsh.write(str(folder / "part.stl"))
    finally:
        gmsh.finalize()

    result = {
        "ok": True,
        "valid": True,
        "design_id": design_id,
        "part": part,
        "params": params,
        "mass_g": round(volume_mm3 * material["density_g_cm3"] / 1000.0, 2),
        "volume_mm3": round(volume_mm3, 1),
        "bbox_mm": [round(xmax - xmin, 2), round(ymax - ymin, 2), round(zmax - zmin, 2)],
        "step": str(folder / "part.step"),
        "stl": str(folder / "part.stl"),
    }
    write_json(folder / "part.json", result)
    return result
