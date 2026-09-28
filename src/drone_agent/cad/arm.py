"""Bras paramétrique : géométrie OpenCASCADE via Gmsh, export STEP/STL, maillage C3D10.

Repère : X le long du bras (0 = extrémité encastrée, axe moteur en x = L),
Y latéral, Z vertical (âme posée sur z = 0, face d'impression).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path

PART = "arm"
PARAM_KEYS = (
    "thickness_mm",
    "width_mm",
    "taper",
    "holes",
    "hole_ratio",
    "rib",
    "rib_height_mm",
    "rib_width_mm",
    "material",
)
DEFAULTS = {
    "taper": 1.0,
    "holes": 0,
    "hole_ratio": 0.5,
    "rib": False,
    "rib_height_mm": 0.0,
    "rib_width_mm": 2.0,
    "material": "PETG",
}
HOLE_MARGIN_MM = 2.0  # marge entre évidements et zones encastrement / plateau moteur


def normalize_params(params: dict) -> dict:
    """Complète, type et arrondit les paramètres ; lève ValueError si inconnus."""
    unknown = sorted(set(params) - set(PARAM_KEYS))
    if unknown:
        raise ValueError(f"paramètres inconnus ou interface figée : {unknown}")
    merged = {**DEFAULTS, **params}
    missing = [key for key in PARAM_KEYS if key not in merged]
    if missing:
        raise ValueError(f"paramètres manquants : {missing}")
    out = {
        "thickness_mm": round(float(merged["thickness_mm"]), 2),
        "width_mm": round(float(merged["width_mm"]), 2),
        "taper": round(float(merged["taper"]), 3),
        "holes": int(merged["holes"]),
        "hole_ratio": round(float(merged["hole_ratio"]), 3),
        "rib": bool(merged["rib"]),
        "rib_height_mm": round(float(merged["rib_height_mm"]), 2),
        "rib_width_mm": round(float(merged["rib_width_mm"]), 2),
        "material": str(merged["material"]),
    }
    if not out["rib"]:
        out["rib_height_mm"] = 0.0
        out["rib_width_mm"] = 0.0
    if out["holes"] == 0:
        out["hole_ratio"] = 0.0
    return out


@dataclass
class Hole:
    x: float
    diameter: float


@dataclass
class ArmLayout:
    """Cotes dérivées des paramètres, sans CAO : partagées par la CAO et la fabricabilité."""

    params: dict
    interfaces: dict
    min_pad_thickness: float
    root_length: float = 0.0
    motor_x: float = 0.0
    pad_radius: float = 0.0
    pad_thickness: float = 0.0
    rib_end_x: float = 0.0
    holes: list[Hole] = field(default_factory=list)
    hole_pitch: float = 0.0

    def __post_init__(self) -> None:
        itf = self.interfaces
        self.root_length = itf["root_length_mm"]
        self.motor_x = self.root_length + itf["arm_free_length_mm"]
        self.pad_radius = itf["motor_pad_diameter_mm"] / 2
        self.pad_thickness = max(self.params["thickness_mm"], self.min_pad_thickness)
        clear_radius = itf["motor_footprint_diameter_mm"] / 2 + 0.5
        half_tip = self.width_at(self.motor_x) / 2
        self.rib_end_x = self.motor_x - math.sqrt(max(clear_radius**2 - half_tip**2, 0.0))
        self._place_holes()

    def width_at(self, x: float) -> float:
        p = self.params
        return p["width_mm"] * (1 + (p["taper"] - 1) * x / self.motor_x)

    def inner_width_at(self, x: float) -> float:
        return self.width_at(x) - 2 * self.params["rib_width_mm"]

    def _place_holes(self) -> None:
        n = self.params["holes"]
        if n <= 0:
            return
        start = self.root_length + HOLE_MARGIN_MM
        end = self.motor_x - self.pad_radius - HOLE_MARGIN_MM
        self.hole_pitch = (end - start) / n
        for i in range(n):
            x = start + self.hole_pitch * (i + 0.5)
            span = min(self.inner_width_at(x), self.hole_pitch)
            diameter = self.params["hole_ratio"] * span
            if diameter >= 1.0:
                self.holes.append(Hole(x=round(x, 3), diameter=round(diameter, 3)))

    def min_walls(self) -> dict:
        """Parois minimales (mm) par zone ; utilisé par check_manufacturability."""
        p = self.params
        walls = {"web_thickness": p["thickness_mm"]}
        if p["rib"]:
            walls["rib_width"] = p["rib_width_mm"]
        if self.holes:
            walls["between_holes"] = min(
                self.hole_pitch - (a.diameter + b.diameter) / 2
                for a, b in zip(self.holes, self.holes[1:])
            ) if len(self.holes) > 1 else self.hole_pitch
            walls["hole_side"] = min((self.inner_width_at(h.x) - h.diameter) / 2 for h in self.holes)
        pattern_half = self.interfaces["motor_pattern_mm"] / 2
        walls["motor_hole_edge"] = (
            self.pad_radius - math.hypot(pattern_half, pattern_half)
            - self.interfaces["motor_screw_hole_mm"] / 2
        )
        return walls


def build_geometry(layout: ArmLayout):
    """Construit le solide dans le modèle Gmsh courant ; renvoie le tag du volume."""
    import gmsh

    occ = gmsh.model.occ
    p, itf = layout.params, layout.interfaces
    t, L = p["thickness_mm"], layout.motor_x
    w0, w1 = layout.width_at(0.0), layout.width_at(L)

    def prism(points_xy, z0, height):
        pts = [occ.addPoint(x, y, z0) for x, y in points_xy]
        lines = [occ.addLine(pts[i], pts[(i + 1) % len(pts)]) for i in range(len(pts))]
        surface = occ.addPlaneSurface([occ.addCurveLoop(lines)])
        extruded = occ.extrude([(2, surface)], 0, 0, height)
        return [e for e in extruded if e[0] == 3][0]

    parts = [prism([(0, -w0 / 2), (L, -w1 / 2), (L, w1 / 2), (0, w0 / 2)], 0, t)]
    parts.append((3, occ.addCylinder(L, 0, 0, 0, 0, layout.pad_thickness, layout.pad_radius)))
    if p["rib"] and p["rib_height_mm"] > 0:
        xe = layout.rib_end_x + 0.5  # recouvrement avec le plateau pour fusionner
        rw, height = p["rib_width_mm"], t + p["rib_height_mm"]
        for sign in (-1, 1):
            outer0, outer1 = w0 / 2, layout.width_at(xe) / 2
            pts = [(0, sign * outer0), (xe, sign * outer1), (xe, sign * (outer1 - rw)), (0, sign * (outer0 - rw))]
            parts.append(prism(pts, 0, height))

    fused, _ = occ.fuse([parts[0]], parts[1:])
    zmin, zmax = -1.0, t + p["rib_height_mm"] + layout.pad_thickness + 1.0
    tools = []

    def through_hole(x, y, diameter):
        tools.append((3, occ.addCylinder(x, y, zmin, 0, 0, zmax - zmin, diameter / 2)))

    for hole in layout.holes:
        through_hole(hole.x, 0.0, hole.diameter)
    for x in itf["root_screw_x_mm"]:
        through_hole(x, 0.0, itf["root_screw_hole_mm"])
    half = itf["motor_pattern_mm"] / 2
    for dx, dy in ((half, half), (half, -half), (-half, half), (-half, -half)):
        through_hole(L + dx, dy, itf["motor_screw_hole_mm"])
    through_hole(L, 0.0, itf["motor_shaft_hole_mm"])

    result, _ = occ.cut(fused, tools)
    occ.synchronize()
    return result


def mesh_to_calculix(path: Path, layout: ArmLayout, band_mm: float) -> dict:
    """Écrit le maillage C3D10 courant et les ensembles utiles aux cas de charge."""
    import gmsh
    import numpy as np

    node_tags, coords, _ = gmsh.model.mesh.getNodes()
    coords = coords.reshape(-1, 3)
    elem_types, elem_tags, elem_nodes = gmsh.model.mesh.getElements(3)
    if 11 not in list(elem_types):
        raise RuntimeError("maillage sans tétraèdres quadratiques (type 11)")
    idx = list(elem_types).index(11)
    tets = np.asarray(elem_nodes[idx], dtype=np.int64).reshape(-1, 10)
    # Gmsh -> Abaqus/CalculiX : les deux derniers nœuds milieux sont permutés.
    tets = tets[:, [0, 1, 2, 3, 4, 5, 6, 7, 9, 8]]
    used = np.unique(tets)
    pos = {int(tag): i for i, tag in enumerate(node_tags)}
    xyz = np.array([coords[pos[int(n)]] for n in used])
    node_xyz = dict(zip(used.tolist(), xyz))

    root_nodes = [int(n) for n, c in node_xyz.items() if c[0] <= layout.root_length + 1e-6]
    r_foot = layout.interfaces["motor_footprint_diameter_mm"] / 2
    motor_nodes = [
        int(n) for n, c in node_xyz.items()
        if c[2] >= layout.pad_thickness - 1e-6 and math.hypot(c[0] - layout.motor_x, c[1]) <= r_foot
    ]
    x_of = np.zeros(int(used.max()) + 1)
    x_of[used] = xyz[:, 0]
    centroid_x = x_of[tets[:, :4]].mean(axis=1)
    elem_ids = np.arange(1, len(tets) + 1)
    eval_elems = elem_ids[centroid_x > layout.root_length + band_mm].tolist()
    if not root_nodes or not motor_nodes or not eval_elems:
        raise RuntimeError("ensembles vides (encastrement, plateau moteur ou zone d'évaluation)")

    def id_lines(ids):
        return "\n".join(", ".join(str(i) for i in ids[k:k + 16]) for k in range(0, len(ids), 16))

    lines = ["*NODE, NSET=NALL"]
    lines += [f"{n}, {c[0]:.6f}, {c[1]:.6f}, {c[2]:.6f}" for n, c in node_xyz.items()]
    lines.append("*ELEMENT, TYPE=C3D10, ELSET=EALL")
    lines += [f"{eid}, " + ", ".join(str(int(n)) for n in tet) for eid, tet in zip(elem_ids, tets)]
    lines += ["*NSET, NSET=NROOT", id_lines(root_nodes)]
    lines += ["*NSET, NSET=NMOTOR", id_lines(motor_nodes)]
    lines += ["*ELSET, ELSET=EEVAL", id_lines(eval_elems)]
    path.write_text("\n".join(lines) + "\n", encoding="ascii")
    return {
        "nodes": len(used),
        "elements": len(tets),
        "max_node_id": int(used.max()),
        "root_nodes": len(root_nodes),
        "motor_nodes": len(motor_nodes),
        "motor_ref_xyz": [layout.motor_x, 0.0, layout.pad_thickness],
    }
