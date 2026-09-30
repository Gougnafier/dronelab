"""Compilateur d'assemblage : squelette décrit par l'agent -> modèle MuJoCo, dossier d'épreuve, OpenUSD, rendu.

workspace/assemblies/<nom>/assembly.json :
{
  "hub_radius_m": 0.15, "cruise_speed_m_s": 15, "payload_attach_m": [0, 0, -0.12],
  "instances": [
    {"id": "arm_0", "ref": "catalog:tube:...", "fromto_m": [x1, y1, z1, x2, y2, z2]},       tube coupé à longueur
    {"id": "m0", "ref": "catalog:motor:...", "pos_m": [x, y, z], "euler_deg": [0, 0, 0]},   axe moteur = z local
    {"id": "p0", "ref": "catalog:propeller:...", "pos_m": [...]},                           disque normal à z local
    {"id": "w", "ref": "catalog:wiring:...", "length_m": 6, "pos_m": [...]},
    {"id": "mount0", "ref": "part:motor_mount", "pos_m": [...], "euler_deg": [...]},        pièce sur mesure
    ...],
  "rotors": [{"prop": "p0", "motor": "m0", "spin": 1}],
  "connections": [{"a": "arm_0", "b": "mount0", "interface": "tube"}, {"a": "m0", "b": "mount0", "interface": "motor"}]
}
Les masses ne sont jamais déclarées : catalogue sourcé ou volume CAO × densité du matériau.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import shutil
import struct
import subprocess
import sys
from pathlib import Path

import numpy as np

from . import catalog, parts
from .exam import check_package, exam_spec

FAMILY_PREFIX = {"motor": "motor", "propeller": "prop", "battery": "battery", "esc": "esc", "tube": "arm",
                 "avionics": "avionics", "wiring": "wiring", "landing_gear": "gear", "other": "misc"}
ROLE_PREFIX = {"frame": "frame", "mount": "frame", "gear": "gear", "payload": "misc", "other": "misc"}
COLORS = {"motor": ".75 .2 .15 1", "prop": ".9 .92 .95 .35", "battery": ".95 .75 .1 1", "esc": ".2 .45 .85 1",
          "arm": ".08 .08 .09 1", "avionics": ".2 .6 .25 1", "wiring": ".55 .3 .1 1", "gear": ".3 .3 .33 1",
          "frame": ".6 .65 .72 1", "misc": ".5 .5 .5 1"}


def _fmt(values):
    return " ".join(f"{float(v):.5f}" for v in values)


def compile_assembly(root: Path, name: str) -> dict:
    ws = root / "workspace"
    src = (ws / "assemblies" / name / "assembly.json")
    if not src.exists():
        return {"ok": False, "issues": [f"{src} introuvable"]}
    asm = json.loads(src.read_text(encoding="utf-8"))
    cat = catalog.entries(root)
    issues, geoms, sites, assets, components = [], [], [], [], []
    out = ws / "designs" / name
    mesh_files: dict[str, Path] = {}
    by_id: dict[str, dict] = {}

    for inst in asm.get("instances", []):
        iid, ref = inst.get("id"), inst.get("ref", "")
        if not iid or iid in by_id:
            issues.append(f"instance sans id ou id en double : {iid}")
            continue
        kind, _, key = ref.partition(":")
        pos = inst.get("pos_m", [0, 0, 0])
        euler = inst.get("euler_deg", [0, 0, 0])
        if kind == "catalog":
            entry = cat.get(key)
            if entry is None:
                issues.append(f"{iid} : pièce de catalogue inconnue {key}")
                continue
            category, specs = entry["category"], entry["specs"]
            prefix = FAMILY_PREFIX[category]
            gname = f"{prefix}_{iid}"
            if category == "tube":
                ft = inst.get("fromto_m")
                if not ft or len(ft) != 6:
                    issues.append(f"{iid} : un tube se place avec fromto_m [x1, y1, z1, x2, y2, z2]")
                    continue
                length = math.dist(ft[:3], ft[3:])
                mass = specs["mass_per_m_kg"] * length
                geoms.append(f'<geom name="{gname}" type="cylinder" fromto="{_fmt(ft)}" size="{specs["outer_diameter_m"] / 2:.5f}" '
                             f'mass="{mass:.5f}" rgba="{COLORS[prefix]}"/>')
                by_id[iid] = {"category": category, "specs": specs, "pos": np.mean([ft[:3], ft[3:]], axis=0),
                              "length_m": length, "fromto": ft}
            elif category == "wiring":
                length = float(inst.get("length_m", 0))
                if length <= 0:
                    issues.append(f"{iid} : câblage avec length_m > 0")
                    continue
                mass = specs["mass_per_m_kg"] * length
                geoms.append(f'<geom name="{gname}" type="box" pos="{_fmt(pos)}" size="0.03 0.03 0.005" mass="{mass:.5f}" '
                             f'rgba="{COLORS[prefix]}" contype="0" conaffinity="0"/>')
                by_id[iid] = {"category": category, "specs": specs, "pos": np.array(pos)}
            elif category in ("motor", "propeller"):
                if category == "motor":
                    size = f'{specs["diameter_m"] / 2:.5f} {specs["height_m"] / 2:.5f}'
                    extra = ""
                else:
                    size = f'{specs["diameter_m"] / 2:.5f} 0.004'
                    extra = ' contype="0" conaffinity="0"'
                    sites.append(f'<site name="rotor_{iid}" pos="{_fmt(pos)}" euler="{_fmt(euler)}"/>')
                mass = specs["mass_kg"]
                geoms.append(f'<geom name="{gname}" type="cylinder" pos="{_fmt(pos)}" euler="{_fmt(euler)}" size="{size}" '
                             f'mass="{mass:.5f}" rgba="{COLORS[prefix]}"{extra}/>')
                by_id[iid] = {"category": category, "specs": specs, "pos": np.array(pos)}
            else:
                dims = specs.get("dims_m", [0.05, 0.05, 0.02])
                mass = specs["mass_kg"]
                geoms.append(f'<geom name="{gname}" type="box" pos="{_fmt(pos)}" euler="{_fmt(euler)}" '
                             f'size="{_fmt([d / 2 for d in dims])}" mass="{mass:.5f}" rgba="{COLORS[prefix]}"/>')
                by_id[iid] = {"category": category, "specs": specs, "pos": np.array(pos)}
            components.append({"instance": iid, "ref": key, "category": category, "mass_kg": round(mass, 4),
                               "source_url": entry["source_url"]})
        elif kind == "part":
            try:
                pdir = parts.resolve_part(root, key)
            except Exception as exc:
                issues.append(f"{iid} : {exc}")
                continue
            built = json.loads((pdir / "build.json").read_text()) if (pdir / "build.json").exists() else None
            current = parts.part_hash(pdir)
            if not built or built.get("hash") != current:
                issues.append(f"{iid} : pièce {key} non construite ou modifiée depuis (part_build)")
                continue
            if not built.get("ok"):
                issues.append(f"{iid} : pièce {key} refusée à la construction : {built.get('issues')}")
                continue
            fem = parts.fem_status(pdir, current)
            for case in built.get("fem_required", []):
                status = fem.get(case)
                if not status or not status["up_to_date"]:
                    issues.append(f"{iid} : pièce {key}, cas « {case} » non calculé (part_fem)")
                elif not status["ok"]:
                    issues.append(f"{iid} : pièce {key}, cas « {case} » : facteur de sécurité {status['sf']} insuffisant")
            prefix = ROLE_PREFIX.get(built.get("role"), "misc")
            asset = f"mesh_{iid}"
            mesh_files[f"{key}.stl"] = pdir / "part.stl"
            assets.append(f'<mesh name="{asset}" file="meshes/{key}.stl" scale="0.001 0.001 0.001"/>')
            geoms.append(f'<geom name="{prefix}_{iid}" type="mesh" mesh="{asset}" pos="{_fmt(pos)}" euler="{_fmt(euler)}" '
                         f'mass="{built["mass_kg"]:.5f}" rgba="{COLORS[prefix]}"/>')
            spec = json.loads((pdir / "part.json").read_text(encoding="utf-8"))
            by_id[iid] = {"category": "part", "part": key, "spec": spec, "pos": np.array(pos)}
            components.append({"instance": iid, "ref": f"part:{key}", "category": f"sur mesure ({built.get('role')})",
                               "material": built.get("material"), "process": built.get("process"),
                               "mass_kg": built["mass_kg"], "part_hash": current})
        else:
            issues.append(f"{iid} : ref doit commencer par catalog: ou part:")

    # Interfaces déclarées entre instances.
    for con in asm.get("connections", []):
        a, b = by_id.get(con.get("a")), by_id.get(con.get("b"))
        if a is None or b is None or b.get("category") != "part":
            issues.append(f"connexion {con} : « b » doit être une pièce sur mesure existante")
            continue
        interface = next((i for i in b["spec"].get("interfaces", []) if i.get("name") == con.get("interface")), None)
        if interface is None:
            issues.append(f"connexion {con} : interface inconnue sur {b['part']}")
            continue
        params = interface.get("params", {})
        if interface.get("type") == "tube_socket":
            od = a["specs"].get("outer_diameter_m") if a.get("category") == "tube" else None
            if od is None or abs(od - params.get("tube_od_m", -1)) > 0.0005:
                issues.append(f"connexion {con} : tube Ø {od} m ≠ manchon Ø {params.get('tube_od_m')} m")
        elif interface.get("type") == "motor_bolts":
            pattern = a["specs"].get("mount_pattern_mm") if a.get("category") == "motor" else None
            patterns = pattern if isinstance(pattern, list) else [pattern]
            if pattern is None or not any(p is not None and abs(p - params.get("pattern_mm", -1)) <= 0.5 for p in patterns):
                issues.append(f"connexion {con} : motif de fixation moteur {pattern} ≠ pièce {params.get('pattern_mm')} mm")

    # Rotors.
    rotors, props_seen = [], set()
    for r in asm.get("rotors", []):
        prop, motor = by_id.get(r.get("prop")), by_id.get(r.get("motor"))
        if not prop or prop["category"] != "propeller" or not motor or motor["category"] != "motor":
            issues.append(f"rotor {r} : prop (hélice) et motor (moteur) doivent désigner des instances du catalogue")
            continue
        if r.get("spin") not in (1, -1):
            issues.append(f"rotor {r} : spin +1 ou -1")
        if float(np.linalg.norm(prop["pos"] - motor["pos"])) > 0.15:
            issues.append(f"rotor {r} : hélice à plus de 15 cm de son moteur")
        max_prop = motor["specs"].get("max_prop_diameter_m")
        if max_prop and prop["specs"]["diameter_m"] > max_prop * 1.02:
            issues.append(f"rotor {r} : hélice {prop['specs']['diameter_m']} m > maximum du moteur {max_prop} m")
        props_seen.add(r.get("prop"))
        rotors.append({"site": f"rotor_{r['prop']}", "spin": r.get("spin"), "prop_diameter_m": prop["specs"]["diameter_m"],
                       "motor_max_power_w": motor["specs"]["max_continuous_power_w"],
                       "motor_peak_power_w": motor["specs"].get("peak_power_w"),
                       "motor_mass_kg": motor["specs"]["mass_kg"], "motor_id": r.get("motor"), "prop_id": r.get("prop")})
    orphan_sites = [s for s in sites if s.split('"')[1][len("rotor_"):] not in props_seen]
    sites = [s for s in sites if s not in orphan_sites]

    batteries = [v for v in by_id.values() if v["category"] == "battery"]
    tubes = [v for v in by_id.values() if v["category"] == "tube"]
    if not batteries:
        issues.append("aucune batterie du catalogue")
    if not tubes:
        issues.append("aucun tube de bras du catalogue")
    if issues:
        return {"ok": False, "assembly": name, "issues": issues}

    weakest = min(tubes, key=lambda t: t["specs"]["outer_diameter_m"] ** 4 - (t["specs"]["outer_diameter_m"] - 2 * t["specs"]["wall_m"]) ** 4)
    attach = asm.get("payload_attach_m", [0, 0, -0.1])
    xml = "\n".join([
        f'<mujoco model="{name}">',
        '  <compiler angle="degree"/>',
        "  <asset>", *[f"    {a}" for a in assets], "  </asset>",
        "  <worldbody>", '    <body name="drone" pos="0 0 1">', "      <freejoint/>",
        *[f"      {g}" for g in geoms], *[f"      {s}" for s in sites],
        f'      <site name="payload_attach" pos="{_fmt(attach)}"/>',
        "    </body>", "  </worldbody>", "</mujoco>", ""])
    out.mkdir(parents=True, exist_ok=True)
    if (out / "meshes").exists():
        shutil.rmtree(out / "meshes")
    if mesh_files:
        (out / "meshes").mkdir()
        for filename, source in mesh_files.items():
            shutil.copy(source, out / "meshes" / filename)
    (out / "drone.xml").write_text(xml, encoding="utf-8")
    design = {
        "name": name, "rotors": rotors,
        "battery": {"energy_wh": sum(b["specs"]["energy_wh"] for b in batteries),
                    "max_power_w": sum(b["specs"]["max_continuous_power_w"] for b in batteries),
                    "mass_kg": sum(b["specs"]["mass_kg"] for b in batteries)},
        "structure": {"arm_tube_od_m": weakest["specs"]["outer_diameter_m"], "arm_tube_wall_m": weakest["specs"]["wall_m"],
                      "hub_radius_m": float(asm.get("hub_radius_m", 0.1))},
        "cruise_speed_m_s": asm.get("cruise_speed_m_s"), "components": components,
        "compiled_by": "assembly_compiler", "xml_sha1": hashlib.sha1(xml.encode("utf-8")).hexdigest(),
        "assembly_sha1": hashlib.sha1(src.read_bytes()).hexdigest(),
    }
    (out / "design.json").write_text(json.dumps(design, indent=2, ensure_ascii=False), encoding="utf-8")
    from .exam import load_assets

    check = check_package(xml, design, assets=load_assets(out))
    resonance = resonance_analysis(by_id, rotors, check.get("aircraft_mass_kg") or 0.0,
                                   check.get("max_payload_for_thrust_margin_kg") or 0.0)
    usda = write_usda(xml, out / f"{name}.usda", out)
    image = render_design(out)
    report = {"ok": check["ok"], "assembly": name, "design_dir": f"designs/{name}", "issues": check["issues"],
              "near_limits": check.get("near_limits"), "aircraft_mass_kg": check.get("aircraft_mass_kg"),
              "masses_by_family_kg": check.get("masses_by_family_kg"), "minimum_masses_kg": check.get("minimum_masses_kg"),
              "max_static_thrust_n": check.get("max_static_thrust_n"),
              "max_payload_for_thrust_margin_kg": check.get("max_payload_for_thrust_margin_kg"),
              "arms": check.get("arms"), "rotors": check.get("rotors"), "battery": design["battery"],
              "resonance": resonance,
              "warnings": (check.get("warnings") or []) + [r["warning"] for r in resonance if r.get("warning")],
              "image": image, "usda": str(usda)}
    (out / "compile.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report


TUBE_YOUNG_GPA = {"CFRP": 70.0, "AL": 69.0}


def resonance_analysis(by_id: dict, rotors: list[dict], aircraft_kg: float, payload_max_kg: float,
                       rho: float = 1.225, ct: float = 0.10, margin: float = 0.15) -> list[dict]:
    """Première fréquence de flexion de chaque bras (poutre encastrée, moteur et hélice en bout) comparée à la
    fréquence de rotation des hélices en stationnaire (1P) et au passage des pales (2P), à vide et à pleine charge."""
    tubes = [(iid, v) for iid, v in by_id.items() if v["category"] == "tube"]
    out = []
    if not tubes or not rotors:
        return out
    for r in rotors:
        motor, prop = by_id.get(r.get("motor_id")), by_id.get(r.get("prop_id"))
        if motor is None or prop is None:
            continue
        iid, tube = min(tubes, key=lambda t: min(math.dist(t[1]["fromto"][:3], motor["pos"]), math.dist(t[1]["fromto"][3:], motor["pos"])))
        specs = tube["specs"]
        od, wall, length = specs["outer_diameter_m"], specs["wall_m"], tube["length_m"]
        inertia = math.pi / 64 * (od**4 - (od - 2 * wall) ** 4)
        young = TUBE_YOUNG_GPA.get(str(specs.get("material", "CFRP")).upper(), 70.0) * 1e9
        tip = motor["specs"]["mass_kg"] + prop["specs"]["mass_kg"]
        moving = tip + 0.24 * specs["mass_per_m_kg"] * length
        f1 = math.sqrt(3 * young * inertia / length**3 / moving) / (2 * math.pi)
        diameter = prop["specs"]["diameter_m"]
        n_rot = len(rotors)
        band = [math.sqrt(m * 9.81 / n_rot / (ct * rho * diameter**4)) for m in (aircraft_kg, aircraft_kg + max(payload_max_kg, 0))]
        one_p = (min(band), max(band))
        two_p = (2 * one_p[0], 2 * one_p[1])
        near = any(lo * (1 - margin) <= f1 <= hi * (1 + margin) for lo, hi in (one_p, two_p))
        item = {"rotor": r["site"], "arm": iid, "arm_length_m": round(length, 3), "f1_hz": round(f1, 1),
                "rotation_1p_hz": [round(v, 1) for v in one_p], "blade_pass_2p_hz": [round(v, 1) for v in two_p],
                "method": "poutre encastrée + masse en bout ; vitesse de rotation par C_T = 0,10 (ordre de grandeur)"}
        if near:
            item["warning"] = (f"résonance probable : bras {iid} f1 ≈ {f1:.0f} Hz dans la bande de rotation "
                               f"{one_p[0]:.0f}–{one_p[1]:.0f} Hz (1P) ou {two_p[0]:.0f}–{two_p[1]:.0f} Hz (2P) à ±15 %")
        out.append(item)
    return out


def render_design(folder: Path) -> str | None:
    code = ("import mujoco, sys\nfrom PIL import Image\n"
            "xml = open(sys.argv[1]).read().replace('<worldbody>', '<worldbody><light pos=\"1 -1 4\" dir=\"-.3 .3 -1\"/>"
            "<light pos=\"-1 1 4\" dir=\".3 -.3 -1\"/>', 1)\n"
            "xml = xml.replace('<asset>', '<asset><texture name=\"sky\" type=\"skybox\" builtin=\"gradient\" rgb1=\"1 1 1\" "
            "rgb2=\".82 .86 .9\" width=\"32\" height=\"32\"/>', 1)\n"
            "xml = xml.replace('<compiler angle=\"degree\"/>', '<compiler angle=\"degree\"/><visual><global offwidth=\"1200\" "
            "offheight=\"800\"/><headlight ambient=\".35 .35 .35\"/></visual>', 1)\n"
            "import pathlib; scene = pathlib.Path(sys.argv[1]).with_name('view_scene.xml'); scene.write_text(xml)\n"
            "m = mujoco.MjModel.from_xml_path(str(scene)); d = mujoco.MjData(m); mujoco.mj_forward(m, d)\n"
            "b = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, 'drone')\n"
            "r = mujoco.Renderer(m, 800, 1200); c = mujoco.MjvCamera(); c.lookat[:] = d.subtree_com[b]\n"
            "c.distance = 2.6 * max(m.geom_rbound[m.geom_bodyid == b].max(), float(abs(d.geom_xpos[m.geom_bodyid == b] - d.subtree_com[b]).max()) + 0.3)\n"
            "c.elevation = -28; c.azimuth = 130; r.update_scene(d, c); Image.fromarray(r.render()).save(sys.argv[2])\n")
    from .gl import run_render

    out = folder / "view.png"
    out.unlink(missing_ok=True)
    run_render([sys.executable, "-c", code, str(folder / "drone.xml"), str(out)], out, timeout=180)
    return str(out) if out.exists() else None


def _read_stl(path: Path):
    data = path.read_bytes()
    count = struct.unpack("<I", data[80:84])[0]
    tris = np.frombuffer(data[84:84 + count * 50], dtype=np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")]))
    return tris["v"].reshape(-1, 3)


def write_usda(xml: str, path: Path, base: Path | None = None) -> Path:
    """OpenUSD ASCII de l'assemblage compilé : cylindres, boîtes et maillages des pièces sur mesure, masses incluses."""
    import xml.etree.ElementTree as ET

    root = ET.fromstring(xml)
    meshes = {m.get("name"): m.get("file") for m in root.iter("mesh")}
    lines = ["#usda 1.0", "(", '    defaultPrim = "Drone"', "    metersPerUnit = 1", '    upAxis = "Z"', ")", "",
             'def Xform "Drone"', "{"]
    for g in root.iter("geom"):
        name = (g.get("name") or "g").replace("-", "_").replace(".", "_")
        mass = float(g.get("mass", 0))
        rgba = [float(v) for v in (g.get("rgba") or ".5 .5 .5 1").split()]
        head = [f'    def {{kind}} "{name}" (', '        prepend apiSchemas = ["PhysicsMassAPI"]', "    )", "    {",
                f"        float physics:mass = {mass:.5f}",
                f"        color3f[] primvars:displayColor = [({rgba[0]}, {rgba[1]}, {rgba[2]})]",
                f"        float[] primvars:displayOpacity = [{rgba[3]}]"]
        t = g.get("type")
        if t == "cylinder" and g.get("fromto"):
            a, b = np.array([float(v) for v in g.get("fromto").split()]).reshape(2, 3)
            axis = b - a
            length = float(np.linalg.norm(axis))
            yaw = math.degrees(math.atan2(axis[1], axis[0]))
            pitch = math.degrees(math.atan2(-axis[2], math.hypot(axis[0], axis[1])))
            mid = (a + b) / 2
            lines += [h.replace("{kind}", "Cylinder") for h in head]
            lines += [f"        double radius = {float(g.get('size').split()[0]):.5f}", f"        double height = {length:.5f}",
                      '        uniform token axis = "X"', f"        float3 xformOp:translate = ({_fmt(mid).replace(' ', ', ')})",
                      f"        float3 xformOp:rotateXYZ = (0, {pitch:.3f}, {yaw:.3f})",
                      '        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:rotateXYZ"]', "    }"]
            continue
        pos = [float(v) for v in (g.get("pos") or "0 0 0").split()]
        euler = [float(v) for v in (g.get("euler") or "0 0 0").split()]
        xform = [f"        float3 xformOp:translate = ({pos[0]:.5f}, {pos[1]:.5f}, {pos[2]:.5f})",
                 f"        float3 xformOp:rotateXYZ = ({euler[0]:.3f}, {euler[1]:.3f}, {euler[2]:.3f})"]
        size = [float(v) for v in (g.get("size") or "0").split()]
        if t == "cylinder":
            lines += [h.replace("{kind}", "Cylinder") for h in head]
            lines += [f"        double radius = {size[0]:.5f}", f"        double height = {2 * size[1]:.5f}", '        uniform token axis = "Z"',
                      *xform, '        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:rotateXYZ"]', "    }"]
        elif t == "box":
            lines += [h.replace("{kind}", "Cube") for h in head]
            lines += ["        double size = 1", *xform, f"        float3 xformOp:scale = ({2 * size[0]:.5f}, {2 * size[1]:.5f}, {2 * size[2]:.5f})",
                      '        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:rotateXYZ", "xformOp:scale"]', "    }"]
        elif t == "mesh":
            mesh_path = Path(meshes[g.get("mesh")])
            verts = _read_stl(mesh_path if mesh_path.is_absolute() or base is None else base / mesh_path) * 0.001
            points = ", ".join(f"({v[0]:.5f}, {v[1]:.5f}, {v[2]:.5f})" for v in verts)
            lines += [h.replace("{kind}", "Mesh") for h in head]
            lines += [f"        point3f[] points = [{points}]",
                      f"        int[] faceVertexCounts = [{', '.join(['3'] * (len(verts) // 3))}]",
                      f"        int[] faceVertexIndices = [{', '.join(str(i) for i in range(len(verts)))}]",
                      *xform, '        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:rotateXYZ"]', "    }"]
    lines.append("}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
