def build(occ):
    # Train landing_gear_v3 AL6061-T6 (CNC) : disque central + 4 poutres diagonales
    # + 4 manchons verticaux pour jambes RAPPORTEES en tube carbone 30 mm.
    # v3 : base ELARGIE (pieds a ±128 mm au lieu de ±92,6) -> angle de basculement
    # ~26,8 deg (cf. msg-0043), et ALLEGE par rapport a l'anneau plein v2 (1,108 kg)
    # vers ~1,0 kg pour financer les masses reelles non comptees (msg-0042).
    # addCylinder(x,y,z, dx,dy,dz, r) : axe = DEPLACEMENT (dx,dy,dz) depuis (x,y,z).
    # Repère mm, z vers le haut. Manchons selon -z (jambes descendantes).
    # Empreinte : manchons a ±128 mm + r_ext 19 -> 294 mm < 300 (CNC), hauteur 63 < 150.
    disc = occ.addCylinder(0, 0, -8, 0, 0, 8, 35)          # disque central r=35, ep 8 (z -8..0)
    solids = [(3, disc)]
    cuts = []
    # 4 pieds sur les diagonales (±128, ±128). Poutre ronde O24 (r=12) du disque (r=30)
    # vers le manchon (r=181) : depart (x0,y0), deplacement (dx,dy), arrivee (x0+dx, y0+dy).
    dirs = [
        (21.21, 21.21, 106.79, 106.79),      # -> (128, 128)
        (-21.21, 21.21, -106.79, 106.79),    # -> (-128, 128)
        (-21.21, -21.21, -106.79, -106.79),  # -> (-128, -128)
        (21.21, -21.21, 106.79, -106.79),    # -> (128, -128)
    ]
    for x0, y0, dx, dy in dirs:
        # poutre diagonale O24 (axe horizontal z=-4), du disque au manchon
        solids.append((3, occ.addCylinder(x0, y0, -4, dx, dy, -4, 12)))
        # manchon vertical : r_ext 19 (OD38), de z=-8 vers le bas (55 mm), a (x0+dx, y0+dy)
        solids.append((3, occ.addCylinder(x0 + dx, y0 + dy, -8, 0, 0, -55, 19)))
        # alésage du tube 30 mm : de z=-9 vers le bas (58 mm), r 15
        cuts.append((3, occ.addCylinder(x0 + dx, y0 + dy, -9, 0, 0, -58, 15)))
        # vis traversante M4 verticale (anti-rotation de la jambe dans le manchon)
        cuts.append((3, occ.addCylinder(x0 + dx, y0 + dy, -40, 0, 0, 40, 2.1)))
    # 4 perçages M5 (O5) a (±22, ±22) : boulonnage train <-> moyeu (pattern 44 mm),
    # partages avec le largueur de charge au-dessus.
    for x, y in [(22, 22), (22, -22), (-22, 22), (-22, -22)]:
        cuts.append((3, occ.addCylinder(x, y, -9, 0, 0, 18, 2.5)))
    body, _ = occ.fuse([solids[0]], solids[1:])
    occ.cut(body, cuts)
