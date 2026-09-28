# K02 — Évaluation sans LLM d’un bras paramétrique

Date : 27 septembre 2026 (bloc « dimanche soir » du cahier des charges).

**Objectif :** `evaluate.py` sur un bras paramétrique, 20 designs aléatoires, résultats en JSON.
**Résultat :** atteint. 20/20 évaluations valides sur la RTX 5090, 3/20 designs faisables.

## Chaîne évaluée

`generate_part` → `check_manufacturability` → `run_fem` sur 4 cas statiques (poussée max, couple moteur, manœuvre, chute) → `run_modal` (3 modes) → score.

- Géométrie : âme trapézoïdale, plateau moteur Ø 30 mm (motif 16 × 16 M3, passage d’axe Ø 8), 2 vis M3 à l’encastrement, évidements circulaires optionnels, nervures de bord optionnelles (section en U). Longueur libre 110 mm, zone encastrée 25 mm.
- Paramètres : épaisseur, largeur, conicité, nombre et taille des évidements, nervures (hauteur, largeur), matériau PETG ou PLA-CF.
- Maillage : tétraèdres quadratiques C3D10, taille bornée par la paroi la plus fine.
- Score : `masse_ref / masse` si faisable (> 0), sinon moins la somme des violations normalisées (< 0).

## Commandes

```bash
# Environnement (local ou distant)
conda env create -f environment.yml
# Tests : 7 tests, dont validation poutre et délai dépassé
PATH=<env>/bin:$PATH python -m pytest -q
# Un design
python scripts/evaluate.py --reference
# Lot aléatoire
python scripts/random_designs.py --n 20 --seed 0 --workers 7
```

Sur la 5090 : code copié par `tar` sur SSH dans `~/drone-agent/repo`, environnement `~/drone-agent/env` (micromamba, Python 3.11, CalculiX 2.23, Gmsh 4.15.2).

## Vérification physique

Bras de référence (PETG, âme 5 mm, largeur 24 mm, nervures 3 × 10 mm) : section en U avec I = 3 000 mm⁴.

| Grandeur | Théorie | CalculiX | Écart |
| --- | --- | --- | --- |
| Flèche sous 15 N, F·L³ / 3EI | 1,11 mm | 1,13 mm | +2 % |
| 1re fréquence, √(k/m) avec 60 g + 25 % de la masse du bras | 72 Hz | 70,3 Hz | −2 % |

Cette concordance valide aussi la permutation des nœuds Gmsh → CalculiX. Elle est vérifiée par `tests/test_tools.py`.

## Lot de 20 designs aléatoires (graine 0)

Résultats : `runs/5090-random-seed0/` (hors Git). Durée : ~4 min avec 7 designs en parallèle, de 4 à 82 s par design selon la finesse du maillage.

| Cycle | Matériau | Section | Masse (g) | Flèche (mm) | FS min | f1 (Hz) | Faisable |
| --- | --- | --- | --- | --- | --- | --- | --- |
| réf. | PETG | U, 0 évidement | 32,1 | 1,13 | 4,5 | 70 | non |
| 11 | PLA-CF | U, 1 évidement | **39,1** | 0,35 | 5,2 | 124 | **oui** (score 0,82) |
| 7 | PLA-CF | U, 0 évidement | 41,0 | 0,16 | 5,5 | 119 | oui |
| 1 | PLA-CF | U, 2 évidements | 42,2 | 0,45 | 4,6 | 109 | oui |
| 19 | PLA-CF | U, 4 évidements | 25,6 | 0,56 | 2,3 | 87 | non : f1 |
| 16 | PETG | U, 5 évidements | 31,8 | 0,95 | 4,6 | 77 | non : f1 |
| 14 | PETG | plate, 4 évidements | 6,4 | 687 | 0,08 | 3 | non : tout |

Tous les designs du lot sont fabricables ; le cas d’échec de fabricabilité est couvert par un test.

## Constats

1. **La fréquence propre est la contrainte dimensionnante.** Parmi les bras nervurés non faisables, la plupart ne violent que f1 ≥ 100 Hz. Avec 60 g de moteur en bout de bras, tenir 100 Hz demande une raideur d’environ 26 N/mm, soit une flèche d’environ 0,6 mm sous 15 N, plus exigeant que la limite de 1 mm.
2. **La plage de rotation d’un moteur 7 pouces (≈ 130 à 330 Hz) est hors d’atteinte** pour un bras imprimé portant 60 g. Le seuil de 100 Hz est provisoire ; le porteur doit le fixer (voir K03).
3. **Le bras de référence provisoire est infaisable** (flèche 1,13 mm et f1 70 Hz) : le score « −15 % » n’a pas encore de base. Il faut la géométrie et la masse du bras réel.
4. **Sans nervure, aucun design ne tient** : une âme plate doit dépasser 10 mm d’épaisseur pour la flèche. Les nervures de bord et le PLA-CF dominent le front de Pareto, ce qui laisse de vrais arbitrages à l’agent (évidements contre fréquence).
5. **Stockage :** les champs CalculiX pesaient ~85 Mo par design (1,8 Go pour le lot). Ils sont désormais supprimés après lecture (`DRONE_AGENT_KEEP_FIELDS=1` pour les garder) : ~3 Mo par design, essentiellement le maillage.

## Limites connues

- Calcul linéaire : les flèches de plusieurs centimètres des designs très souples n’ont pas de sens physique ; elles servent seulement de pénalité.
- Matériau isotrope, sans anisotropie d’impression ni remplissage partiel.
- Pas encore de rayons de raccordement ni de nervure centrale ; chute en statique équivalente de 40 N latéral et 20 N vertical, à confirmer.
- Le maximum de contrainte exclut une bande de 3 mm à l’encastrement ; la sensibilité au maillage n’a pas été étudiée.
- Durée de vie d’un processus WSL après déconnexion SSH non vérifiée : à tester avant le lancement continu de mardi.
