---
name: assembly-design
description: Composer le squelette d'un drone à partir de pièces du catalogue et de pièces sur mesure (assembly.json), vérifier les interfaces, compiler en dossier d'épreuve avec masses calculées, inspecter le rendu. Charger avant de créer ou modifier un assemblage.
version: 1.0.0
category: engineering
---

# Composer un assemblage

Le squelette est **ta** conception : topologie, nombre de bras, hauteurs, où va chaque pièce. Il n'y a pas de gabarit : tu écris `workspace/assemblies/<nom>/assembly.json`, puis `assembly_compile(<nom>)` produit `designs/<nom>/` (seul chemin vers `run_exam`).

## Format

```json
{"hub_radius_m": 0.12, "cruise_speed_m_s": 15, "payload_attach_m": [0, 0, -0.4],
 "instances": [
   {"id": "arm0", "ref": "catalog:tube:...", "fromto_m": [x1, y1, z1, x2, y2, z2]},
   {"id": "mount0", "ref": "part:motor_mount", "pos_m": [x, y, z], "euler_deg": [0, 0, 45]},
   {"id": "m0", "ref": "catalog:motor:...", "pos_m": [x, y, z]},
   {"id": "p0", "ref": "catalog:propeller:...", "pos_m": [x, y, z + 0.03]},
   {"id": "esc0", "ref": "catalog:esc:...", "pos_m": [...]},
   {"id": "bat", "ref": "catalog:battery:...", "pos_m": [...]},
   {"id": "cables", "ref": "catalog:wiring:...", "length_m": 6, "pos_m": [...]},
   {"id": "hub", "ref": "part:hub_plate", "pos_m": [0, 0, 0]}],
 "rotors": [{"prop": "p0", "motor": "m0", "spin": 1}],
 "connections": [{"a": "arm0", "b": "mount0", "interface": "tube"}, {"a": "m0", "b": "mount0", "interface": "motor"}]}
```

- Repère : mètres, z vers le haut ; une hélice pousse selon son z local (garde euler_deg à 0 pour une poussée verticale).
- `ref` : `catalog:<id>` (voir `catalog_search`) ou `part:<nom>` (pièce construite et calculée).
- `connections` : « b » est une pièce sur mesure dont l'interface est vérifiée contre « a ».
- Masses : aucune à écrire. Elles viennent du catalogue (sourcé) et de la CAO (volume × densité).

## Idées de squelette à évaluer (avec des chiffres)

- Nombre de rotors et diamètre : surface de disque contre masse de moteurs et de bras.
- **Recouvrement des hélices** : la règle de l'épreuve (écart vertical minimal, pénalité de puissance selon la surface recouverte) est décrite dans la compétence `lift-exam` ; le rapport de compilation donne le `power_factor` de chaque rotor.
- Bras : tube acheté (catalogue) + manchons usinés ou imprimés ; longueur minimale imposée par les hélices.
- Où mettre la batterie et la charge : sous le centre, centre de gravité sous le plan des rotors.

## Après compilation

Lis `issues`, `near_limits`, `masses_by_family_kg` contre `minimum_masses_kg`, `max_payload_for_thrust_margin_kg`, `arms`, puis regarde `image` (outil de vision) : bras connectés, hélices dégagées, rien qui flotte. Corrige avant l'épreuve.
