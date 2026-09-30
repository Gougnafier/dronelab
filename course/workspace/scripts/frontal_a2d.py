import mujoco, numpy as np, math, os

XML = "runs/lift_challenge/workspace/designs/a2d_hexa_mn1118_stagger/drone.xml"
M = 24.599

os.chdir(os.path.dirname(XML))
model = mujoco.MjModel.from_xml_path(XML)
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
    contrib.append((name, c[2]-rb, c[2]+rb, rb))
pts = np.array(pts)
sy = pts[:,1].max()-pts[:,1].min()
hz = pts[:,2].max()-pts[:,2].min()
frontal = sy*hz
cda = 0.8*frontal
print("a2d: m=%.3f  span_y=%.3f  height_z=%.3f  frontal=%.3f  cda=%.3f" % (M, sy, hz, frontal, cda))
g=9.81; rho=1.225
for spd in [16,17,18]:
    tantheta = 0.5*rho*spd*spd*cda/(M*g)
    th = math.degrees(math.atan(tantheta))
    print("  v=%.0f m/s: tilt_vide=%.2f deg" % (spd, th))
print("contrib z (rbound decroissant):")
for name, zlo, zhi, rb in sorted(contrib, key=lambda x:-x[3])[:8]:
    print("  %-16s z=[%.3f,%.3f] rbound=%.4f" % (name, zlo, zhi, rb))
