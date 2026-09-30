"""Mesure l'aire frontale (boite englobante hors helices) et le tilt a vide d'un design compile.

Usage: frontal_gen.py <design_dir> <mass_kg>
Reproduit le calcul de cda de l'epreuve (exam.py: frontale = sy*hz sur les geoms non-prop,
cda = 0.8*frontale) et l'estimation du tilt a vide tan(theta) = 0.5*rho*v^2*cda/(m*g).
"""
import math
import os
import sys

import mujoco
import numpy as np

DESIGN = sys.argv[1]
M = float(sys.argv[2])

os.chdir(DESIGN)
model = mujoco.MjModel.from_xml_path("drone.xml")
data = mujoco.MjData(model)
mujoco.mj_forward(model, data)
drone = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "drone")

pts = []
contrib = []
for gi in range(model.ngeom):
    name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_GEOM, gi) or ""
    if model.geom_bodyid[gi] != drone or name.startswith("prop"):
        continue
    c = data.geom_xpos[gi]
    rb = model.geom_rbound[gi]
    pts += [c - rb, c + rb]
    contrib.append((name, c[2] - rb, c[2] + rb, rb))

pts = np.array(pts)
sy = pts[:, 1].max() - pts[:, 1].min()
hz = pts[:, 2].max() - pts[:, 2].min()
frontal = sy * hz
cda = 0.8 * frontal
g, rho = 9.81, 1.225
print(f"design={os.path.basename(DESIGN)} m={M:.3f} span_y={sy:.3f} height_z={hz:.3f} "
      f"frontal={frontal:.3f} cda={cda:.3f}")
for spd in (16, 17, 18):
    tantheta = 0.5 * rho * spd * spd * cda / (M * g)
    th = math.degrees(math.atan(tantheta))
    print(f"  v={spd:.0f} m/s: tilt_vide={th:.2f} deg")
print("contrib z (rbound decroissant):")
for name, zlo, zhi, rb in sorted(contrib, key=lambda x: -x[3])[:10]:
    print(f"  {name:18s} z=[{zlo:.3f},{zhi:.3f}] rbound={rb:.4f}")
