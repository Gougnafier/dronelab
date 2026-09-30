def build(occ):
    # release_hook_v2 : largueur de charge à mors, AL7075-T6 (CNC).
    # Charge tire vers -z. Plaque fixée au moyeu (4x M5) + corps + axe du mors
    # + mors (position FERMÉE, referme la boucle de retenue de l'élingue) + bossage du verrou.
    # L'ouverture réelle est assurée par le retrait du verrou (actionneur) ; le mors pivote
    # sur l'axe. Ici le mors est fusionné au corps en position fermée pour le calcul statique.
    plate = occ.addBox(-30, -30, -6, 60, 60, 6)               # plaque 60x60x6, z -6..0
    holes = []
    for x, y in [(22, 22), (22, -22), (-22, 22), (-22, -22)]:
        holes.append((3, occ.addCylinder(x, y, -8, 0, 0, 16, 2.6)))   # 4 perçages M5 (fixation moyeu)
    body = occ.addCylinder(0, 0, -6, 0, 0, -40, 20)          # corps Ø40, z -6..-46
    axle = occ.addCylinder(-20, 0, -28, 40, 0, 0, 4)         # axe du mors Ø8 (axe x), z=-28
    # mors : patte verticale + barre horizontale basse, en position FERMÉE
    jaw_vert = occ.addCylinder(0, 0, -28, 0, 0, -30, 7)      # patte du mors z -28..-58
    jaw_bar = occ.addCylinder(0, -12, -58, 0, 24, 0, 7)      # barre du mors z=-58, y -12..12
    # bossage du verrou Ø12 (axe y) pour goupille de verrouillage, z=-28
    latch = occ.addCylinder(0, -18, -28, 0, 36, 0, 6)
    solid, _ = occ.fuse([(3, plate)], [(3, body), (3, axle), (3, jaw_vert), (3, jaw_bar), (3, latch)])
    occ.cut(solid, holes)
