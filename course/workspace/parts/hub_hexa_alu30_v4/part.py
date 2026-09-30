def build(occ):
    # Moyeu hexa AL6061-T6 : disque central + 6 manchons radiaux pour tubes 30 mm.
    # v4 (cycle 101) : vis d'anti-rotation DEPLACEE de r=70 a r=50 (centre du manchon
    # r=40..60). En v3 la vis a r=70 coincidait avec la sortie de l'alesage (encastrement
    # du porte-a-faux, moment de flexion maximal du tube nu) : la section nette du tube
    # perde (2 trous Ø4) y donnait sigma_nette = 255,7 MPa, marge 4,3 % < 20 % (note-0024).
    # A r=50, le tube est doublement soutenu (manchon alu r15..17 + disque) : le perçage
    # n'eloigne plus de matiere au droit du moment maximal. Le couple reactif rotor (5,5 N.m)
    # est constant le long du bras, la vis en r=50 le reprend identiquement.
    # Verrouillage declare : rondelle Nord-Lock M4 + frein-filet Loctite 243, couple 2,5 N.m.
    # Repere mm, disque dans le plan xy (epaisseur selon z). Poussee = axe z.
    disk = occ.addCylinder(0, 0, -5, 0, 0, 10, 96)   # disque r=96 (v2: 110), epaisseur 10 mm
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
        # blocage mecanique en rotation autour de l'axe du bras, hors zone de flexion max.
        locks.append((3, occ.addCylinder(50*cx, 50*sx, -20, 0, 0, 40, 2.1)))
    # 4 perçages M5 (Ø5) pour la fixation du largueur de charge (pattern 44 mm)
    hook_bolts = []
    for x, y in [(22, 22), (22, -22), (-22, 22), (-22, -22)]:
        hook_bolts.append((3, occ.addCylinder(x, y, -6, 0, 0, 12, 2.5)))
    body, _ = occ.fuse([(3, disk)], sleeves)
    occ.cut(body, bores + locks + hook_bolts)
