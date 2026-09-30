def build(occ):
    # Train AL6061-T6 : anneau supérieur + 4 jambes Ø28 vers le bas (rôle gear).
    # Repère mm, anneau dans le plan xy (épaisseur selon z), jambes selon -z.
    # Contraintes CNC : empreinte <= 400x300, hauteur <= 150 mm.
    ring = occ.addCylinder(0, 0, -3, 0, 0, 6, 135)          # disque plein r=135 (OD 270), ép 6 mm
    ring_bore = occ.addCylinder(0, 0, -4, 0, 0, 8, 127.5)   # alésage -> anneau (ID 255)
    legs = []
    for x, y in [(92.6, 92.6), (92.6, -92.6), (-92.6, 92.6), (-92.6, -92.6)]:
        # jambe Ø28 (r 14), de z=-3 vers le bas (longueur 138)
        legs.append((3, occ.addCylinder(x, y, -3, 0, 0, -138, 14)))
    body, _ = occ.fuse([(3, ring)], legs)
    occ.cut(body, [(3, ring_bore)])
