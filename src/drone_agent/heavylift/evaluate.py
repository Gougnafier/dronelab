"""Outil evaluate_vehicle : un design de multirotor lourd -> charge max, ratio, marges, score.

Score : charge_max / masse_aéronef si le design qualifie (masse < limite, charge >= minimum,
fréquences séparées), sinon moins la somme des écarts normalisés.
"""

from __future__ import annotations

import copy
import time

from ..spec import REPO_ROOT, load_spec, short_hash
from ..store import append_jsonl, now_iso, runs_dir
from ..tools.base import tool
from .model import PART, Vehicle, bound_violations, max_payload, normalize_params

SPEC_PATH = REPO_ROOT / "spec" / "darpa_lift.yaml"
KG_PER_LB = 0.45359237


def lift_spec(overrides: dict | None = None) -> dict:
    """Spec de base, avec éventuellement des valeurs remplacées par chemin pointé
    (ex. {"batteries.lipo.specific_energy_wh_kg": 180} ou {..: {"value": 180, ...}})."""
    spec = load_spec(SPEC_PATH)
    if not overrides:
        return spec
    spec = copy.deepcopy(spec)
    for path, entry in overrides.items():
        value = entry["value"] if isinstance(entry, dict) and "value" in entry else entry
        node, keys = spec, path.split(".")
        for key in keys[:-1]:
            if not isinstance(node.get(key), dict):
                raise KeyError(f"chemin de modèle inconnu : {path}")
            node = node[key]
        if keys[-1] not in node:
            raise KeyError(f"chemin de modèle inconnu : {path}")
        node[keys[-1]] = value
    return spec


@tool
def evaluate_vehicle(params: dict, edition: str | None = None, overrides: dict | None = None) -> dict:
    spec = lift_spec(overrides)
    edition = edition or spec["default_edition"]
    rules = spec["editions"][edition]
    params = normalize_params(params, spec["parameters"])
    design_id = f"{PART}-{short_hash({'params': params, 'spec': spec})}"
    issues = bound_violations(params, spec["parameters"])
    if params["arm_od_mm"] - 2 * params["arm_wall_mm"] <= 0:
        issues.append("tube de bras plein ou impossible (paroi >= rayon)")
    if issues:
        return {"ok": True, "valid": True, "design_id": design_id, "params": params, "edition": edition,
                "feasible": False, "violations": issues, "score": -float(len(issues))}

    vehicle = Vehicle(params, spec)
    result = max_payload(vehicle, rules, spec["payload_step_kg"])
    mass = vehicle.mass_kg
    payload = result["payload_kg"]
    frequency = vehicle.arm_frequency(payload)

    violations, penalty = [], 0.0
    if mass >= rules["aircraft_mass_max_kg"]:
        violations.append(f"masse aéronef {mass:.2f} kg >= {rules['aircraft_mass_max_kg']} kg")
        penalty += mass / rules["aircraft_mass_max_kg"] - 1
    if payload < rules["payload_min_kg"]:
        limit = ", ".join(result["limiting_factors"]) or "aucun vol possible"
        violations.append(f"charge max {payload:.1f} kg < {rules['payload_min_kg']} kg (limite : {limit})")
        penalty += 1 - payload / rules["payload_min_kg"]
    if frequency["separation"] < spec["margins"]["arm_frequency_separation"]:
        violations.append(f"1re fréquence du bras {frequency['f1_hz']} Hz trop proche des bandes 1P "
                          f"{frequency['one_p_hz']} Hz ou passage de pales {frequency['blade_pass_hz']} Hz")
        penalty += spec["margins"]["arm_frequency_separation"] - frequency["separation"]

    feasible = not violations
    ratio = payload / mass
    return {
        "ok": True,
        "valid": True,
        "design_id": design_id,
        "part": PART,
        "edition": edition,
        "params": params,
        "aircraft_mass_kg": round(mass, 3),
        "aircraft_mass_lb": round(mass / KG_PER_LB, 2),
        "max_payload_kg": payload,
        "max_payload_lb": round(payload / KG_PER_LB, 1),
        "payload_ratio": round(ratio, 3),
        "limiting_factors": result["limiting_factors"],
        "checks_at_max": result["checks_at_max"],
        "mission": result["details_at_max"],
        "arm_frequency": frequency,
        "mass_breakdown_kg": {k: round(v, 3) for k, v in vehicle.masses_kg.items()},
        "geometry": {"rotors": vehicle.n_rotors, "arm_center_m": round(vehicle.arm_center_m, 3),
                     "span_m": round(2 * vehicle.arm_center_m + vehicle.diameter_m, 3),
                     "disk_loading_n_m2": round((mass + payload) * vehicle.g / vehicle.total_area_m2, 1)},
        "battery_wh": round(vehicle.battery_wh, 1),
        "feasible": feasible,
        "violations": violations,
        "score": round(ratio, 4) if feasible else round(-penalty, 4),
    }


def evaluate(params: dict, cycle: int | None = None, edition: str | None = None, record: bool = True,
             overrides: dict | None = None, tags: dict | None = None) -> dict:
    """Évalue et ajoute une ligne à runs/results.jsonl (même contrat que le bras imprimé)."""
    start = time.monotonic()
    result = evaluate_vehicle(params, edition, overrides)
    line = {"cycle": cycle, "timestamp": now_iso(), **(tags or {}),
            **{k: v for k, v in result.items() if k != "trace"}}
    line.setdefault("part", PART)
    line["seconds"] = round(time.monotonic() - start, 3)
    if record:
        append_jsonl(runs_dir() / "results.jsonl", line)
    return line
