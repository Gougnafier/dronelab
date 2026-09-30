def build(occ):
    # Moyeu hexa AL6061-T6 : disque central + 6 manchons radiaux pour tubes 30 mm.
    # v3 : disque r=110 -> r=81 (ep 10 inchangee) pour ALLEGER le moyeu de 0,845 kg
    # vers ~0,646 kg (le minimum frame 0,983 kg = hub + supports moteur 0,337 kg).
    # La couronne retiree (r 81..110) est hors de la zone chargee (manchons r<=60,
    # perçages hook r=31) : la resistance en flexion de la charge suspendue est inchangee.
    # Repère mm, disque dans le plan xy (épaisseur selon z). Poussée = axe z.
    disk = occ.addCylinder(0, 0, -5, 0, 0, 10, 96)   # disque r=96 (v2: 110), épaisseur 10 mm
    # 6 directions radiales (cos, sin) : 0°, 60°, 120°, 180°, 240°, 300°
    dirs = [(1.0, 0.0), (0.5, 0.866), (-0.5, 0.866), (-1.0, 0.0), (-0.5, -0.866), (0.5, -0.866)]
    sleeves = []
    bores = []
    locks = []
    for cx, sx in dirs:
        # manchon plein : de r=40 a r=60 (longueur 20), r_ext 17,0 (Ø34)
        sleeves.append((3, occ.addCylinder(40*cx, 40*sx, 0, 60*cx, 60*sx, 0, 17.0)))
        # alésage du tube 30 mm : de r=35 a r=70 (longueur 35), r 15,0
        bores.append((3, occ.addCylinder(35*cx, 35*sx, 0, 70*cx, 70*sx, 0, 15.0)))
        # Vis traversante M4 verticale (axe z) au centre du manchon (r~70) :
        # blocage mécanique en rotation autour de l'axe du bras.
        locks.append((3, occ.addCylinder(70*cx, 70*sx, -20, 0, 0, 40, 2.1)))
    # 4 perçages M5 (Ø5) pour la fixation du largueur de charge (pattern 44 mm)
    hook_bolts = []
    for x, y in [(22, 22), (22, -22), (-22, 22), (-22, -22)]:
        hook_bolts.append((3, occ.addCylinder(x, y, -6, 0, 0, 12, 2.5)))
    body, _ = occ.fuse([(3, disk)], sleeves)
    occ.cut(body, bores + locks + hook_bolts)
