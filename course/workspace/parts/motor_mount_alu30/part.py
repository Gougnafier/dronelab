def build(occ):
    # Support moteur AL6061-T6 pour MN1118 sur tube carbone 30 mm OD.
    # Repère mm. Bras = axe x (horizontal), poussée = axe z (vertical).
    # Manchon cylindrique (axe x) enserrant le tube 30 mm (r=15), paroi 2 mm, longueur 50 mm.
    mandrel = occ.addCylinder(-25, 0, 0, 50, 0, 0, 17.0)   # r_ext 17,0 (Ø34)
    # Platine moteur horizontale 40x40x3, z 15..18 (chevauche pour fusion)
    plate = occ.addBox(-20, -20, 15, 40, 40, 3)
    body, _ = occ.fuse([(3, mandrel)], [(3, plate)])
    # Alésage du tube (OD 30 -> r 15), traverse
    bore = occ.addCylinder(-26, 0, 0, 52, 0, 0, 15.0)
    # 4 perçages M4 (r 2.1) sur pattern moteur 25 mm, traversant la platine
    h1 = occ.addCylinder(12.5, 0, 13, 0, 0, 7, 2.1)
    h2 = occ.addCylinder(-12.5, 0, 13, 0, 0, 7, 2.1)
    h3 = occ.addCylinder(0, 12.5, 13, 0, 0, 7, 2.1)
    h4 = occ.addCylinder(0, -12.5, 13, 0, 0, 7, 2.1)
    # Vis traversante M4 verticale (axe z) au centre : blocage mécanique en rotation
    # autour de l'axe du bras (x). Traverse manchon + platine + tube (perçage à l'assemblage).
    lock = occ.addCylinder(0, 0, -20, 0, 0, 40, 2.1)
    occ.cut(body, [(3, bore), (3, h1), (3, h2), (3, h3), (3, h4), (3, lock)])
