import mujoco
import numpy as np
import math, os

xml_path = "runs/lift_challenge/workspace/designs/a1_hexa_mn1118_35mm/drone.xml"
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

print("=== Calcul frontal (reproduction exam.py lignes 490-499) ===")
print("span_x = %.3f m   span_y = %.3f m   height_z = %.3f m" % (span_x, span_y, height_z))
print("frontal = span_y * height_z = %.3f m2" % frontal)
print("cda = 0.8 * frontal = %.3f m2" % cda)
print("z_min = %.3f  z_max = %.3f" % (pts[:,2].min(), pts[:,2].max()))
print()
print("Contributions (tri par rbound decroissant):")
for name, c, rb, zlo, zhi in sorted(contrib, key=lambda x:-x[2]):
    print("  %-16s center=(%.3f,%.3f,%.3f) rbound=%.4f  z=[%.3f, %.3f]" % (name, c[0],c[1],c[2], rb, zlo, zhi))

m_drone = 24.844
g = 9.81
rho = 1.225
vmax = math.sqrt(0.7 * m_drone * g / (0.5 * rho * cda))
print()
print("m_vide = %.1f kg ; autorite tilt 35 deg = %.1f N horizontale" % (m_drone, 0.7*m_drone*g))
print("v_max_vide (tilt sature 35 deg) = sqrt(%.1f*%.3f*g/(0.5*rho*cda)) = %.3f m/s" % (0.7, m_drone, vmax))

# variante : bras plus courts (hub plus grand), sans changer la portee
for arm_len in [0.93, 0.75, 0.60, 0.45]:
    # hauteur z = arm_len (dominee par rbound des bras = demi-longueur)
    hz = arm_len
    f = span_y * hz
    cd = 0.8 * f
    vm = math.sqrt(0.7 * m_drone * g / (0.5 * rho * cd))
    print("  arm_len=%.2f m -> frontal=%.3f cda=%.3f v_max=%.2f m/s" % (arm_len, f, cd, vm))
