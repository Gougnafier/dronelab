"""Dimensionnement d'un multirotor lourd sur l'épreuve DARPA Lift (modèle de conception préliminaire).

Puissance : théorie de la quantité de mouvement avec facteur de mérite, vitesse induite de Glauert
en avancement, puissance de profil (1 + 4,65 mu^2) et puissance parasite. Bras : tube encastré
au moyeu, force au moteur (flexion, flèche, 1re fréquence avec masse en bout).
Le résultat principal est la charge maximale transportable sur le parcours, par pas de 2,5 lb.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

PART = "heavylift"


def normalize_params(params: dict, bounds: dict) -> dict:
    unknown = sorted(set(params) - set(bounds))
    if unknown:
        raise ValueError(f"paramètres inconnus : {unknown}")
    missing = sorted(set(bounds) - set(params))
    if missing:
        raise ValueError(f"paramètres manquants : {missing}")
    out = {}
    for key, allowed in bounds.items():
        value = params[key]
        if key == "n_arms":
            out[key] = int(value)
        elif key == "coaxial":
            out[key] = bool(value)
        elif key == "battery":
            out[key] = str(value)
        else:
            out[key] = round(float(value), 3)
    return out


def bound_violations(params: dict, bounds: dict) -> list[str]:
    issues = []
    for key, allowed in bounds.items():
        value = params[key]
        if key in ("n_arms", "coaxial", "battery"):
            if value not in allowed:
                issues.append(f"{key}={value} hors valeurs {allowed}")
        elif not allowed[0] <= value <= allowed[1]:
            issues.append(f"{key}={value} hors bornes {allowed}")
    return issues


@dataclass
class Vehicle:
    params: dict
    spec: dict

    def __post_init__(self) -> None:
        p, s = self.params, self.spec
        prop, env, mm = s["propulsion"], s["environment"], s["mass_models"]
        self.rho, self.g = env["air_density_kg_m3"], env["gravity_m_s2"]
        self.n_arms = p["n_arms"]
        self.rotors_per_arm = 2 if p["coaxial"] else 1
        self.n_rotors = self.n_arms * self.rotors_per_arm
        self.diameter_m = p["prop_diameter_in"] * 0.0254
        self.radius_m = self.diameter_m / 2
        disk = math.pi * self.radius_m**2
        self.arm_area_m2 = disk * (prop["coaxial_area_factor"] if p["coaxial"] else 1.0)
        self.total_area_m2 = self.n_arms * self.arm_area_m2
        self.eta = prop["motor_efficiency"] * prop["esc_efficiency"]
        self.fm, self.kappa = prop["figure_of_merit"], prop["induced_power_factor"]
        # Hélice choisie pour Mach max en bout de pale à poussée max ; plus lente en stationnaire.
        self.tip_speed_max = s["margins"]["tip_mach_max"] * prop["speed_of_sound_m_s"]

        clearance = 1 + s["margins"]["rotor_clearance_ratio"]
        self.arm_center_m = max(self.radius_m * clearance / math.sin(math.pi / self.n_arms),
                                mm["hub_radius_m"] + self.radius_m * clearance)
        self.arm_free_m = self.arm_center_m - mm["hub_radius_m"]

        od, wall = p["arm_od_mm"] / 1000, p["arm_wall_mm"] / 1000
        idia = max(od - 2 * wall, 0.0)
        self.arm_inertia_m4 = math.pi / 64 * (od**4 - idia**4)
        arm_section = math.pi / 4 * (od**2 - idia**2)
        arm_tube_kg = s["arm_material"]["density_kg_m3"] * arm_section * (self.arm_free_m + 0.1)

        motor_kw = p["motor_power_kw"]
        per_rotor = {
            "motor": motor_kw / mm["motor_specific_power_kw_kg"],
            "esc": motor_kw / mm["esc_specific_power_kw_kg"],
            "prop": mm["prop_mass_40in_kg"] * (p["prop_diameter_in"] / 40) ** mm["prop_mass_exponent"],
        }
        self.tip_mass_per_arm_kg = self.rotors_per_arm * sum(per_rotor.values())
        self.arm_tube_kg = arm_tube_kg
        self.masses_kg = {
            "motors": self.n_rotors * per_rotor["motor"],
            "escs": self.n_rotors * per_rotor["esc"],
            "props": self.n_rotors * per_rotor["prop"],
            "arms": self.n_arms * arm_tube_kg,
            "hub": mm["hub_kg"] + mm["hub_per_arm_kg"] * self.n_arms,
            "landing_gear": mm["landing_gear_kg"],
            "payload_release": mm["payload_release_kg"],
            "avionics": mm["avionics_kg"],
            "wiring": mm["wiring_kg_per_kw"] * self.n_rotors * motor_kw,
            "battery": p["battery_kg"],
        }
        self.mass_kg = sum(self.masses_kg.values())
        chem = s["batteries"][p["battery"]]
        self.battery_wh = p["battery_kg"] * chem["specific_energy_wh_kg"]
        self.battery_max_w = self.battery_wh * chem["max_continuous_c"]

    # --- puissances (W arbre) ---------------------------------------------------------
    def tip_speed(self, thrust_n: float) -> float:
        """Vitesse en bout de pale pour une poussée totale donnée (T proportionnelle à Omega^2)."""
        return self.tip_speed_max * math.sqrt(min(1.0, thrust_n / self.max_static_thrust_n()))

    def hover_velocity(self, thrust_n: float) -> float:
        return math.sqrt(thrust_n / (2 * self.rho * self.total_area_m2))

    def profile_power(self, thrust_n: float, mu: float = 0.0) -> float:
        return (1 / self.fm - self.kappa) * thrust_n * self.hover_velocity(thrust_n) * (1 + 4.65 * mu**2)

    def hover_power(self, weight_n: float) -> float:
        return weight_n * self.hover_velocity(weight_n) / self.fm

    def climb_power(self, weight_n: float, climb_rate: float) -> float:
        vh = self.hover_velocity(weight_n)
        vi = -climb_rate / 2 + math.sqrt(climb_rate**2 / 4 + vh**2)
        return weight_n * climb_rate + self.kappa * weight_n * vi + self.profile_power(weight_n)

    def cruise_power(self, weight_n: float, airspeed: float, cda_m2: float) -> float:
        drag = 0.5 * self.rho * airspeed**2 * cda_m2
        thrust = math.hypot(weight_n, drag)
        vh = self.hover_velocity(thrust)
        vi = math.sqrt((-airspeed**2 + math.sqrt(airspeed**4 + 4 * vh**4)) / 2)
        mu = airspeed / self.tip_speed(thrust)
        return self.kappa * thrust * vi + self.profile_power(thrust, mu) + drag * airspeed

    def max_static_thrust_n(self) -> float:
        shaft_per_arm = self.rotors_per_arm * self.params["motor_power_kw"] * 1000
        per_arm = (shaft_per_arm * self.fm * math.sqrt(2 * self.rho * self.arm_area_m2)) ** (2 / 3)
        return self.n_arms * per_arm

    # --- mission ----------------------------------------------------------------------
    def mission(self, payload_kg: float, edition: dict) -> dict:
        s, g = self.spec, self.g
        mis, mm = s["mission"], s["mass_models"]
        v = self.params["cruise_speed_m_s"]
        airspeed = v + s["environment"]["headwind_m_s"]
        loaded, empty = (self.mass_kg + payload_kg) * g, self.mass_kg * g
        h = s["cruise_altitude_m"]
        segments = [
            ("takeoff_hover", mis["takeoff_hover_s"], self.hover_power(loaded)),
            ("climb", h / mis["climb_rate_m_s"], self.climb_power(loaded, mis["climb_rate_m_s"])),
            ("cruise_loaded", edition["loaded_distance_m"] / v,
             self.cruise_power(loaded, airspeed, mm["body_cda_m2"] + mm["payload_cda_m2"])),
            ("drop_hover", mis["drop_hover_s"], self.hover_power(loaded)),
            ("cruise_empty", edition["unloaded_distance_m"] / v, self.cruise_power(empty, airspeed, mm["body_cda_m2"])),
            ("descent", h / mis["descent_rate_m_s"], self.hover_power(empty)),
            ("landing_hover", mis["landing_hover_s"], self.hover_power(empty)),
        ]
        table = {name: {"seconds": round(t, 1), "power_kw": round(p / self.eta / 1000, 3),
                        "energy_wh": round(p / self.eta * t / 3600, 2)} for name, t, p in segments}
        energy_wh = sum(seg["energy_wh"] for seg in table.values())
        return {"segments": table, "energy_wh": round(energy_wh, 1),
                "time_s": round(sum(t for _, t, _ in segments), 1),
                "peak_cruise_kw": max(seg["power_kw"] for seg in table.values())}

    def arm_checks(self, payload_kg: float) -> dict:
        s = self.spec
        mat, margins = s["arm_material"], s["margins"]
        e_pa, length = mat["young_gpa"] * 1e9, self.arm_free_m
        loaded_n = (self.mass_kg + payload_kg) * self.g
        design_force = margins["thrust_to_weight_min"] * loaded_n / self.n_arms
        od = self.params["arm_od_mm"] / 1000
        stress_mpa = design_force * length * (od / 2) / self.arm_inertia_m4 / 1e6
        hover_force = loaded_n / self.n_arms
        stiffness = 3 * e_pa * self.arm_inertia_m4 / length**3
        return {
            "arm_free_length_m": round(length, 3),
            "stress_mpa": round(stress_mpa, 1),
            "sf": round(mat["strength_mpa"] / stress_mpa, 3),
            "hover_deflection_mm": round(hover_force / stiffness * 1000, 2),
            "deflection_ratio": round(hover_force / stiffness / length, 5),
        }

    def arm_frequency(self, payload_kg: float) -> dict:
        """1re fréquence du bras et écart relatif aux bandes 1P et passage de pales,
        balayées du stationnaire à vide au stationnaire à pleine charge."""
        e_pa, length = self.spec["arm_material"]["young_gpa"] * 1e9, self.arm_free_m
        stiffness = 3 * e_pa * self.arm_inertia_m4 / length**3
        moving = self.tip_mass_per_arm_kg + 0.24 * self.arm_tube_kg
        f1 = math.sqrt(stiffness / moving) / (2 * math.pi)
        rev_hz = [self.tip_speed(m * self.g) / (math.pi * self.diameter_m)
                  for m in (self.mass_kg, self.mass_kg + payload_kg)]
        blades = self.spec["propulsion"]["blades"]

        def distance(low: float, high: float) -> float:
            if low <= f1 <= high:
                return 0.0
            return min(abs(f1 - low) / low, abs(f1 - high) / high)

        one_p = (min(rev_hz), max(rev_hz))
        blade_pass = (blades * one_p[0], blades * one_p[1])
        return {"f1_hz": round(f1, 1), "one_p_hz": [round(v, 1) for v in one_p],
                "blade_pass_hz": [round(v, 1) for v in blade_pass],
                "separation": round(min(distance(*one_p), distance(*blade_pass)), 3)}

    def payload_checks(self, payload_kg: float, edition: dict) -> tuple[dict, dict]:
        """Contrôles qui dépendent de la charge ; renvoie (marges, détails). Marge >= 0 = respecté."""
        s = self.spec
        margins, mission = s["margins"], self.mission(payload_kg, edition)
        loaded_n = (self.mass_kg + payload_kg) * self.g
        usable_wh = self.battery_wh * s["batteries"]["usable_fraction"]
        needed_wh = mission["energy_wh"] * (1 + s["mission"]["energy_reserve_fraction"])
        tw = self.max_static_thrust_n() / loaded_n
        demand_w = self.hover_power(margins["thrust_to_weight_min"] * loaded_n) / self.eta
        arm = self.arm_checks(payload_kg)
        checks = {
            "energy": usable_wh / needed_wh - 1,
            "thrust_to_weight": tw / margins["thrust_to_weight_min"] - 1,
            "battery_power": self.battery_max_w / demand_w - 1,
            "arm_strength": arm["sf"] / margins["arm_safety_factor_min"] - 1,
            "arm_deflection": margins["arm_deflection_max_ratio"] / arm["deflection_ratio"] - 1,
        }
        details = {"mission": mission, "usable_wh": round(usable_wh, 1), "needed_wh": round(needed_wh, 1),
                   "thrust_to_weight": round(tw, 3), "peak_demand_kw": round(demand_w / 1000, 2),
                   "battery_max_kw": round(self.battery_max_w / 1000, 2),
                   "hover_tip_speed_m_s": round(self.tip_speed(loaded_n), 1),
                   "arm": arm}
        return checks, details


def max_payload(vehicle: Vehicle, edition: dict, step_kg: float, max_steps: int = 400) -> dict:
    """Plus grande charge (multiple du plus petit disque) qui passe tous les contrôles."""

    def passes(k: int) -> bool:
        checks, _ = vehicle.payload_checks(k * step_kg, edition)
        return all(v >= 0 for v in checks.values())

    if not passes(0):
        best = -1
    else:
        lo, hi = 0, max_steps
        if passes(hi):
            lo = hi
        while hi - lo > 1:
            mid = (lo + hi) // 2
            lo, hi = (mid, hi) if passes(mid) else (lo, mid)
        best = lo
    probe = max(best, 0) * step_kg
    fail_checks, _ = vehicle.payload_checks((best + 1) * step_kg, edition)
    limiting = sorted((name for name, v in fail_checks.items() if v < 0), key=lambda n: fail_checks[n])
    checks, details = vehicle.payload_checks(probe, edition)
    return {"payload_kg": round(probe, 3) if best >= 0 else 0.0, "flyable_empty": best >= 0,
            "limiting_factors": limiting, "checks_at_max": {k: round(v, 4) for k, v in checks.items()},
            "details_at_max": details}
