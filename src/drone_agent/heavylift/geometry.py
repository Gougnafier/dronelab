"""Maquette 3D d'un design heavylift : pièces primitives aux cotes et masses du modèle, export OpenUSD.

Repère : mètres, Z vers le haut, moyeu centré à l'origine. Les formes sont des maquettes (cylindres,
boîtes) : volumes déduits des masses, pas des fichiers de fabricants.
"""

from __future__ import annotations

import math
from pathlib import Path

from .model import Vehicle

LB = 0.45359237
# Disques Olympic autorisés par le règlement : (livres, diamètre m, épaisseur m), valeurs indicatives.
PLATES = [(45, 0.450, 0.055), (35, 0.420, 0.050), (25, 0.380, 0.042), (10, 0.300, 0.035), (5, 0.230, 0.030),
          (2.5, 0.190, 0.025)]
COLORS = {"hub": (0.18, 0.18, 0.2), "arm": (0.05, 0.05, 0.06), "motor": (0.75, 0.2, 0.15),
          "prop": (0.85, 0.87, 0.9), "battery": (0.95, 0.75, 0.1), "gear": (0.25, 0.25, 0.28),
          "plate": (0.12, 0.12, 0.13), "sling": (0.6, 0.6, 0.62)}


def _cyl(name, kind, radius, height, center, axis="Z", yaw_deg=0.0, mass=0.0, opacity=1.0):
    return {"name": name, "kind": kind, "shape": "cylinder", "radius": radius, "height": height,
            "center": list(center), "axis": axis, "yaw_deg": yaw_deg, "mass_kg": mass,
            "color": COLORS[kind], "opacity": opacity}


def _box(name, kind, size, center, mass=0.0):
    return {"name": name, "kind": kind, "shape": "box", "size": list(size), "center": list(center),
            "axis": "Z", "yaw_deg": 0.0, "mass_kg": mass, "color": COLORS[kind], "opacity": 1.0}


def plate_stack(payload_kg: float) -> list[tuple[float, float, float]]:
    """Décomposition gloutonne en disques (plus grands d'abord), comme le demande le règlement."""
    remaining = payload_kg / LB + 1e-6
    stack = []
    for pounds, diameter, thickness in PLATES:
        while remaining >= pounds:
            stack.append((pounds, diameter, thickness))
            remaining -= pounds
    return stack


def assembly(vehicle: Vehicle, payload_kg: float) -> list[dict]:
    p, mm = vehicle.params, vehicle.spec["mass_models"]
    masses = vehicle.masses_kg
    parts = []
    hub_r = mm["hub_radius_m"]
    parts.append(_cyl("hub", "hub", hub_r, 0.07, (0, 0, 0), mass=masses["hub"] + masses["avionics"]))

    od = p["arm_od_mm"] / 1000
    per_rotor = {k: masses[k] / vehicle.n_rotors for k in ("motors", "escs", "props")}
    motor_mass = per_rotor["motors"]
    motor_r = (motor_mass / 4500 / (1.2 * math.pi)) ** (1 / 3)  # masse volumique apparente d'un moteur
    motor_h = 1.2 * motor_r
    prop_r = vehicle.diameter_m / 2
    arm_start = 0.6 * hub_r
    arm_len = vehicle.arm_center_m - arm_start
    for i in range(vehicle.n_arms):
        angle = 2 * math.pi * i / vehicle.n_arms + math.pi / vehicle.n_arms
        ca, sa = math.cos(angle), math.sin(angle)
        mid = arm_start + arm_len / 2
        parts.append(_cyl(f"arm_{i}", "arm", od / 2, arm_len, (mid * ca, mid * sa, 0), axis="X",
                          yaw_deg=math.degrees(angle), mass=masses["arms"] / vehicle.n_arms))
        tip = (vehicle.arm_center_m * ca, vehicle.arm_center_m * sa)
        levels = [1] + ([-1] if p["coaxial"] else [])
        for level in levels:
            z_motor = level * (od / 2 + motor_h / 2)
            parts.append(_cyl(f"motor_{i}_{'up' if level > 0 else 'down'}", "motor", motor_r, motor_h,
                              (*tip, z_motor), mass=motor_mass + per_rotor["escs"]))
            z_prop = level * (od / 2 + motor_h + 0.02)
            parts.append(_cyl(f"prop_{i}_{'up' if level > 0 else 'down'}", "prop", prop_r, 0.006, (*tip, z_prop),
                              mass=per_rotor["props"], opacity=0.35))

    battery_volume = masses["battery"] / 2000.0  # pack ~2 kg/L
    bx = (battery_volume / (0.6 * 0.35)) ** (1 / 3)
    size = (bx, 0.6 * bx, 0.35 * bx)
    parts.append(_box("battery", "battery", size, (0, 0, 0.035 + size[2] / 2), mass=masses["battery"]))

    leg_h = 0.55
    for i, (sx, sy) in enumerate(((1, 1), (1, -1), (-1, 1), (-1, -1))):
        parts.append(_cyl(f"gear_leg_{i}", "gear", 0.012, leg_h, (sx * 0.8 * hub_r, sy * 0.8 * hub_r, -leg_h / 2 - 0.035),
                          mass=masses["landing_gear"] / 6))
    for i, sy in enumerate((1, -1)):
        parts.append(_cyl(f"gear_skid_{i}", "gear", 0.015, 0.9, (0, sy * 0.8 * hub_r, -leg_h - 0.035), axis="X",
                          mass=masses["landing_gear"] / 6))

    stack = plate_stack(payload_kg)
    z = -0.12
    parts.append(_cyl("payload_release", "sling", 0.02, 0.08, (0, 0, -0.075), mass=masses["payload_release"]))
    for i, (pounds, diameter, thickness) in enumerate(stack):
        z -= thickness
        parts.append(_cyl(f"plate_{i}_{pounds:g}lb", "plate", diameter / 2, thickness, (0, 0, z + thickness / 2),
                          mass=pounds * LB))
    return parts


def write_usda(parts: list[dict], path: Path, meta: dict) -> Path:
    """OpenUSD ASCII sans dépendance : Xform racine, Cylinder et Cube, masses en PhysicsMassAPI."""
    def fmt(v):
        return f"({v[0]:.5f}, {v[1]:.5f}, {v[2]:.5f})"

    lines = ["#usda 1.0", "(", '    defaultPrim = "Drone"', "    metersPerUnit = 1", '    upAxis = "Z"',
             f'    doc = "{meta.get("design_id", "")} — maquette générée par l\'agent dronelab"', ")", "",
             'def Xform "Drone"', "{"]
    for key, value in meta.items():
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            lines.append(f"    custom double dronelab:{key} = {value}")
        elif isinstance(value, str):
            lines.append(f'    custom string dronelab:{key} = "{value}"')
    for part in parts:
        prim = "Cylinder" if part["shape"] == "cylinder" else "Cube"
        lines += ["", f'    def {prim} "{part["name"]}" (', '        prepend apiSchemas = ["PhysicsMassAPI"]', "    )", "    {"]
        if prim == "Cylinder":
            lines += [f"        double radius = {part['radius']:.5f}", f"        double height = {part['height']:.5f}",
                      f'        uniform token axis = "{part["axis"]}"']
            ops = ["xformOp:translate", "xformOp:rotateXYZ"]
        else:
            lines += ["        double size = 1"]
            lines.append(f"        float3 xformOp:scale = {fmt(part['size'])}")
            ops = ["xformOp:translate", "xformOp:rotateXYZ", "xformOp:scale"]
        lines += [f"        float3 xformOp:translate = {fmt(part['center'])}",
                  f"        float3 xformOp:rotateXYZ = (0, 0, {part['yaw_deg']:.3f})",
                  "        uniform token[] xformOpOrder = [" + ", ".join(f'"{o}"' for o in ops) + "]",
                  f"        color3f[] primvars:displayColor = [{fmt(part['color'])}]",
                  f"        float[] primvars:displayOpacity = [{part['opacity']}]",
                  f"        float physics:mass = {part['mass_kg']:.4f}",
                  "    }"]
    lines.append("}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
