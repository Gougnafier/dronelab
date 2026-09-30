def build(occ):
    # release_hook : verrou de largage + oeil d'accroche de la charge, AL7075-T6 (CNC).
    # Repere mm ; la charge tire vers -z. Plaque vissee sous le moyeu + corps + oeil.
    # La piece porte la charge suspendue : 556 N (125 lb), choc 2x, effort lateral (attache rigide).
    plate = occ.addBox(-30, -30, -6, 60, 60, 6)            # plaque 60x60x6, z -6..0
    holes = []
    for x, y in [(22, 22), (22, -22), (-22, 22), (-22, -22)]:
        holes.append((3, occ.addCylinder(x, y, -8, 0, 0, 16, 2.6)))   # 4 perces M5
    body = occ.addCylinder(0, 0, -6, 0, 0, -50, 12)        # corps D=24, z -6..-56
    eye = occ.addTorus(0, 0, -62, 11, 6)                     # oeil R11 r6, centre z=-62
    solid, _ = occ.fuse([(3, plate)], [(3, body), (3, eye)])
    occ.cut(solid, holes)
