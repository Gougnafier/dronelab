---
name: part-design
description: Concevoir une pièce sur mesure (support moteur, collier de bras, moyeu, train, attache de charge) - CAO par script Gmsh/OpenCASCADE, choix matériau et procédé (impression ou usinage alu), calcul par éléments finis, thermique, allègement. Charger avant de créer ou modifier une pièce.
version: 1.0.0
category: engineering
---

# Concevoir une pièce sur mesure

Une pièce = `workspace/parts/<nom>/` avec deux fichiers. Tu la construis avec `part_build`, tu la calcules avec `part_fem`, tu la regardes (champ `image`, outil de vision). L'assemblage refuse une pièce non construite, modifiée depuis, ou dont un cas de charge n'est pas calculé avec un facteur de sécurité ≥ 1,5.

## part.py (unités : millimètres)

```python
def build(occ):                      # occ = gmsh.model.occ (OpenCASCADE)
    plate = occ.addBox(x, y, z, dx, dy, dz)
    boss = occ.addCylinder(x, y, z, ax, ay, az, r)          # cylindre d'axe (ax, ay, az), longueur = norme
    body, _ = occ.fuse([(3, plate)], [(3, boss)])           # garder le résultat : les numéros changent
    occ.cut(body, [(3, occ.addCylinder(...))])             # perçages, alésages, évidements
    # aussi : addSphere, addCone, addTorus, addWedge, fillet(volumes, courbes, [rayon]), chamfer, rotate, translate
```

Règles : récupérer les entités renvoyées par chaque opération booléenne ; finir avec un seul solide (plusieurs sont fusionnés) ; pas d'import ni d'accès fichier dans le script.

## part.json

```json
{"material": "AL6061-T6", "process": "cnc", "role": "mount",
 "interfaces": [{"name": "tube", "type": "tube_socket", "params": {"tube_od_m": 0.03}},
                {"name": "motor", "type": "motor_bolts", "params": {"pattern_mm": 16}}],
 "load_cases": [{"name": "poussee_max", "fixed_box_mm": [xmin, ymin, zmin, xmax, ymax, zmax],
                 "load_box_mm": [...], "force_n": [0, 0, 330]}],
 "heat": {"heat_w": 20}}
```

- `role` : frame (moyeu, plaques, supports ; compte dans la masse de structure), mount, gear, payload, other.
- `interfaces` : ce que l'assemblage vérifie (diamètre du tube dans un manchon, motif de vis du moteur).
- `load_cases` : boîtes dans le repère de la pièce. La zone encastrée représente la liaison qui tient la pièce (le tube, les vis) ; la zone chargée reçoit l'effort. **Chaque effort réel doit avoir son cas** : poussée max du rotor, couple, atterrissage, choc. La poussée max du rotor est donnée par `check_design` ou calculable (puissance, diamètre).
- `heat` : chaleur conduite du moteur dans la pièce, **ordre de grandeur 3 à 10 % des pertes du moteur** (pertes ≈ 12 % de sa puissance). L'estimation thermique (modèle d'ailette) montre pourquoi l'aluminium convient mieux près d'un moteur puissant qu'un plastique.

## Choisir matériau et procédé (`materials_info`)

- FDM (PETG, PLA-CF, PA12-CF) : léger, abattement de résistance de 40 % (couches), mauvais conducteur thermique, volume 250 mm.
- CNC (AL6061-T6, AL7075-T6) : lourd mais résistant et conducteur, volume 400 × 300 × 150 mm.
- Compare les deux avec des chiffres (masse, facteur de sécurité, température) et écris la raison du choix dans le cahier.

## Alléger

Commence robuste, calcule, puis retire de la matière là où la contrainte est faible (évidements, épaisseurs) et recalcule. Vise un facteur de sécurité autour de 2, pas 10 : l'excès de marge est de la masse perdue, le manque est un refus.
