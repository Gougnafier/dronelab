def build(occ):
    # Moyeu hexa AL6061-T6 : disque central + 6 manchons radiaux pour tubes 35 mm.
    # Repère mm, disque dans le plan xy (épaisseur selon z). Poussée = axe z.
    disk = occ.addCylinder(0, 0, -5, 0, 0, 10, 110)   # disque r=110, épaisseur 10 mm
    # 6 directions radiales (cos, sin) : 0°, 60°, 120°, 180°, 240°, 300°
    dirs = [(1.0, 0.0), (0.5, 0.866), (-0.5, 0.866), (-1.0, 0.0), (-0.5, -0.866), (0.5, -0.866)]
    sleeves = []
    bores = []
    locks = []
    for cx, sx in dirs:
        # manchon plein : de r=40 a r=100 (longueur 60), r_ext 19,5 (Ø39)
        sleeves.append((3, occ.addCylinder(40*cx, 40*sx, 0, 60*cx, 60*sx, 0, 19.5)))
        # alésage du tube 35 mm : de r=35 a r=105 (longueur 70), r 17,5
        bores.append((3, occ.addCylinder(35*cx, 35*sx, 0, 70*cx, 70*sx, 0, 17.5)))
        # Vis traversante M4 verticale (axe z) au centre du manchon (r~70) :
        # blocage mécanique en rotation autour de l'axe du bras. Traverse disque + manchon + tube.
        locks.append((3, occ.addCylinder(70*cx, 70*sx, -20, 0, 0, 40, 2.1)))
    body, _ = occ.fuse([(3, disk)], sleeves)
    occ.cut(body, bores + locks)
