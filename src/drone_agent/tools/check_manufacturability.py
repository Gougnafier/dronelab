"""Outil check_manufacturability : paroi mince, hors plateau, bornes, interfaces."""

from __future__ import annotations

from ..spec import load_spec
from ..store import design_dir, read_json
from .base import tool
from .generate_part import layout_for


@tool
def check_manufacturability(design_id: str) -> dict:
    spec = load_spec()
    part = read_json(design_dir(design_id) / "part.json")
    if not part or not part.get("valid"):
        return {"ok": False, "valid": False, "design_id": design_id, "reason": "design non généré"}
    params, mfg = part["params"], spec["manufacturing"]
    violations = []

    for key, bounds in spec["parameters"].items():
        value = params.get(key)
        if key == "material" and value not in bounds:
            violations.append(f"matériau non autorisé : {value}")
        elif key not in ("material", "rib") and value is not None:
            if (params["holes"] == 0 and key == "hole_ratio") or (not params["rib"] and key.startswith("rib_")):
                continue
            if not bounds[0] <= value <= bounds[1]:
                violations.append(f"{key}={value} hors bornes {bounds}")

    bed_x, bed_y = mfg["bed_mm"]
    length, width, height = part["bbox_mm"]
    fits = (length <= bed_x and width <= bed_y) or (length <= bed_y and width <= bed_x)
    if not fits:
        violations.append(f"hors plateau : {length} x {width} mm > {bed_x} x {bed_y} mm")
    if height > mfg["max_height_mm"]:
        violations.append(f"hauteur {height} mm > {mfg['max_height_mm']} mm")

    layout = layout_for(params, spec)
    walls = {k: round(v, 3) for k, v in layout.min_walls().items()}
    for name, value in walls.items():
        if value < mfg["min_wall_mm"]:
            violations.append(f"paroi mince ({name}) : {value} mm < {mfg['min_wall_mm']} mm")
    if layout.pad_thickness < mfg["pad_min_thickness_mm"]:
        violations.append(f"plateau moteur trop fin : {layout.pad_thickness} mm")
    if params["rib"] and layout.inner_width_at(layout.motor_x) < 0:
        violations.append("nervures qui se chevauchent en bout de bras")
    if params["holes"] and len(layout.holes) < params["holes"]:
        violations.append(f"{params['holes'] - len(layout.holes)} évidement(s) trop petit(s) pour être imprimés")

    return {
        "ok": True,
        "valid": True,
        "design_id": design_id,
        "manufacturable": not violations,
        "violations": violations,
        "min_walls_mm": walls,
        "interfaces": "figées par le générateur (spec/cahier_des_charges.yaml#interfaces)",
    }
