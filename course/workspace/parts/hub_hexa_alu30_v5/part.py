def build(occ):
    # Moyeu hexa AL6061-T6 : disque central + 6 manchons radiaux pour tubes 30 mm.
    # v5 (cycle 104) : disque central AMINCI de 10 mm a 8 mm (epaisseur z=-4..+4).
    # v4 (cycle 101) avait un disque de 10 mm, dimensionne par le cas charge_suspendue
    # (1112 N) avec SF = 2,86 (von Mises 96,6 MPa). Amincir a 8 mm releve la contrainte
    # en 1/t^2 : SF attendu ~2,86 x (8/10)^2 = 1,83 (> 1,5). Gain de masse ~0,15 kg
    # (disque : pi x 96^2 x 2 mm = 57,9 cm^3 x 2,70 g/cm^3 = 156 g).
    # Les manchons, alesages tubes et vis restent inchanges (interfaces invariantes).
    # Repere mm, disque dans le plan xy (epaisseur selon z). Poussee = axe z.
    disk = occ.addCylinder(0, 0, -4, 0, 0, 8, 96)   # disque r=96, epaisseur 8 mm (v4: 10)
    # 6 directions radiales (cos, sin) : 0°, 60°, 120°, 180°, 240°, 300°
    dirs = [(1.0, 0.0), (0.5, 0.866), (-0.5, 0.866), (-1.0, 0.0), (-0.5, -0.866), (0.5, -0.866)]
    sleeves = []
    bores = []
    locks = []
    for cx, sx in dirs:
        # manchon plein : de r=40 a r=60 (longueur 20), r_ext 17,0 (Ø34)
        sleeves.append((3, occ.addCylinder(40*cx, 40*sx, 0, 60*cx, 60*sx, 0, 17.0)))
        # alesage du tube 30 mm : de r=35 a r=70 (longueur 35), r 15,0
        bores.append((3, occ.addCylinder(35*cx, 35*sx, 0, 70*cx, 70*sx, 0, 15.0)))
        # Vis traversante M4 verticale (axe z) au CENTRE du manchon (r=50) :
        locks.append((3, occ.addCylinder(50*cx, 50*sx, -20, 0, 0, 40, 2.1)))
    # 4 perçages M5 (Ø5) pour la fixation du largueur de charge (pattern 44 mm)
    hook_bolts = []
    for x, y in [(22, 22), (22, -22), (-22, 22), (-22, -22)]:
        hook_bolts.append((3, occ.addCylinder(x, y, -6, 0, 0, 12, 2.5)))
    body, _ = occ.fuse([(3, disk)], sleeves)
    occ.cut(body, bores + locks + hook_bolts)
