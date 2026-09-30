import mujoco
import numpy as np
import math, os, sys

xml_path = "runs/lift_challenge/workspace/designs/a2c_hexa_mn1118_stagger/drone.xml"
os.chdir(os.path.dirname(xml_path))
model = mujoco.MjModel.from_xml_path(xml_path)
data = mujoco.MjData(model)
mujoco.mj_forward(model, data)

drone = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "drone")

pts = []
contrib = []
for gi in range(model.ngeom):
    name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_GEOM, gi) or ""
    if model.geom_bodyid[gi] != drone:
        continue
    if name.startswith("prop"):
        continue
    c = data.geom_xpos[gi]
    rb = model.geom_rbound[gi]
    pts += [c - rb, c + rb]
    contrib.append((name, c.copy(), rb, c[2]-rb, c[2]+rb))

pts = np.array(pts)
span_y = pts[:,1].max()-pts[:,1].min()
span_x = pts[:,0].max()-pts[:,0].min()
height_z = pts[:,2].max()-pts[:,2].min()
frontal = span_y * height_z
cda = 0.8 * frontal

print("=== Calcul frontal a2c ===")
print("span_x = %.3f m   span_y = %.3f m   height_z = %.3f m" % (span_x, span_y, height_z))
print("frontal = %.3f m2   cda = %.3f m2" % (frontal, cda))
print("z_min = %.3f  z_max = %.3f" % (pts[:,2].min(), pts[:,2].max()))
print("y_min = %.3f  y_max = %.3f" % (pts[:,1].min(), pts[:,1].max()))
print()
print("Contributions (tri par rbound decroissant):")
for name, c, rb, zlo, zhi in sorted(contrib, key=lambda x:-x[2]):
    print("  %-16s center=(%.3f,%.3f,%.3f) rbound=%.4f  z=[%.3f, %.3f]  y=[%.3f, %.3f]" % (name, c[0],c[1],c[2], rb, zlo, zhi, c[1]-rb, c[1]+rb))

# masses: read from design.json? approximate aircraft mass
import json
dj = json.load(open("runs/lift_challenge/workspace/designs/a2c_hexa_mn1118_stagger/design.json"))
# find mass
def find_mass(obj):
    if isinstance(obj, dict):
        for k,v in obj.items():
            if k in ("aircraft_mass_kg","mass_kg","total_mass_kg") and isinstance(v,(int,float)):
                return v
            r = find_mass(v)
            if r: return r
    elif isinstance(obj, list):
        for v in obj:
            r = find_mass(v)
            if r: return r
    return None
m = find_mass(dj) or 24.698
g=9.81; rho=1.225
for spd in [16, 17, 18]:
    vmax = math.sqrt(0.7*m*g/(0.5*rho*cda))
    tantheta = 0.5*rho*spd*spd*cda/(m*g)
    theta = math.degrees(math.atan(tantheta))
    print("v=%.0f m/s: tan=%.3f  tilt_vide=%.2f deg  (v_max=%.2f)" % (spd, tantheta, theta, vmax))
