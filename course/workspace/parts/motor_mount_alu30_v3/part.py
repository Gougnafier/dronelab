def build(occ):
    # Support moteur AL6061-T6 pour MN1118 sur tube carbone 30 mm OD.
    # Repère mm. Bras = axe x (horizontal), poussée = axe z (vertical).
    # Manchon cylindrique (axe x) enserrant le tube 30 mm (r=15), paroi 2 mm.
    # v3 : manchon ALLONGÉ vers l'intérieur pour un engagement de 60 mm (2 diamètres),
    # contre 25 mm en v2 (borné par le manchon de 50 mm). Le tube arrive du côté -x
    # et se termine à x=0 (le moteur est au-dessus de la platine, en bout de bras).
    mandrel = occ.addCylinder(-60, 0, 0, 85, 0, 0, 17.0)   # r_ext 17,0 (Ø34), x -60..+25
    # Platine moteur horizontale 40x40x3, z 15..18 (chevauche pour fusion)
    plate = occ.addBox(-20, -20, 15, 40, 40, 3)
    body, _ = occ.fuse([(3, mandrel)], [(3, plate)])
    # Alésage du tube (OD 30 -> r 15), traverse
    bore = occ.addCylinder(-62, 0, 0, 88, 0, 0, 15.0)      # x -62..+26
    # 4 perçages M4 (r 2.1) sur pattern moteur 25 mm, traversant la platine
    h1 = occ.addCylinder(12.5, 0, 13, 0, 0, 7, 2.1)
    h2 = occ.addCylinder(-12.5, 0, 13, 0, 0, 7, 2.1)
    h3 = occ.addCylinder(0, 12.5, 13, 0, 0, 7, 2.1)
    h4 = occ.addCylinder(0, -12.5, 13, 0, 0, 7, 2.1)
    # Vis traversante M4 verticale (axe z) à x=-12 (blocage mécanique en rotation autour
    # de l'axe du bras). x=-12 = 3 diamètres (M4) du bord du tube (tube terminé à x=0)
    # ET 48 mm du bord intérieur (x=-60) : au cœur de l'engagement de 60 mm.
    lock = occ.addCylinder(-12, 0, -20, 0, 0, 40, 2.1)
    occ.cut(body, [(3, bore), (3, h1), (3, h2), (3, h3), (3, h4), (3, lock)])
