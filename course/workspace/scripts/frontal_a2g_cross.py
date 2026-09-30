import mujoco
import numpy as np
import math, os

xml_path = "runs/lift_challenge/workspace/designs/a2g_hexa_mn1118_stagger/drone.xml"
os.chdir(os.path.dirname(xml_path))
model = mujoco.MjModel.from_xml_path(xml_path)
data = mujoco.MjData(model)
mujoco.mj_forward(model, data)

drone = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "drone")
g = 9.81
rho = 1.225
m_air = 23.935

# ---------- 1) Aire frontale EPREUVE (reproduction exam.py) ----------
pts = []
contrib = []
for gi in range(model.ngeom):
    name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_GEOM, gi) or ""
    if model.geom_bodyid[gi] != drone:
        continue
    if name.startswith("prop"):
        continue
    c = data.geom_xpos[gi].copy()
    rb = model.geom_rbound[gi]
    gtype = model.geom_type[gi]
    sz = model.geom_size[gi].copy()
    pts += [c - rb, c + rb]
    contrib.append((name, gtype, sz, c, rb, c[2]-rb, c[2]+rb))

pts = np.array(pts)
span_y_exam = pts[:,1].max() - pts[:,1].min()
span_z_exam = pts[:,2].max() - pts[:,2].min()
frontal_exam = span_y_exam * span_z_exam
cda_exam = 0.8 * frontal_exam

print("="*72)
print("A) AIRE FRONTALE EPREUVE (boite des spheres englobantes, helices exclues)")
print("="*72)
print("span_y = %.4f m   span_z = %.4f m" % (span_y_exam, span_z_exam))
print("frontal_exam = %.4f m2   cda_exam = %.4f m2" % (frontal_exam, cda_exam))
print("z_exam [%.4f, %.4f]   y_exam [%.4f, %.4f]" % (pts[:,2].min(), pts[:,2].max(), pts[:,1].min(), pts[:,1].max()))
print()
print("Contributions (tri rbound decroissant):")
for name, gtype, sz, c, rb, zlo, zhi in sorted(contrib, key=lambda x:-x[4]):
    print("  %-18s type=%d size=[%s] rbound=%.4f  z=[%+.4f,%+.4f]"
          % (name, gtype, ",".join("%.4f"%s for s in sz), rb, zlo, zhi))

# ---------- 2) Aire frontale SILHOUETTE REELLE (union rasterisee y-z) ----------
GRID = 0.005
BOX = mujoco.mjtGeom.mjGEOM_BOX
CYL = mujoco.mjtGeom.mjGEOM_CYLINDER
MSH = mujoco.mjtGeom.mjGEOM_MESH

def geom_rot(gi):
    body = model.geom_bodyid[gi]
    Rb = data.xmat[body].reshape(3,3)
    q = model.geom_quat[gi]
    m = np.zeros(9)
    mujoco.mju_quat2Mat(m, q)
    Rg = m.reshape(3,3)
    return Rb @ Rg

geoms = []
for gi in range(model.ngeom):
    name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_GEOM, gi) or ""
    if model.geom_bodyid[gi] != drone:
        continue
    if name.startswith("prop"):
        continue
    gtype = model.geom_type[gi]
    c = data.geom_xpos[gi].copy()
    sz = model.geom_size[gi].copy()
    if gtype == BOX:
        y0, y1 = c[1]-sz[1], c[1]+sz[1]
        z0, z1 = c[2]-sz[2], c[2]+sz[2]
    elif gtype == CYL:
        r = sz[0]
        if sz[1] > sz[0]:
            R = geom_rot(gi)
            ax = R @ np.array([0,0,1.0])
            frm = c - sz[1]*ax
            to  = c + sz[1]*ax
            y0 = min(frm[1], to[1]) - r; y1 = max(frm[1], to[1]) + r
            z0 = min(frm[2], to[2]) - r; z1 = max(frm[2], to[2]) + r
        else:
            y0, y1 = c[1]-r, c[1]+r
            z0, z1 = c[2]-sz[1], c[2]+sz[1]
    elif gtype == MSH:
        mid = model.geom_dataid[gi]
        n = model.mesh_vertnum[mid]
        adr = model.mesh_vertadr[mid]
        verts = model.mesh_vert[adr:adr+n].reshape(-1,3)
        R = geom_rot(gi)
        wv = (R @ verts.T).T + c
        y0, y1 = wv[:,1].min(), wv[:,1].max()
        z0, z1 = wv[:,2].min(), wv[:,2].max()
    else:
        continue
    geoms.append((name, gtype, gi, c, sz, y0, y1, z0, z1))

y_lo = min(x[5] for x in geoms); y_hi = max(x[6] for x in geoms)
z_lo = min(x[7] for x in geoms); z_hi = max(x[8] for x in geoms)

print()
print("="*72)
print("B) BOITE REELLE PAR GEOM (projection y-z de la forme reelle)")
print("="*72)
for name, gtype, gi, c, sz, y0, y1, z0, z1 in sorted(geoms, key=lambda x: x[7]):
    print("  %-18s y=[%+.4f,%+.4f](%.3f)  z=[%+.4f,%+.4f](%.3f)  Abox=%.4f"
          % (name, y0, y1, y1-y0, z0, z1, z1-z0, (y1-y0)*(z1-z0)))

ny = int(math.ceil((y_hi - y_lo)/GRID)) + 1
nz = int(math.ceil((z_hi - z_lo)/GRID)) + 1
grid = np.zeros((ny, nz), dtype=bool)

def mark_rect(y0, y1, z0, z1):
    iy0 = max(0, int((y0-y_lo)//GRID)); iy1 = min(ny-1, int((y1-y_lo)//GRID))
    iz0 = max(0, int((z0-z_lo)//GRID)); iz1 = min(nz-1, int((z1-z_lo)//GRID))
    if iy1 >= iy0 and iz1 >= iz0:
        grid[iy0:iy1+1, iz0:iz1+1] = True

def mark_segment(frm, to, r):
    a = np.array([frm[1], frm[2]]); b = np.array([to[1], to[2]])
    ab = b - a; L2 = ab.dot(ab)
    iy0 = max(0, int((min(frm[1],to[1])-r-y_lo)//GRID)); iy1 = min(ny-1, int((max(frm[1],to[1])+r-y_lo)//GRID))
    iz0 = max(0, int((min(frm[2],to[2])-r-z_lo)//GRID)); iz1 = min(nz-1, int((max(frm[2],to[2])+r-z_lo)//GRID))
    for iy in range(iy0, iy1+1):
        y = y_lo + (iy+0.5)*GRID
        for iz in range(iz0, iz1+1):
            z = z_lo + (iz+0.5)*GRID
            p = np.array([y, z])
            if L2 < 1e-12:
                d = np.linalg.norm(p-a)
            else:
                t = max(0.0, min(1.0, (p-a).dot(ab)/L2))
                d = np.linalg.norm(p - (a+t*ab))
            if d <= r:
                grid[iy, iz] = True

for name, gtype, gi, c, sz, y0, y1, z0, z1 in geoms:
    if gtype == BOX:
        mark_rect(y0, y1, z0, z1)
    elif gtype == CYL:
        if sz[1] > sz[0]:
            R = geom_rot(gi)
            ax = R @ np.array([0,0,1.0])
            frm = c - sz[1]*ax; to = c + sz[1]*ax
            mark_segment(frm, to, sz[0])
        else:
            mark_rect(y0, y1, z0, z1)
    elif gtype == MSH:
        mid = model.geom_dataid[gi]
        n = model.mesh_vertnum[mid]; adr = model.mesh_vertadr[mid]
        verts = model.mesh_vert[adr:adr+n].reshape(-1,3)
        R = geom_rot(gi)
        wv = (R @ verts.T).T + c
        mark_rect(wv[:,1].min(), wv[:,1].max(), wv[:,2].min(), wv[:,2].max())

area_real = grid.sum() * GRID * GRID
cda_real = 0.8 * area_real

v = 17.0
W = m_air * g
theta_exam = math.degrees(math.atan(0.5*rho*v*v*cda_exam/W))
theta_real = math.degrees(math.atan(0.5*rho*v*v*cda_real/W))
F_lat_exam = 0.5*rho*8*8*cda_exam
F_lat_real = 0.5*rho*8*8*cda_real

print()
print("="*72)
print("C) SYNTHESE")
print("="*72)
print("Aire frontale EPREUVE (boite des spheres) : %.4f m2  -> cda %.4f m2" % (frontal_exam, cda_exam))
print("Aire frontale SILHOUETTE reelle (union y-z) : %.4f m2  -> cda %.4f m2" % (area_real, cda_real))
print("Rapport silhouette/epreuve : %.1f %%" % (100*area_real/frontal_exam))
print()
print("Assiette a vide a 17 m/s :  EPREUVE %.2f deg   REELLE %.2f deg" % (theta_exam, theta_real))
print("Poussee laterale vent 8 m/s : EPREUVE %.1f N   REELLE %.1f N" % (F_lat_exam, F_lat_real))
print()
print("Seuil eclaireur : cda silhouette < 70%% de 0.848 = %.4f m2" % (0.7*0.848))
print("Conclusion :", "SOUS le seuil -> deposer report_exam_limitation" if cda_real < 0.7*0.848 else "pas sous le seuil")
