"""Épreuve simulée DARPA Lift (MuJoCo) : l'examinateur, indépendant de l'agent.

L'agent fournit un dossier de conception :
  drone.xml    modèle MJCF : un corps « drone » avec <freejoint/>, sans autre articulation ; des sites
               « rotor_* » dont l'axe z local est l'axe de poussée ; un site « payload_attach » ;
               des geoms « motor_* » et « battery » portant leurs masses.
  design.json  {"rotors": [{"site", "spin" (+1/-1), "prop_diameter_m", "motor_max_power_w"}],
                "battery": {"energy_wh", "max_power_w", "mass_kg"}, "cruise_speed_m_s", "components": [...]}

L'épreuve impose la physique (poussée et puissance par la théorie de la quantité de mouvement,
batterie, traînée), le pilote automatique, le parcours et le score. Elle renvoie un résumé, la
télémétrie (10 Hz) et la trajectoire (5 Hz) qui sert à produire la vidéo.
"""

from __future__ import annotations

import csv
import io
import json
import math
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np

from ..spec import REPO_ROOT, load_spec

SPEC_PATH = REPO_ROOT / "spec" / "lift_exam.yaml"
LB = 0.45359237


def exam_spec() -> dict:
    return load_spec(SPEC_PATH)


# --- dossier de conception -------------------------------------------------------------------------
def load_assets(design_dir: Path) -> dict[str, bytes]:
    """Maillages référencés en relatif par le dossier compilé (meshes/*.stl), pour MuJoCo en mémoire."""
    folder = Path(design_dir) / "meshes"
    return {f"meshes/{f.name}": f.read_bytes() for f in sorted(folder.glob("*.stl"))} if folder.exists() else {}


def load_package(design_dir: Path) -> tuple[str, dict]:
    design_dir = Path(design_dir)
    xml_path, json_path = design_dir / "drone.xml", design_dir / "design.json"
    if not xml_path.exists() or not json_path.exists():
        raise FileNotFoundError(f"drone.xml et design.json attendus dans {design_dir}")
    return xml_path.read_text(encoding="utf-8"), json.loads(json_path.read_text(encoding="utf-8"))


def _payload_stack(payload_kg: float, step_lb: float) -> tuple[float, float]:
    pounds = math.floor(payload_kg / LB / step_lb + 1e-9) * step_lb
    return pounds * LB, pounds


def _child(parent, tag):
    found = parent.find(tag)
    return found if found is not None else ET.SubElement(parent, tag)


MASS_FAMILIES = {"motor": ("motor",), "battery": ("battery",), "esc": ("esc",), "prop": ("prop",),
                 "arm": ("arm",), "wiring": ("wiring", "cable"), "avionics": ("avionics",),
                 "gear": ("gear", "leg", "skid"), "frame": ("hub", "frame", "plate")}


def declared_masses(drone_xml: str) -> tuple[dict, dict, list[str]]:
    """Masses explicites par famille de pièces (préfixe du nom de geom) et masse de chaque hélice."""
    masses = {family: 0.0 for family in MASS_FAMILIES}
    props, issues = {}, []
    for geom in ET.fromstring(drone_xml).iter("geom"):
        name = (geom.get("name") or "").lower()
        family = next((f for f, prefixes in MASS_FAMILIES.items() if name.startswith(prefixes)), None)
        if family is None:
            continue
        if geom.get("mass") is None:
            issues.append(f"geom « {name} » : attribut mass explicite requis")
            continue
        masses[family] += float(geom.get("mass"))
        if family == "prop":
            props[name] = float(geom.get("mass"))
    return masses, props, issues


def build_model_xml(drone_xml: str, payload_kg: float, spec: dict) -> str:
    """Ajoute sol, lumière, charge (disques) soudée sous le site payload_attach, et réglages de rendu."""
    root = ET.fromstring(drone_xml)
    if root.tag != "mujoco":
        raise ValueError("drone.xml doit avoir <mujoco> pour racine")
    option = _child(root, "option")
    option.set("timestep", str(spec["physics"]["timestep_s"]))
    option.set("gravity", f"0 0 {-spec['physics']['gravity_m_s2']}")
    visual = _child(root, "visual")
    glob = _child(visual, "global")
    glob.set("offwidth", "1280")
    glob.set("offheight", "720")
    quality = _child(visual, "quality")
    quality.set("shadowsize", "4096")
    visual_map = _child(visual, "map")
    visual_map.set("znear", "0.005")  # plans de coupe relatifs à l'étendue de la scène (fixée à 10 m)
    visual_map.set("zfar", "300")
    statistic = _child(root, "statistic")
    statistic.set("extent", "10")
    statistic.set("center", "0 0 1")
    asset = _child(root, "asset")
    ET.SubElement(asset, "texture", name="exam_grid", type="2d", builtin="checker", rgb1=".82 .84 .86",
                  rgb2=".72 .75 .78", width="512", height="512")
    ET.SubElement(asset, "material", name="exam_floor", texture="exam_grid", texrepeat="400 400")
    ET.SubElement(asset, "texture", name="exam_sky", type="skybox", builtin="gradient", rgb1=".75 .85 .95",
                  rgb2=".95 .97 1", width="256", height="256")
    world = root.find("worldbody")
    if world is None:
        raise ValueError("<worldbody> manquant")
    ET.SubElement(world, "geom", name="exam_floor", type="plane", size="6000 6000 1", material="exam_floor")
    ET.SubElement(world, "light", name="exam_sun", directional="true", pos="0 0 100", dir="-0.3 0.2 -1",
                  castshadow="true")
    drone = next((b for b in world.iter("body") if b.get("name") == "drone"), None)
    if drone is None:
        raise ValueError("corps « drone » introuvable")
    mass, _ = _payload_stack(payload_kg, spec["rules"]["payload_step_lb"])
    if mass > 0:
        stack_h = max(0.03, 0.055 * math.ceil(mass / (45 * LB)))
        payload = ET.SubElement(world, "body", name="payload", pos="0 0 -1")
        ET.SubElement(payload, "freejoint", name="payload_free")
        ET.SubElement(payload, "geom", name="payload_plates", type="cylinder", size=f"0.225 {stack_h / 2:.4f}",
                      mass=f"{mass:.4f}", rgba=".12 .12 .13 1")
        equality = _child(root, "equality")
        ET.SubElement(equality, "weld", name="payload_hook", body1="drone", body2="payload",
                      relpose="0 0 0 0 0 0 0")
    return ET.tostring(root, encoding="unicode")


def check_package(drone_xml: str, design: dict, spec: dict | None = None, payload_kg: float | None = None,
                  assets: dict[str, bytes] | None = None) -> dict:
    """Contrôles statiques : structure du modèle, masses minimales, hélices, bras, batterie, plausibilité,
    marge de poussée (pour la charge donnée). Sans simulation."""
    import mujoco

    spec = spec or exam_spec()
    issues, warnings, near_limits = [], [], []
    try:
        model = mujoco.MjModel.from_xml_string(build_model_xml(drone_xml, 0.0, spec), assets or {})
    except Exception as exc:  # MJCF invalide
        return {"ok": False, "issues": [f"MJCF invalide : {exc}"], "warnings": [], "near_limits": []}
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)
    body = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "drone")
    drone_mass = float(model.body_subtreemass[body])
    subtree = [b for b in range(model.nbody) if _is_descendant(model, b, body)]
    joints = [j for j in range(model.njnt) if model.jnt_bodyid[j] in subtree]
    if len(joints) != 1 or model.jnt_type[joints[0]] != mujoco.mjtJoint.mjJNT_FREE or model.jnt_bodyid[joints[0]] != body:
        issues.append("le corps « drone » doit avoir exactement un <freejoint/> et aucune autre articulation")
    if mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SITE, "payload_attach") < 0:
        issues.append("site « payload_attach » manquant")
    phys, plaus, floors, struct = spec["physics"], spec["plausibility"], spec["mass_floors"], spec["structure"]
    g = phys["gravity_m_s2"]

    def near(value, limit, label):
        if limit and value >= limit * (1 - plaus["near_limit_fraction"]):
            near_limits.append(f"{label} : {value:.1f} pour un plafond de {limit:.1f}")

    masses, prop_masses, mass_issues = declared_masses(drone_xml)
    issues += mass_issues

    # Rotors : positions, recouvrement, coaxialité, poussée max.
    rotors = design.get("rotors") or []
    if len(rotors) < 3:
        issues.append("au moins 3 rotors déclarés dans design.json")
    origin = data.xpos[body]
    info = []
    for i, rotor in enumerate(rotors):
        site = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SITE, rotor.get("site", ""))
        diameter, power = float(rotor.get("prop_diameter_m", 0)), float(rotor.get("motor_max_power_w", 0))
        if site < 0:
            issues.append(f"rotor {i} : site « {rotor.get('site')} » introuvable")
            continue
        if diameter <= 0 or power <= 0 or rotor.get("spin") not in (1, -1):
            issues.append(f"rotor {i} : prop_diameter_m, motor_max_power_w et spin (+1/-1) requis")
            continue
        info.append({"site": rotor["site"], "pos": data.site_xpos[site] - origin, "diameter_m": diameter, "power_w": power})
    penalty = [0.0] * len(info)
    tol = plaus["rotor_overlap_tolerance"]
    for i in range(len(info)):
        for j in range(i + 1, len(info)):
            a, b = info[i], info[j]
            dh = float(np.linalg.norm((a["pos"] - b["pos"])[:2]))
            dv = abs(float(a["pos"][2] - b["pos"][2]))
            dmin = min(a["diameter_m"], b["diameter_m"])
            needed = (a["diameter_m"] + b["diameter_m"]) / 2 * (1 + tol)
            if dh >= needed:
                continue
            if dv >= plaus["overlap_min_vertical_fraction"] * dmin:
                # Hélices décalées en hauteur (ou coaxiales) : permis, pénalité selon la surface recouverte.
                frac = _overlap_fraction(a["diameter_m"] / 2, b["diameter_m"] / 2, dh)
                penalty[i] += plaus["overlap_power_penalty"] * frac
                penalty[j] += plaus["overlap_power_penalty"] * frac
            else:
                issues.append(f"hélices {a['site']} et {b['site']} se chevauchent dans le même plan : jeu "
                              f"{100 * (dh - needed):+.0f} cm (entraxe {dh:.2f} m, minimum {needed:.2f} m) ; décaler en "
                              f"hauteur d'au moins {plaus['overlap_min_vertical_fraction'] * dmin:.2f} m ou écarter")
    coaxial = {i for i, p in enumerate(penalty) if p > 0}
    total_thrust, total_power = 0.0, 0.0
    for i, r in enumerate(info):
        factor = 1.0 + penalty[i]
        r["power_factor"] = round(factor, 3)
        area = math.pi * r["diameter_m"] ** 2 / 4
        r["max_thrust_n"] = round((r["power_w"] / factor * phys["powertrain_efficiency"] * phys["figure_of_merit"]
                                   * math.sqrt(2 * phys["air_density_kg_m3"] * area)) ** (2 / 3), 1)
        r["coaxial"] = i in coaxial  # recouvrement (coaxial ou décalé en hauteur)
        total_thrust += r["max_thrust_n"]
        total_power += r["power_w"]

    if plaus.get("require_compiled"):
        import hashlib

        if design.get("compiled_by") != "assembly_compiler" or design.get("xml_sha1") != hashlib.sha1(drone_xml.encode("utf-8")).hexdigest():
            issues.append("dossier non compilé ou modifié à la main : décrire l'assemblage et utiliser assembly_compile")

    # Moteurs et batterie.
    if masses["motor"] <= 0:
        issues.append("aucune geom « motor_* » avec une masse")
    else:
        specific = total_power / masses["motor"]
        if specific > plaus["motor_specific_power_max_w_kg"]:
            issues.append(f"puissance moteur {specific:.0f} W/kg > {plaus['motor_specific_power_max_w_kg']} W/kg")
        near(specific, plaus["motor_specific_power_max_w_kg"], "puissance massique moteur (W/kg)")
    battery = design.get("battery") or {}
    energy, bmass, bpower = float(battery.get("energy_wh", 0)), float(battery.get("mass_kg", 0)), float(battery.get("max_power_w", 0))
    if energy <= 0 or bmass <= 0 or bpower <= 0:
        issues.append("battery.energy_wh, battery.max_power_w et battery.mass_kg requis")
    else:
        if abs(masses["battery"] - bmass) > 0.05 * bmass:
            issues.append(f"masse des geoms « battery* » {masses['battery']:.2f} kg ≠ déclarée {bmass:.2f} kg")
        wh_kg, c_rate = energy / bmass, bpower / energy
        tier = next((t for t in plaus["battery_tiers"] if wh_kg <= t["max_wh_kg"]), None)
        if tier is None:
            issues.append(f"énergie massique {wh_kg:.0f} Wh/kg > {plaus['battery_tiers'][-1]['max_wh_kg']} Wh/kg au niveau du pack")
        else:
            if c_rate > tier["max_c"]:
                issues.append(f"décharge {c_rate:.1f} C > {tier['max_c']} C pour un pack à {wh_kg:.0f} Wh/kg")
            near(wh_kg, tier["max_wh_kg"], "énergie massique batterie (Wh/kg)")
            near(c_rate, tier["max_c"], "décharge batterie (C)")

    # Masses minimales des autres pièces.
    kw = total_power / 1000
    floors_needed = {"esc": floors["esc_kg_per_kw"] * kw, "wiring": floors["wiring_kg_per_kw"] * kw,
                     "avionics": floors["avionics_kg"], "gear": floors["gear_fraction"] * drone_mass,
                     "frame": floors["frame_fraction"] * drone_mass}
    for family, minimum in floors_needed.items():
        if masses[family] < minimum - 1e-6:
            issues.append(f"pièces « {family} » : {masses[family]:.2f} kg < minimum {minimum:.2f} kg")
    for r in info:
        minimum = floors["prop_kg_at_1m"] * r["diameter_m"] ** floors["prop_exponent"]
        name = next((n for n in prop_masses if n.endswith(r["site"].split("_", 1)[-1])), None)
        declared = prop_masses.get(name) if name else None
        if declared is None:
            declared = masses["prop"] / max(len(info), 1)
        if declared < minimum - 1e-6:
            issues.append(f"hélice de {r['diameter_m']:.2f} m : {declared:.2f} kg < minimum {minimum:.2f} kg")
            break

    # Bras : flexion à poussée max et masse minimale des tubes.
    structure = design.get("structure") or {}
    od, wall, hub_r = (float(structure.get(k, 0)) for k in ("arm_tube_od_m", "arm_tube_wall_m", "hub_radius_m"))
    arm_report = {}
    if od <= 0 or wall <= 0 or wall * 2 >= od:
        issues.append("structure.arm_tube_od_m, arm_tube_wall_m (et hub_radius_m) requis dans design.json")
    else:
        inner = od - 2 * wall
        modulus = math.pi * (od**4 - inner**4) / (32 * od)
        section = math.pi * (od**2 - inner**2) / 4
        lengths = [max(float(np.linalg.norm(r["pos"][:2])) - hub_r, 0.0) for r in info]
        worst = max((r["max_thrust_n"] * L / modulus / 1e6, L) for r, L in zip(info, lengths)) if info else (0, 0)
        limit = struct["strength_mpa"] / struct["safety_factor"]
        arm_report = {"max_stress_mpa": round(worst[0], 1), "allowed_mpa": round(limit, 1), "longest_arm_m": round(max(lengths or [0]), 3)}
        if worst[0] > limit:
            issues.append(f"bras trop faibles : {worst[0]:.0f} MPa à poussée max > {limit:.0f} MPa admissibles "
                          f"(tube Ø {od * 1000:.0f} × {wall * 1000:.1f} mm, bras de {worst[1]:.2f} m)")
        tube_mass = struct["density_kg_m3"] * section * sum(lengths)
        if masses["arm"] < 0.9 * tube_mass:
            issues.append(f"geoms « arm* » : {masses['arm']:.2f} kg < masse des tubes déclarés {tube_mass:.2f} kg")

    if drone_mass >= spec["rules"]["aircraft_mass_max_kg"]:
        warnings.append(f"masse aéronef {drone_mass:.2f} kg ≥ {spec['rules']['aircraft_mass_max_kg']} kg : hors règlement")
    twr_min = plaus["thrust_to_weight_min"]
    max_payload_margin = total_thrust / (twr_min * g) - drone_mass
    result = {"ok": not issues, "issues": issues, "warnings": warnings, "near_limits": near_limits,
              "exam_version": spec.get("version", 1), "aircraft_mass_kg": round(drone_mass, 3),
              "rotors": [{k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items() if k != "pos"} for r in info],
              "max_static_thrust_n": round(total_thrust, 1),
              "thrust_to_weight_empty": round(total_thrust / (drone_mass * g), 2) if drone_mass else None,
              "max_payload_for_thrust_margin_kg": round(max_payload_margin, 2),
              "masses_by_family_kg": {k: round(v, 3) for k, v in masses.items()},
              "minimum_masses_kg": {k: round(v, 3) for k, v in floors_needed.items()}, "arms": arm_report}
    if payload_kg is not None and payload_kg > max_payload_margin:
        result["ok"] = False
        weight = (drone_mass + payload_kg) * g
        result["issues"].append(f"marge de poussée : poussée max {total_thrust:.0f} N < {twr_min} × poids chargé "
                                f"{weight:.0f} N = {twr_min * weight:.0f} N ; charge max admissible {max_payload_margin:.1f} kg")
    return result


def _overlap_fraction(r1: float, r2: float, d: float) -> float:
    """Aire de recouvrement de deux disques rapportée à l'aire du plus petit."""
    if d >= r1 + r2:
        return 0.0
    small = min(r1, r2)
    if d <= abs(r1 - r2):
        return 1.0
    a1 = r1**2 * math.acos((d**2 + r1**2 - r2**2) / (2 * d * r1))
    a2 = r2**2 * math.acos((d**2 + r2**2 - r1**2) / (2 * d * r2))
    a3 = 0.5 * math.sqrt(max((-d + r1 + r2) * (d + r1 - r2) * (d - r1 + r2) * (d + r1 + r2), 0.0))
    return (a1 + a2 - a3) / (math.pi * small**2)


def _is_descendant(model, b, ancestor) -> bool:
    while b > 0:
        if b == ancestor:
            return True
        b = model.body_parentid[b]
    return b == ancestor


# --- mission de référence ------------------------------------------------------------------------------
class Mission:
    """Consigne de position/vitesse en fonction du temps, par phases."""

    def __init__(self, spec: dict, z0: float, cruise_speed: float, with_payload: bool):
        rules, mis = spec["rules"], spec["mission"]
        self.h, self.z0, self.v = rules["cruise_altitude_m"] + z0, z0, cruise_speed
        self.acc = mis["cruise_accel_m_s2"]
        self.phases = []
        t = 0.0

        def add(name, duration, **info):
            nonlocal t
            self.phases.append({"name": name, "t0": t, "t1": t + duration, **info})
            t += duration

        add("settle", mis["settle_s"])
        add("climb", (self.h - z0) / mis["climb_rate_m_s"], rate=mis["climb_rate_m_s"])
        add("cruise_loaded", self._leg_time(rules["loaded_distance_m"]), x0=0.0, dist=rules["loaded_distance_m"])
        add("hover_drop", mis["hover_before_drop_s"] + mis["hover_after_drop_s"], drop_at=mis["hover_before_drop_s"])
        x1 = rules["loaded_distance_m"]
        add("cruise_empty", self._leg_time(rules["unloaded_distance_m"]), x0=x1, dist=-rules["unloaded_distance_m"])
        add("descent", (self.h - z0) / mis["descent_rate_m_s"], rate=mis["descent_rate_m_s"])
        add("landing", 5.0)
        self.x_end = x1 - rules["unloaded_distance_m"]
        self.duration = t

    def _leg_time(self, dist):
        t_acc = self.v / self.acc
        d_acc = self.v * t_acc  # accélération + freinage
        return 2 * t_acc + (dist - d_acc) / self.v if dist > d_acc else 2 * math.sqrt(dist / self.acc)

    def _leg(self, s, dist):
        """Position, vitesse, accélération le long d'une branche de longueur |dist| au temps s."""
        d, sign = abs(dist), math.copysign(1, dist)
        t_acc = min(self.v / self.acc, math.sqrt(d / self.acc))
        vmax = self.acc * t_acc
        t_cruise = max(0.0, (d - vmax * t_acc) / self.v) if vmax >= self.v - 1e-9 else 0.0
        if s < t_acc:
            x, v, a = 0.5 * self.acc * s**2, self.acc * s, self.acc
        elif s < t_acc + t_cruise:
            x, v, a = 0.5 * self.acc * t_acc**2 + vmax * (s - t_acc), vmax, 0.0
        else:
            r = min(s - t_acc - t_cruise, t_acc)
            x = 0.5 * self.acc * t_acc**2 + vmax * t_cruise + vmax * r - 0.5 * self.acc * r**2
            v, a = vmax - self.acc * r, -self.acc if r < t_acc else 0.0
        return sign * x, sign * v, sign * a

    def reference(self, t):
        for ph in self.phases:
            if t < ph["t1"]:
                break
        s = t - ph["t0"]
        name = ph["name"]
        pos, vel, acc = np.array([0.0, 0.0, self.z0]), np.zeros(3), np.zeros(3)
        if name == "settle":
            return name, pos, vel, acc
        if name == "climb":
            pos[2] = min(self.z0 + ph["rate"] * s, self.h)
            vel[2] = ph["rate"] if pos[2] < self.h else 0.0
            return name, pos, vel, acc
        pos[2] = self.h
        if name == "cruise_loaded":
            pos[0], vel[0], acc[0] = self._leg(s, ph["dist"])
        elif name == "hover_drop":
            pos[0] = self.phases[2]["dist"]
        elif name == "cruise_empty":
            x, vel[0], acc[0] = self._leg(s, ph["dist"])
            pos[0] = ph["x0"] + x
        else:
            pos[0] = self.x_end
            if name == "descent":
                pos[2] = max(self.h - ph["rate"] * s, self.z0)
                vel[2] = -ph["rate"] if pos[2] > self.z0 else 0.0
            else:
                pos[2] = self.z0
        return name, pos, vel, acc


# --- simulation ----------------------------------------------------------------------------------------
def _vee(m):
    return np.array([m[2, 1], m[0, 2], m[1, 0]])


def run_exam(drone_xml: str, design: dict, payload_kg: float, cruise_speed: float | None = None,
             spec: dict | None = None, scenario: str = "nominal", assets: dict[str, bytes] | None = None) -> dict:
    import copy

    import mujoco

    spec = copy.deepcopy(spec or exam_spec())
    scenarios = spec.get("scenarios", {"nominal": {}})
    if scenario not in scenarios:
        return {"ok": False, "reason": f"scénario inconnu : {scenario} (disponibles : {sorted(scenarios)})"}
    setting = scenarios[scenario]
    if "air_density_kg_m3" in setting:
        spec["physics"]["air_density_kg_m3"] = setting["air_density_kg_m3"]
    wind_base = np.array(setting.get("wind_m_s", [0.0, 0.0, 0.0]), dtype=float)
    gust = float(setting.get("gust_m_s", 0.0))
    gust_period = float(setting.get("gust_period_s", 3.0))
    thermal = spec.get("motor_thermal", {})
    ambient = float(setting.get("ambient_c", thermal.get("ambient_c", 25)))

    def wind_at(t):
        if gust <= 0:
            return wind_base
        w = 2 * math.pi / gust_period
        return wind_base + gust * np.array([0.6 * math.sin(w * t) + 0.4 * math.sin(2.3 * w * t + 1.0),
                                            0.5 * math.sin(0.7 * w * t + 2.0), 0.2 * math.sin(1.9 * w * t + 0.5)])
    phys, fail, rules = spec["physics"], spec["failure"], spec["rules"]
    payload_requested = float(payload_kg)
    payload_kg, payload_lb = _payload_stack(payload_kg, spec["rules"]["payload_step_lb"])
    check = check_package(drone_xml, design, spec, payload_kg=payload_kg, assets=assets)
    if not check["ok"]:
        return {"ok": True, "exam_version": spec.get("version", 1), "passed": False,
                "failure": {"reason": "dossier refusé", "details": check["issues"]}, "check": check, "score": -2.0,
                "payload_kg": round(payload_kg, 3), "payload_requested_kg": round(payload_requested, 3),
                "aircraft_mass_kg": check.get("aircraft_mass_kg")}
    cruise = float(cruise_speed or design.get("cruise_speed_m_s") or spec["mission"]["default_cruise_speed_m_s"])
    cruise = min(max(cruise, 1.0), spec["mission"]["max_cruise_speed_m_s"])
    full_xml = build_model_xml(drone_xml, payload_kg, spec)
    model = mujoco.MjModel.from_xml_string(full_xml, assets or {})
    data = mujoco.MjData(model)
    drone = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "drone")
    payload = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "payload")
    hook = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_EQUALITY, "payload_hook")
    attach = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SITE, "payload_attach")
    dq = model.jnt_qposadr[model.body_jntadr[drone]]
    dv = model.jnt_dofadr[model.body_jntadr[drone]]

    # Position initiale : charge sous le site d'accroche, point le plus bas à 2 cm du sol.
    mujoco.mj_forward(model, data)
    if payload >= 0:
        pq = model.jnt_qposadr[model.body_jntadr[payload]]
        half = model.geom_size[model.body_geomadr[payload]][1]
        data.qpos[pq:pq + 3] = data.site_xpos[attach] - np.array([0, 0, half + 0.02])
        data.qpos[pq + 3:pq + 7] = [1, 0, 0, 0]
        mujoco.mj_forward(model, data)
        rel = _relpose(data, drone, payload)  # relpose de la soudure = pose initiale relative
        model.eq_data[hook][3:6], model.eq_data[hook][6:10] = rel[0], rel[1]
    lows = [data.geom_xpos[g][2] - model.geom_rbound[g] for g in range(model.ngeom)
            if model.geom_bodyid[g] != 0 and model.geom_rbound[g] > 0]
    shift = 0.02 - min(lows)
    data.qpos[dq + 2] += shift
    if payload >= 0:
        data.qpos[pq + 2] += shift
    mujoco.mj_forward(model, data)

    m_drone = float(model.body_subtreemass[drone])
    g = phys["gravity_m_s2"]
    rho, fm, kappa, eta = phys["air_density_kg_m3"], phys["figure_of_merit"], phys["induced_power_factor"], phys["powertrain_efficiency"]
    rotors = []
    factors = {r["site"]: r.get("power_factor", 1.0) for r in check["rotors"]}
    for r in design["rotors"]:
        site = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SITE, r["site"])
        area = math.pi * r["prop_diameter_m"] ** 2 / 4
        factor = factors.get(r["site"], 1.0)
        peak = float(r.get("motor_peak_power_w") or r["motor_max_power_w"])
        t_max = (max(peak, r["motor_max_power_w"]) / factor * eta * fm * math.sqrt(2 * rho * area)) ** (2 / 3)
        mass_m = float(r.get("motor_mass_kg") or 1.0)
        loss = thermal.get("loss_fraction", 0.12)
        rotors.append({"site": site, "spin": r["spin"], "area": area, "t_max": t_max, "factor": factor,
                       "cq": phys["torque_to_thrust_per_m"] * r["prop_diameter_m"],
                       "heat_cap": mass_m * thermal.get("heat_capacity_j_kgk", 500),
                       "r_th": thermal.get("rated_rise_k", 80) / (r["motor_max_power_w"] * loss), "temp": ambient})
    t_max = np.array([r["t_max"] for r in rotors])

    # Aire frontale (boîte englobante hors hélices) pour la traînée.
    pts = []
    for gi in range(model.ngeom):
        if _is_descendant(model, model.geom_bodyid[gi], drone) and not (mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_GEOM, gi) or "").startswith("prop"):
            c, rb = data.geom_xpos[gi], model.geom_rbound[gi]
            pts += [c - rb, c + rb]
    pts = np.array(pts)
    frontal = float((pts[:, 1].max() - pts[:, 1].min()) * (pts[:, 2].max() - pts[:, 2].min()))
    cda_body = phys["body_drag_coefficient"] * frontal
    span = float(max(pts[:, 0].max() - pts[:, 0].min(), pts[:, 1].max() - pts[:, 1].min()))

    battery = design["battery"]
    usable_wh = battery["energy_wh"] * phys["battery_usable_fraction"]
    p_batt_max = battery["max_power_w"]

    z0 = float(data.subtree_com[drone][2])
    J = _rot_inertia(model, data, dv)  # constante dans le repère du drone (corps rigide)
    mission = Mission(spec, z0, cruise, payload >= 0)
    ctrl_every = max(1, round(1 / (phys["control_hz"] * model.opt.timestep)))
    dt_ctrl = ctrl_every * model.opt.timestep
    log_every = max(1, round(phys["control_hz"] / spec["telemetry"]["log_hz"]))
    traj_every = max(1, round(phys["control_hz"] / spec["telemetry"]["trajectory_hz"]))

    energy_wh, attached, dead = 0.0, payload >= 0, False
    thrusts = np.zeros(len(rotors))
    power = 0.0
    telemetry, trajectory = [], []
    phase_stats: dict[str, dict] = {}
    failure = None
    max_tilt = max_err = 0.0
    max_motor_temp = ambient
    climb_reached = False
    k = 0
    t_end_limit = mission.duration * 1.5 + 60
    while data.time < t_end_limit:
        t = data.time
        name, p_ref, v_ref, a_ref = mission.reference(t)
        if k % ctrl_every == 0:
            R = data.xmat[drone].reshape(3, 3)
            com = data.subtree_com[drone].copy()
            vel = data.qvel[dv:dv + 3].copy()
            omega = data.qvel[dv + 3:dv + 6].copy()
            m_tot = m_drone + (model.body_mass[payload] if attached else 0.0)
            wind = wind_at(t)
            rel = vel - wind
            speed = float(np.linalg.norm(rel))  # vitesse air
            if name == "hover_drop" and attached and t - mission.phases[3]["t0"] >= mission.phases[3]["drop_at"]:
                data.eq_active[hook] = 0
                attached = False
            if name == "settle" or dead:
                thrusts[:] = 0.0
            else:
                err = p_ref - com
                a_des = 1.2 * err + 2.2 * (v_ref - vel) + a_ref
                horiz = np.linalg.norm(a_des[:2])
                if horiz > 4.0:
                    a_des[:2] *= 4.0 / horiz
                a_des[2] = np.clip(a_des[2], -4.0, 4.0)
                cda = cda_body + (phys["payload_cda_m2"] if attached else 0.0)
                f_des = m_tot * (a_des + np.array([0, 0, g])) + 0.5 * rho * cda * float(np.linalg.norm(vel)) * vel
                z_des = f_des / max(np.linalg.norm(f_des), 1e-6)
                tilt_lim = math.radians(35)
                if math.acos(np.clip(z_des[2], -1, 1)) > tilt_lim:
                    h = z_des[:2] / max(np.linalg.norm(z_des[:2]), 1e-9)
                    z_des = np.array([h[0] * math.sin(tilt_lim), h[1] * math.sin(tilt_lim), math.cos(tilt_lim)])
                y_des = np.cross(z_des, [1.0, 0.0, 0.0])
                y_des /= max(np.linalg.norm(y_des), 1e-9)
                x_des = np.cross(y_des, z_des)
                R_des = np.column_stack([x_des, y_des, z_des])
                e_R = 0.5 * _vee(R_des.T @ R - R.T @ R_des)
                wn = 2 * math.pi * 1.2
                tau = J @ (-(wn**2) * e_R - 2 * 0.9 * wn * omega) + np.cross(omega, J @ omega)
                thrust_cmd = float(f_des @ R[:, 2])
                B = np.zeros((4, len(rotors)))
                for i, r in enumerate(rotors):
                    z_i = R.T @ data.site_xmat[r["site"]].reshape(3, 3)[:, 2]
                    r_i = R.T @ (data.site_xpos[r["site"]] - com)
                    B[0, i] = z_i[2]
                    B[1:, i] = np.cross(r_i, z_i) + r["cq"] * r["spin"] * z_i
                thrusts = np.clip(np.linalg.pinv(B) @ np.concatenate([[thrust_cmd], tau]), 0.0, t_max)
            # Puissance électrique (quantité de mouvement + Glauert) et limite batterie.
            power = _power(thrusts, rotors, speed, rho, fm, kappa, eta)
            power_limited = power > p_batt_max > 0
            if power_limited:
                thrusts *= (p_batt_max / power) ** (2 / 3)
                power = _power(thrusts, rotors, speed, rho, fm, kappa, eta)
            energy_wh += power * dt_ctrl / 3600
            for r_i, p_i in zip(rotors, _rotor_powers(thrusts, rotors, speed, rho, fm, kappa, eta)):
                q_loss = p_i * thermal.get("loss_fraction", 0.12)
                r_i["temp"] += (q_loss - (r_i["temp"] - ambient) / r_i["r_th"]) * dt_ctrl / r_i["heat_cap"]
            motor_temp = max(r_i["temp"] for r_i in rotors)
            max_motor_temp = max(max_motor_temp, motor_temp)
            if motor_temp > thermal.get("max_winding_c", 150) and failure is None:
                failure = {"reason": "surchauffe moteur", "t": round(t, 1), "phase": name}
            if energy_wh >= usable_wh and not dead:
                dead = True
                failure = failure or {"reason": "batterie épuisée", "t": round(t, 1), "phase": name}
            force, torque = np.zeros(3), np.zeros(3)
            origin = data.xipos[drone]
            for i, r in enumerate(rotors):
                z_w = data.site_xmat[r["site"]].reshape(3, 3)[:, 2]
                f_i = thrusts[i] * z_w
                force += f_i
                torque += np.cross(data.site_xpos[r["site"]] - origin, f_i) + r["cq"] * r["spin"] * thrusts[i] * z_w
            force -= 0.5 * rho * cda_body * speed * rel
            data.xfrc_applied[drone, :3], data.xfrc_applied[drone, 3:] = force, torque
            if payload >= 0:
                pv = data.qvel[model.jnt_dofadr[model.body_jntadr[payload]]:][:3] - wind
                data.xfrc_applied[payload, :3] = -0.5 * rho * phys["payload_cda_m2"] * np.linalg.norm(pv) * pv

            tilt = math.degrees(math.acos(np.clip(R[2, 2], -1, 1)))
            err_norm = float(np.linalg.norm(p_ref - com))
            if name not in ("settle",):
                max_tilt = max(max_tilt, tilt)
            if name == "climb" and com[2] >= mission.h - 1.0:
                climb_reached = True
            if name not in ("settle", "climb", "landing"):
                max_err = max(max_err, err_norm)
            st = phase_stats.setdefault(name, {"t_start": round(t, 1), "energy_wh": 0.0, "max_throttle": 0.0,
                                               "power_sum": 0.0, "n": 0, "max_tracking_error_m": 0.0})
            st["t_end"] = round(t, 1)
            st["energy_wh"] += power * dt_ctrl / 3600
            st["max_throttle"] = max(st["max_throttle"], float((thrusts / t_max).max()) if len(t_max) else 0.0)
            st["power_sum"] += power
            st["n"] += 1
            st["max_tracking_error_m"] = max(st["max_tracking_error_m"], err_norm)

            if failure is None:
                if tilt > fail["crash_tilt_deg"] and name != "settle":
                    failure = {"reason": "perte de contrôle (inclinaison)", "t": round(t, 1), "phase": name}
                elif name not in ("settle", "climb", "landing") and err_norm > fail["max_tracking_error_m"]:
                    failure = {"reason": "écart de trajectoire (poussée ou puissance insuffisante)", "t": round(t, 1), "phase": name}
                elif name == "climb" and t - mission.phases[1]["t0"] > (mission.phases[1]["t1"] - mission.phases[1]["t0"]) * fail["climb_timeout_factor"] and not climb_reached:
                    failure = {"reason": "montée impossible", "t": round(t, 1), "phase": name}
                elif name in ("cruise_loaded", "hover_drop", "cruise_empty") and com[2] < fail["min_flight_altitude_m"] + z0:
                    failure = {"reason": "chute", "t": round(t, 1), "phase": name}
            if failure and "context" not in failure:  # état au moment de l'échec, pour le diagnostic
                failure["context"] = {"battery_pct": round(100 * (1 - energy_wh / battery["energy_wh"]), 1),
                                      "motor_temp_max_c": round(motor_temp, 1),
                                      "power_w": round(power, 1), "battery_power_limited": bool(power_limited),
                                      "throttle_max": round(float((thrusts / t_max).max()), 3),
                                      "altitude_m": round(float(com[2] - z0), 2), "tilt_deg": round(tilt, 1),
                                      "tracking_error_m": round(err_norm, 2)}
            if (k // ctrl_every) % log_every == 0:
                telemetry.append({
                    "t": round(t, 2), "phase": name, "x": round(com[0], 2), "y": round(com[1], 2), "z": round(com[2] - z0, 2),
                    "vx": round(vel[0], 2), "vy": round(vel[1], 2), "vz": round(vel[2], 2), "speed": round(speed, 2),
                    "tilt_deg": round(tilt, 2), "x_ref": round(p_ref[0], 2), "z_ref": round(p_ref[2] - z0, 2),
                    "tracking_error_m": round(err_norm, 2), "thrust_total_n": round(float(thrusts.sum()), 1),
                    "throttle_max": round(float((thrusts / t_max).max()), 3), "power_w": round(power, 1),
                    "energy_wh": round(energy_wh, 2), "battery_pct": round(100 * (1 - energy_wh / battery["energy_wh"]), 2),
                    "payload_attached": int(attached), "power_limited": int(power_limited),
                    "motor_temp_max_c": round(motor_temp, 1), "wind_m_s": round(float(np.linalg.norm(wind)), 1)})
            if (k // ctrl_every) % traj_every == 0:
                q = [round(float(v), 5) for v in data.qpos[dq:dq + 7]]
                pq_vals = [round(float(v), 5) for v in data.qpos[pq:pq + 7]] if payload >= 0 else []
                trajectory.append([round(t, 2), name, q, pq_vals])
            if failure and data.time - failure["t"] > 3.0:
                break  # quelques secondes après l'échec, pour la vidéo
            if name == "landing" and data.time >= mission.duration:
                break
        mujoco.mj_step(model, data)
        k += 1

    passed = failure is None and data.time >= mission.duration - 0.1
    rules_ok = m_drone < rules["aircraft_mass_max_kg"]
    ratio = payload_kg / m_drone if m_drone else 0.0
    if passed and rules_ok and payload_kg >= rules["payload_min_kg"]:
        score = round(ratio, 4)
    elif passed and rules_ok:
        score = round(-0.1 * (1 - payload_kg / rules["payload_min_kg"]), 4)
    elif not rules_ok:
        score = -1.5
    else:
        progress = min(1.0, (failure["t"] if failure else data.time) / mission.duration)
        score = round(-1 + 0.9 * progress, 4)
    for st in phase_stats.values():
        st["mean_power_w"] = round(st.pop("power_sum") / max(st.pop("n"), 1), 1)
        st["energy_wh"] = round(st["energy_wh"], 2)
        st["max_throttle"] = round(st["max_throttle"], 3)
        st["max_tracking_error_m"] = round(st["max_tracking_error_m"], 2)
    return {
        "ok": True, "exam_version": spec.get("version", 1), "scenario": scenario,
        "scenario_description": setting.get("description"), "passed": passed, "failure": failure,
        "score": score if scenario == "nominal" else None, "scenario_score": score,
        "max_motor_temp_c": round(max_motor_temp, 1), "ambient_c": ambient,
        "payload_requested_kg": round(payload_requested, 3),
        "aircraft_mass_kg": round(m_drone, 3), "payload_kg": round(payload_kg, 3), "payload_lb": payload_lb,
        "ratio": round(ratio, 3), "rules": {"aircraft_mass_ok": rules_ok, "payload_qualifying": payload_kg >= rules["payload_min_kg"]},
        "cruise_speed_m_s": cruise, "mission_time_s": round(data.time, 1), "planned_time_s": round(mission.duration, 1),
        "energy_used_wh": round(energy_wh, 1), "battery_usable_wh": round(usable_wh, 1),
        "battery_min_pct": round(100 * (1 - energy_wh / battery["energy_wh"]), 1),
        "max_tilt_deg": round(max_tilt, 1), "max_tracking_error_m": round(max_err, 2),
        "phases": phase_stats, "check": check, "frontal_area_m2": round(frontal, 3), "span_m": round(span, 2),
        "telemetry_csv": _to_csv(telemetry), "trajectory": trajectory, "model_xml": full_xml,
    }


def _relpose(data, b1, b2):
    """Pose de b2 dans le repère de b1 (position, quaternion)."""
    import mujoco

    q1inv = np.zeros(4)
    mujoco.mju_negQuat(q1inv, data.xquat[b1])
    pos = np.zeros(3)
    mujoco.mju_rotVecQuat(pos, data.xpos[b2] - data.xpos[b1], q1inv)
    quat = np.zeros(4)
    mujoco.mju_mulQuat(quat, q1inv, data.xquat[b2])
    return pos, quat


def _rot_inertia(model, data, dv):
    import mujoco

    full = np.zeros((model.nv, model.nv))
    mujoco.mj_fullM(model, data, full)  # signature MuJoCo 3.14 : (m, d, dst)
    return full[dv + 3:dv + 6, dv + 3:dv + 6]


def _rotor_powers(thrusts, rotors, speed, rho, fm, kappa, eta):
    out = []
    for t_i, r in zip(thrusts, rotors):
        if t_i <= 0:
            out.append(0.0)
            continue
        vh = math.sqrt(t_i / (2 * rho * r["area"]))
        vi = math.sqrt((-speed**2 + math.sqrt(speed**4 + 4 * vh**4)) / 2)
        out.append(r.get("factor", 1.0) * (kappa * t_i * vi + (1 / fm - kappa) * t_i * vh) / eta)
    return out


def _power(thrusts, rotors, speed, rho, fm, kappa, eta):
    return sum(_rotor_powers(thrusts, rotors, speed, rho, fm, kappa, eta))


def _to_csv(rows: list[dict]) -> str:
    if not rows:
        return ""
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def main() -> None:
    """Point d'entrée distant (RTX 5090) : job JSON sur stdin -> RESULT_JSON sur stdout."""
    import sys

    try:
        job = json.loads(sys.stdin.read())
        import base64

        assets = {name: base64.b64decode(data) for name, data in (job.get("assets") or {}).items()}
        result = run_exam(job["drone_xml"], job["design"], job["payload_kg"], job.get("cruise_speed_m_s"),
                          scenario=job.get("scenario", "nominal"), assets=assets)
    except Exception as exc:
        import traceback

        result = {"ok": False, "reason": f"{type(exc).__name__}: {exc}", "trace": traceback.format_exc(limit=4)}
    print("RESULT_JSON " + json.dumps(result))


if __name__ == "__main__":
    main()
