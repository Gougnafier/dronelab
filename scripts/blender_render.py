"""Rendu Blender (mode arrière-plan) d'une maquette décrite en JSON (sortie de heavylift.geometry.assembly).

  blender -b --factory-startup --python scripts/blender_render.py -- parts.json out.png [iso|top|side]
"""

import json
import math
import sys

import bpy
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:]
parts_path, out_path = args[0], args[1]
view = args[2] if len(args) > 2 else "iso"
parts = json.load(open(parts_path, encoding="utf-8"))

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
materials = {}


def material(part):
    key = (tuple(part["color"]), part["opacity"])
    if key not in materials:
        mat = bpy.data.materials.new(f"m{len(materials)}")
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes["Principled BSDF"]
        bsdf.inputs["Base Color"].default_value = (*part["color"], 1.0)
        bsdf.inputs["Roughness"].default_value = 0.45
        bsdf.inputs["Metallic"].default_value = 0.6 if part["kind"] in ("motor", "plate", "hub") else 0.0
        if part["opacity"] < 1:
            bsdf.inputs["Alpha"].default_value = part["opacity"]
        materials[key] = mat
    return materials[key]


for part in parts:
    cx, cy, cz = part["center"]
    if part["shape"] == "cylinder":
        rot = (0.0, math.pi / 2, math.radians(part["yaw_deg"])) if part["axis"] == "X" else (0.0, 0.0, 0.0)
        bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=part["radius"], depth=part["height"],
                                            location=(cx, cy, cz), rotation=rot)
    else:
        bpy.ops.mesh.primitive_cube_add(size=1, location=(cx, cy, cz))
        bpy.context.object.scale = part["size"]
    obj = bpy.context.object
    obj.name = part["name"]
    obj.data.materials.append(material(part))
    bpy.ops.object.shade_smooth()

xs = [p["center"][0] + s * p.get("radius", 0.2) for p in parts for s in (-1, 1)]
ys = [p["center"][1] + s * p.get("radius", 0.2) for p in parts for s in (-1, 1)]
zs = [p["center"][2] for p in parts]
span = max(max(xs) - min(xs), max(ys) - min(ys), 1.0)
floor = min(zs) - 0.1
target = Vector((0, 0, (max(zs) + min(zs)) / 2))

bpy.ops.mesh.primitive_plane_add(size=span * 6, location=(0, 0, floor))
ground = bpy.context.object
gmat = bpy.data.materials.new("ground")
gmat.use_nodes = True
gmat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.82, 0.84, 0.86, 1)
ground.data.materials.append(gmat)

bpy.ops.object.light_add(type="SUN", location=(0, 0, 10))
bpy.context.object.data.energy = 3.5
bpy.context.object.rotation_euler = (math.radians(35), math.radians(10), math.radians(30))
world = bpy.data.worlds.new("w")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.9, 0.92, 0.95, 1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.8
scene.world = world

direction = {"iso": Vector((1.0, -1.1, 0.75)), "top": Vector((0.001, -0.001, 1.0)),
             "side": Vector((0.0, -1.0, 0.12))}[view].normalized()
bpy.ops.object.camera_add(location=target + direction * span * 1.55)
cam = bpy.context.object
cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
cam.data.lens = 40
scene.camera = cam

scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = 48
scene.cycles.use_denoising = True
scene.render.resolution_x, scene.render.resolution_y = 1400, 900
scene.render.filepath = out_path
bpy.ops.render.render(write_still=True)
