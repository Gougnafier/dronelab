def build(occ):
    # Support moteur usiné AL6061-T6 pour MN1118 sur tube carbone 32 mm OD — allégé.
    # Repère mm. Bras = axe x (horizontal), poussée = axe z (vertical).
    # Manchon cylindrique (axe x) enserrant le tube 32 mm (r=16), paroi 2 mm, longueur 50 mm.
    mandrel = occ.addCylinder(-25, 0, 0, 50, 0, 0, 18)   # r_ext 18 (Ø36)
    # Platine moteur horizontale 40x40x3, z 15..18 (chevauche pour fusion)
    plate = occ.addBox(-20, -20, 15, 40, 40, 3)
    body, _ = occ.fuse([(3, mandrel)], [(3, plate)])
    # Perçage du tube (ID 32 -> r 16), traverse
    bore = occ.addCylinder(-26, 0, 0, 52, 0, 0, 16)
    # 4 perçages M4 (r 2.1) sur pattern moteur 25 mm, traversant la platine
    h1 = occ.addCylinder(12.5, 0, 13, 0, 0, 7, 2.1)
    h2 = occ.addCylinder(-12.5, 0, 13, 0, 0, 7, 2.1)
    h3 = occ.addCylinder(0, 12.5, 13, 0, 0, 7, 2.1)
    h4 = occ.addCylinder(0, -12.5, 13, 0, 0, 7, 2.1)
    occ.cut(body, [(3, bore), (3, h1), (3, h2), (3, h3), (3, h4)])
