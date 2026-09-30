def build(occ):
    # Train landing_gear_v2 AL6061-T6 : anneau de fixation au moyeu + 4 manchons verticaux
    # pour jambes RAPPORTEES en tube carbone 30 mm (role gear).
    # Repère mm, anneau dans le plan xy (epaisseur selon z), manchons selon -z.
    # Contraintes CNC : empreinte 270x270 <= 300, hauteur 79 mm <= 150.
    ring = occ.addCylinder(0, 0, -10, 0, 0, 20, 135)          # disque plein r=135 (OD 270), ep 20 mm
    ring_bore = occ.addCylinder(0, 0, -11, 0, 0, 22, 115)      # alesage central -> anneau radial 115..135
    sleeves = []
    bores = []
    locks = []
    for x, y in [(92.6, 92.6), (92.6, -92.6), (-92.6, 92.6), (-92.6, -92.6)]:
        # manchon plein : de z=-10 vers le bas (55 mm), r_ext 19 (OD38)
        sleeves.append((3, occ.addCylinder(x, y, -10, 0, 0, -55, 19)))
        # alesage du tube 30 mm : de z=-11 vers le bas (58 mm), r 15
        bores.append((3, occ.addCylinder(x, y, -11, 0, 0, -58, 15)))
        # vis traversante M4 verticale (anti-rotation de la jambe dans le manchon)
        locks.append((3, occ.addCylinder(x, y, -40, 0, 0, 40, 2.1)))
    body, _ = occ.fuse([(3, ring)], sleeves)
    occ.cut(body, [(3, ring_bore)] + bores + locks)
