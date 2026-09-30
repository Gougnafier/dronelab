import mujoco
import numpy as np
import math, os

def analyze(xml_path, m):
    os.chdir(os.path.dirname(xml_path))
    model = mujoco.MjModel.from_xml_path(xml_path)
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)
    drone = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "drone")
    pts = []
    for gi in range(model.ngeom):
        name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_GEOM, gi) or ""
        if model.geom_bodyid[gi] != drone:
            continue
        if name.startswith("prop"):
            continue
        c = data.geom_xpos[gi]
        rb = model.geom_rbound[gi]
        pts += [c - rb, c + rb]
    pts = np.array(pts)
    span_y = pts[:,1].max()-pts[:,1].min()
    height_z = pts[:,2].max()-pts[:,2].min()
    frontal = span_y * height_z
    cda = 0.8 * frontal
    g=9.81; rho=1.225
    print("m=%.3f kg  span_y=%.3f  height_z=%.3f  frontal=%.3f  cda=%.3f" % (m, span_y, height_z, frontal, cda))
    for spd in [16, 17, 18]:
        vmax = math.sqrt(0.7*m*g/(0.5*rho*cda))
        tantheta = 0.5*rho*spd*spd*cda/(m*g)
        theta = math.degrees(math.atan(tantheta))
        print("  v=%.0f m/s: tilt_vide=%.2f deg  (v_max=%.2f m/s)" % (spd, theta, vmax))
    return cda, frontal

print("=== a2b (sans chemin de charge, m=24.489) ===")
analyze("runs/lift_challenge/workspace/designs/a2b_hexa_mn1118_stagger/drone.xml", 24.489)
print()
print("=== a2c (chemin de charge, m=24.698) ===")
analyze("runs/lift_challenge/workspace/designs/a2c_hexa_mn1118_stagger/drone.xml", 24.698)
