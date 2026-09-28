"""Bras en tube : modèle coque (S8R) Gmsh + CalculiX, encastré au moyeu, effort et masse du moteur
répartis sur les nœuds d'extrémité (CalculiX refuse un corps rigide sur des nœuds de coque).

Entrée (dict, SI sauf mention) : length_m, od_mm, wall_mm, young_gpa, poisson, density_kg_m3,
strength_mpa, tip_force_n [Fx, Fy, Fz], tip_mass_kg, mesh_mm (optionnel).
Sortie : contrainte de von Mises max, facteur de sécurité, flèche en bout, 1re fréquence.
Unités internes : mm, N, t, MPa.
"""

from __future__ import annotations

import math
import tempfile
import time
from pathlib import Path

from . import calculix


def _mesh(job: dict, folder: Path) -> dict:
    import gmsh
    import numpy as np

    length = job["length_m"] * 1000
    radius = (job["od_mm"] - job["wall_mm"]) / 2  # rayon du feuillet moyen
    size = job.get("mesh_mm") or max(2.0, min(8.0, 2 * math.pi * radius / 48))
    gmsh.initialize(interruptible=False)
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        occ = gmsh.model.occ
        circle = occ.addCircle(0, 0, 0, radius, zAxis=[1, 0, 0])
        occ.extrude([(1, circle)], length, 0, 0, numElements=[max(4, round(length / size))], recombine=True)
        occ.synchronize()
        for curve in gmsh.model.getEntities(1):
            gmsh.model.mesh.setTransfiniteCurve(curve[1], max(8, round(2 * math.pi * radius / size)) + 1)
        gmsh.option.setNumber("Mesh.RecombineAll", 1)
        gmsh.option.setNumber("Mesh.ElementOrder", 2)
        gmsh.option.setNumber("Mesh.SecondOrderIncomplete", 1)
        gmsh.model.mesh.generate(2)
        tags, coords, _ = gmsh.model.mesh.getNodes()
        types, _, nodes = gmsh.model.mesh.getElements(2)
    finally:
        gmsh.finalize()
    if 16 not in list(types):
        raise RuntimeError("maillage sans quadrangles à 8 nœuds")
    quads = np.asarray(nodes[list(types).index(16)], dtype=np.int64).reshape(-1, 8)
    xyz = dict(zip((int(t) for t in tags), coords.reshape(-1, 3)))
    used = sorted({int(n) for n in quads.ravel()})
    root = [n for n in used if xyz[n][0] < 1e-6]
    tip = [n for n in used if xyz[n][0] > length - 1e-6]
    band = job["od_mm"]  # exclusion de la zone perturbée par l'encastrement
    centroid_x = np.array([np.mean([xyz[int(n)][0] for n in q[:4]]) for q in quads])
    eval_elems = [i + 1 for i in np.nonzero((centroid_x > band) & (centroid_x < length - band))[0].tolist()]

    def ids(values):
        return "\n".join(", ".join(str(v) for v in values[k:k + 16]) for k in range(0, len(values), 16))

    lines = ["*NODE, NSET=NALL"] + [f"{n}, {xyz[n][0]:.5f}, {xyz[n][1]:.5f}, {xyz[n][2]:.5f}" for n in used]
    lines.append("*ELEMENT, TYPE=S8R, ELSET=EALL")
    lines += [f"{i + 1}, " + ", ".join(str(int(n)) for n in q) for i, q in enumerate(quads)]
    lines += ["*NSET, NSET=NROOT", ids(root), "*NSET, NSET=NTIP", ids(tip), "*ELSET, ELSET=EEVAL", ids(eval_elems)]
    (folder / "mesh.inp").write_text("\n".join(lines) + "\n", encoding="ascii")
    return {"max_node": max(used), "elements": len(quads), "length_mm": length, "mesh_mm": round(size, 2),
            "tip_nodes": tip}


def _deck(job: dict, mesh: dict, modal: bool) -> str:
    tip = mesh["tip_nodes"]
    rho = job["density_kg_m3"] * 1e-12  # t/mm^3
    deck = [
        "*INCLUDE, INPUT=mesh.inp",
        f"*MATERIAL, NAME=CFRP\n*ELASTIC\n{job['young_gpa'] * 1000}, {job['poisson']}\n*DENSITY\n{rho:.6e}",
        f"*SHELL SECTION, ELSET=EALL, MATERIAL=CFRP\n{job['wall_mm']}",
        "*BOUNDARY\nNROOT, 1, 6",
    ]
    if modal:
        first = mesh["elements"] + 1
        deck += ["*ELEMENT, TYPE=MASS, ELSET=EMOTOR"] + [f"{first + i}, {n}" for i, n in enumerate(tip)]
        deck += [f"*MASS, ELSET=EMOTOR\n{job['tip_mass_kg'] * 1e-3 / len(tip):.6e}", "*STEP\n*FREQUENCY\n3",
                 "*END STEP"]
    else:
        loads = [f"NTIP, {dof}, {value / len(tip):.6f}" for dof, value in enumerate(job["tip_force_n"], start=1)
                 if value]
        deck += ["*STEP", "*STATIC", "*CLOAD", *loads, "*NODE PRINT, NSET=NTIP", "U",
                 "*EL PRINT, ELSET=EEVAL", "S", "*END STEP"]
    return "\n".join(deck) + "\n"


def solve_tube(job: dict, timeout_s: float = 300, threads: int = 4) -> dict:
    start = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="tube-") as tmp:
        folder = Path(tmp) if not job.get("keep_dir") else Path(job["keep_dir"])
        folder.mkdir(parents=True, exist_ok=True)
        mesh = _mesh(job, folder)
        out = {"ok": True, "elements": mesh["elements"], "mesh_mm": mesh["mesh_mm"]}
        for name, modal in (("static", False), ("modal", True)):
            (folder / f"{name}.inp").write_text(_deck(job, mesh, modal), encoding="ascii")
            run = calculix.run_ccx(folder, name, timeout_s, threads)
            if not run["ok"]:
                return {"ok": False, "reason": f"{name} : {run['reason']}"}
        static = calculix.parse_static_dat(folder / "static.dat")
        tip_u = list(static["displacements"].get("NTIP", {}).values())
        tip = [sum(u[i] for u in tip_u) / len(tip_u) for i in range(3)] if tip_u else None
        freqs = calculix.parse_frequencies(folder / "modal.dat")
        if tip is None or not freqs:
            return {"ok": False, "reason": "résultats absents"}
    vm = static["von_mises_max_mpa"]
    out.update({
        "von_mises_max_mpa": round(vm, 2),
        "sf": round(job["strength_mpa"] / vm, 3) if vm > 0 else None,
        "tip_deflection_mm": round(math.sqrt(sum(u * u for u in tip)), 3),
        "f1_hz": round(freqs[0], 2),
        "modal_hz": [round(f, 2) for f in freqs[:3]],
        "seconds": round(time.monotonic() - start, 1),
    })
    return out


def main() -> None:
    """Point d'entrée distant : job JSON sur l'entrée standard, résultat JSON sur la sortie standard."""
    import json
    import sys

    try:
        result = solve_tube(json.loads(sys.stdin.read()))
    except Exception as exc:  # le résultat doit toujours être lisible
        result = {"ok": False, "reason": f"{type(exc).__name__}: {exc}"}
    print("RESULT_JSON " + json.dumps(result))


if __name__ == "__main__":
    main()
