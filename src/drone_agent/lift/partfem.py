"""Calcul statique par éléments finis d'une pièce sur mesure (Gmsh + CalculiX), exécuté sur la RTX 5090.

Job JSON sur stdin : step (texte STEP, unités mm), young_mpa, poisson, fixed_box_mm, load_box_mm
([xmin, ymin, zmin, xmax, ymax, zmax] dans le repère de la pièce), force_n [Fx, Fy, Fz], mesh_mm (optionnel).
Sortie : RESULT_JSON avec contrainte de von Mises max (hors bande d'encastrement), déplacement max.
"""

from __future__ import annotations

import json
import math
import sys
import tempfile
import time
from pathlib import Path

import numpy as np

from ..fem import calculix


def _inside(xyz, box, tol=0.01):
    return (xyz[:, 0] >= box[0] - tol) & (xyz[:, 1] >= box[1] - tol) & (xyz[:, 2] >= box[2] - tol) & \
           (xyz[:, 0] <= box[3] + tol) & (xyz[:, 1] <= box[4] + tol) & (xyz[:, 2] <= box[5] + tol)


def solve(job: dict, timeout_s: float = 600, threads: int = 8) -> dict:
    import gmsh

    start = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="partfem-") as tmp:
        folder = Path(tmp)
        (folder / "part.step").write_text(job["step"], encoding="utf-8")
        gmsh.initialize(interruptible=False)
        try:
            gmsh.option.setNumber("General.Terminal", 0)
            gmsh.merge(str(folder / "part.step"))
            box = gmsh.model.getBoundingBox(-1, -1)
            diag = math.dist(box[:3], box[3:])
            size = job.get("mesh_mm") or min(4.0, max(0.8, diag / 45))
            gmsh.option.setNumber("Mesh.MeshSizeMax", size)
            gmsh.option.setNumber("Mesh.MeshSizeMin", size / 4)
            gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 12)
            gmsh.option.setNumber("Mesh.ElementOrder", 2)
            gmsh.option.setNumber("Mesh.SecondOrderLinear", 1)
            gmsh.model.mesh.generate(3)
            tags, coords, _ = gmsh.model.mesh.getNodes()
            types, _, nodes = gmsh.model.mesh.getElements(3)
        finally:
            gmsh.finalize()
        if 11 not in list(types):
            return {"ok": False, "reason": "maillage quadratique impossible"}
        tets = np.asarray(nodes[list(types).index(11)], dtype=np.int64).reshape(-1, 10)[:, [0, 1, 2, 3, 4, 5, 6, 7, 9, 8]]
        coords = coords.reshape(-1, 3)
        index = {int(t): i for i, t in enumerate(tags)}
        used = np.unique(tets)
        xyz = np.array([coords[index[int(n)]] for n in used])
        fixed = used[_inside(xyz, job["fixed_box_mm"])]
        loaded = used[_inside(xyz, job["load_box_mm"])]
        if len(fixed) == 0 or len(loaded) == 0:
            return {"ok": False, "reason": f"zones vides : {len(fixed)} nœuds encastrés, {len(loaded)} nœuds chargés ; "
                                           f"vérifier les boîtes (boîte englobante de la pièce : {[round(v, 1) for v in box]})"}
        x_of = {int(n): c for n, c in zip(used, xyz)}
        band = [b - 2 * size if k < 3 else b + 2 * size for k, b in enumerate(job["fixed_box_mm"])]
        centroids = np.array([np.mean([x_of[int(n)] for n in t[:4]], axis=0) for t in tets])
        keep = np.nonzero(~_inside(centroids, band, 0.0))[0] + 1
        if len(keep) == 0:
            keep = np.arange(1, len(tets) + 1)

        def ids(values):
            values = [int(v) for v in values]
            return "\n".join(", ".join(str(v) for v in values[k:k + 16]) for k in range(0, len(values), 16))

        lines = ["*NODE, NSET=NALL"] + [f"{int(n)}, {c[0]:.5f}, {c[1]:.5f}, {c[2]:.5f}" for n, c in zip(used, xyz)]
        lines.append("*ELEMENT, TYPE=C3D10, ELSET=EALL")
        lines += [f"{i + 1}, " + ", ".join(str(int(n)) for n in t) for i, t in enumerate(tets)]
        lines += ["*NSET, NSET=NFIX", ids(fixed), "*NSET, NSET=NLOAD", ids(loaded), "*ELSET, ELSET=EEVAL", ids(keep)]
        lines += ["*MATERIAL, NAME=M", "*ELASTIC", f"{job['young_mpa']}, {job['poisson']}",
                  "*SOLID SECTION, ELSET=EALL, MATERIAL=M", "*BOUNDARY", "NFIX, 1, 3", "*STEP", "*STATIC", "*CLOAD"]
        lines += [f"NLOAD, {dof}, {value / len(loaded):.6f}" for dof, value in enumerate(job["force_n"], start=1) if value]
        lines += ["*NODE PRINT, NSET=NALL", "U", "*EL PRINT, ELSET=EEVAL", "S", "*END STEP"]
        (folder / "case.inp").write_text("\n".join(lines) + "\n", encoding="ascii")
        run = calculix.run_ccx(folder, "case", timeout_s, threads)
        if not run["ok"]:
            return {"ok": False, "reason": run["reason"]}
        parsed = calculix.parse_static_dat(folder / "case.dat")
    disp = parsed["displacements"].get("NALL", {})
    umax = max((math.sqrt(sum(c * c for c in u)) for u in disp.values()), default=0.0)
    return {"ok": True, "von_mises_max_mpa": round(parsed["von_mises_max_mpa"], 2), "max_displacement_mm": round(umax, 4),
            "nodes": int(len(used)), "elements": int(len(tets)), "fixed_nodes": int(len(fixed)), "loaded_nodes": int(len(loaded)),
            "mesh_mm": round(size, 2), "seconds": round(time.monotonic() - start, 1),
            "note": "contrainte max hors d'une bande de 2 mailles autour de la zone encastrée (singularité)"}


def main() -> None:
    try:
        result = solve(json.loads(sys.stdin.read()))
    except Exception as exc:
        result = {"ok": False, "reason": f"{type(exc).__name__}: {exc}"}
    print("RESULT_JSON " + json.dumps(result))


if __name__ == "__main__":
    main()
