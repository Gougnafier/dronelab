# Cahier des charges — Agent ingénieur drone (Paris Claw Challenge)

Sep 27, 2026 · @titi

## Contexte et objectif

Construire un agent qui tourne jour et nuit sur une machine locale et allège un châssis de drone imprimable en 3D, en décidant lui-même de ses essais. Soumission au NVIDIA Paris Claw Agent Challenge avant le 2 octobre 2026, avec une vidéo de 60 à 90 secondes.

**Pitch en une phrase :** « Je donne mon drone à l'agent le soir, le matin il me rend un châssis plus léger, testé en flexion, en chute et en vibration, et prêt à imprimer. »

L'agent ne remplace pas un optimiseur numérique : il **pilote la démarche d'ingénierie**. Il formule des hypothèses, choisit les cas de charge, arbitre les compromis, change de stratégie quand il stagne et documente tout dans un cahier de labo. L'optimisation fine est un outil qu'il appelle.

## Périmètre

L'agent redessine 2 ou 3 pièces d'un quadricoptère sans toucher aux interfaces ; tout le reste est hors périmètre.

**L'agent fait :**

- Lire un cahier des charges en langage naturel et en tirer objectifs et contraintes.
- Modifier les paramètres des pièces : bras, plaque inférieure, plaque supérieure (épaisseur, largeur, évidements, nervures, rayons, matériau).
- Choisir lui-même les cas de charge à tester pour chaque design.
- Lancer les calculs par éléments finis (statique et modal) et vérifier la fabricabilité.
- Tenir un cahier de labo et changer de stratégie quand il ne progresse plus.
- Tourner en continu plusieurs jours sans intervention, et prévenir l'utilisateur seulement quand un nouveau meilleur design est trouvé.

**L'agent ne fait pas :**

- Modifier les interfaces : fixations moteurs, stack du contrôleur de vol, fixation batterie.
- Importer ou modifier un assemblage STEP existant (géométrie non paramétrique).
- De l'aérodynamique ou de la simulation de vol (pas d'Isaac Sim).
- De la CFD.

## Cas de démo

Objectif : minimiser la masse du châssis en respectant toutes les contraintes ci-dessous. Les valeurs sont des points de départ à ajuster lundi selon ton drone réel.

| Élément | Valeur de départ |
| --- | --- |
| Type | Quadricoptère, hélices 7 pouces |
| Masse au décollage max | 1,2 kg |
| Poussée max par moteur | 15 N |
| Fabrication | Impression FDM, PETG ou PLA-CF, plateau 220 × 220 mm |
| Épaisseur de paroi min | 1,2 mm |
| Interfaces figées | Moteur 16 × 16 mm en M3, stack 30,5 × 30,5 mm en M3, sangle batterie |
| Facteur de sécurité min | 2 sur chaque cas de charge |
| Flèche max en bout de bras | 1 mm sous poussée max |
| Première fréquence propre du bras | Au-dessus de la plage de rotation des moteurs (seuil à fixer) |

**Cas de charge disponibles** (l'agent choisit lesquels lancer et dans quel ordre) :

1. Poussée max : force verticale au moteur, bras encastré au châssis.
2. Couple moteur : torsion du bras.
3. Manœuvre : facteur de charge vertical appliqué à tout le châssis.
4. Chute : impact sur un bout de bras, modélisé en statique équivalente.
5. Modal : trois premières fréquences propres du bras.

## Architecture et stack

Hermes gère la boucle, la planification et la mémoire ; toute la logique métier vit dans des outils Python exposés en MCP, testables sans LLM.

&#91;embedded content: architecture · 7 composants\]

Le cerveau passe par les endpoints build.nvidia.com pour laisser la RTX 5090 aux calculs. Chaque outil renvoie du JSON et ne plante jamais : une erreur devient un résultat « invalide » que l'agent lit.

**Stack :** Python 3.11, FreeCAD 1.x en mode `freecadcmd`, CalculiX, Gmsh ou Netgen pour le maillage, scipy ou Optuna, pyvista pour les rendus, Hermes pour l'orchestration.

**Structure du dépôt :**

```
drone-agent/
  spec/cahier_des_charges.yaml   # objectifs, contraintes, interfaces
  tools/                         # un fichier par outil, serveur MCP
  cad/                           # génération paramétrique des pièces
  fem/                           # cas de charge, maillage, CalculiX
  agent/                         # prompts, boucle, détecteur de plateau
  runs/results.jsonl             # une ligne par évaluation
  runs/notebook.md               # cahier de labo
  runs/designs/                  # STEP, STL, rendus PNG
  dashboard/                     # page de suivi
  evaluate.py                    # point d'entrée sans LLM
```

## Outils à implémenter

Sept outils, chacun testable seul en ligne de commande avant d'être branché sur l'agent. Chaque appel reçoit et renvoie du JSON, avec un identifiant de design pour tout relier.

| Outil | Entrée | Sortie |
| --- | --- | --- |
| `generate_part` | pièce, paramètres | `design_id`, STEP, STL, masse (g), encombrement |
| `check_manufacturability` | `design_id` | ok ou non, liste des violations (paroi mince, hors plateau, interface modifiée) |
| `run_fem` | `design_id`, cas de charge | contrainte de von Mises max (MPa), déplacement max (mm), facteur de sécurité |
| `run_modal` | `design_id` | 3 premières fréquences propres (Hz) |
| `render` | `design_id`, résultat optionnel | PNG de la pièce, avec carte des contraintes si fournie |
| `optimize_local` | paramètres de départ, bornes, objectif | meilleurs paramètres, historique |
| `notebook` | lecture ou écriture d'une entrée | résumé des N dernières entrées, ou confirmation |

**Règles communes :**

- Timeout de 5 minutes par calcul ; au-delà, résultat « invalide » avec la raison.
- Jamais d'exception qui remonte à l'agent : toute erreur est renvoyée comme résultat lisible.
- Chaque appel ajoute une ligne à `runs/results.jsonl`.
- `evaluate.py` enchaîne `generate_part` → `check_manufacturability` → `run_fem` sur tous les cas → `run_modal` et produit un score global, sans LLM.

## Boucle de l'agent et anti-plateau

Un cycle = un design évalué et une conclusion écrite ; le détecteur de plateau est codé en dur, l'agent ne peut pas l'ignorer.

&#91;embedded content: boucle de l'agent · 6 étapes, 1 décision\]

**Détecteur de plateau :** si le meilleur score n'a pas progressé de plus de 1 % depuis 15 cycles, le code impose une rétrospective. L'agent relit tout le cahier et répond à trois questions : qu'ai-je essayé, qu'est-ce qui a échoué et pourquoi, quelle piste n'ai-je jamais testée.

**Stratégies de relance (l'agent en choisit une et justifie) :**

1. Changer de paramétrage : ajouter des nervures, passer d'évidements ronds à des treillis, changer la section du bras.
2. Repartir d'un design très différent du meilleur actuel.
3. Relâcher une contrainte pour explorer, puis la resserrer.
4. Changer de matériau.
5. Déléguer une passe de réglage fin à `optimize_local`.

**Garde-fous :**

- Chaque cycle démarre avec un contexte neuf : cahier des charges, résumé du cahier de labo, 5 meilleurs designs. Jamais une conversation infinie.
- Un design invalide est noté et l'agent continue ; trois échecs d'outil d'affilée déclenchent une alerte.
- Notification à l'utilisateur uniquement pour un nouveau record ou un blocage.

## Cahier de labo et données

Deux fichiers font foi : `results.jsonl` pour les chiffres, `notebook.md` pour le raisonnement. Le tableau de bord et la vidéo se construisent uniquement à partir d'eux.

**Une ligne de `results.jsonl` :**

```json
{"cycle": 42, "design_id": "arm-0042", "timestamp": "2026-09-30T03:14:00+02:00", "part": "arm", "params": {"thickness_mm": 4.2, "width_mm": 14, "holes": 3, "rib": true, "material": "PETG"}, "manufacturable": true, "mass_g": 18.4, "load_cases": {"max_thrust": {"sf": 2.6, "deflection_mm": 0.7}, "crash": {"sf": 2.1}}, "modal_hz": [212, 540, 890], "score": 0.83, "valid": true}
```

**Une entrée de `notebook.md` :**

```markdown
### Cycle 42 · 2026-09-30 03:14
Hypothèse : une nervure centrale compense la perte de rigidité due au 3e évidement.
Essais choisis : poussée max, chute (le 3e trou fragilise le bout du bras).
Résultat : masse −6 %, facteur de sécurité en chute 2,1 (limite 2).
Conclusion : piste valable, marge en chute trop juste. Prochain essai : trou plus petit côté moteur.
```

**Résumé automatique :** toutes les 10 entrées, l'agent réécrit un résumé de 15 lignes maximum (pistes gagnantes, impasses, record actuel). C'est ce résumé, pas le cahier entier, qui entre dans le contexte de chaque cycle.

## Livrables, planning et plan B

L'agent doit tourner en continu au plus tard mardi soir : chaque nuit d'historique réel est la preuve du « long-running ».

**Planning :**

1. **Dimanche soir** : `evaluate.py` sur un bras paramétrique, 20 designs aléatoires, résultats en JSON.
2. **Lundi** : les 5 cas de charge, le calcul modal, la vérification de fabricabilité. **Point de décision : si FreeCAD FEM ne tourne pas de façon fiable lundi soir, bascule sur le plan B.**
3. **Mardi** : outils exposés en MCP, branchés dans Hermes, boucle et détecteur de plateau. Lancement en continu le soir.
4. **Mercredi** : plaques du châssis, rendus, tableau de bord. L'agent continue de tourner.
5. **Jeudi** : tournage de la vidéo, description, impression 3D du meilleur design si possible.
6. **Vendredi matin** : soumission, avant la clôture du 2 octobre.

**Livrables :**

- Vidéo de 60 à 90 s : le problème, le cahier des charges, le timelapse des designs, la courbe qui plafonne puis repart après une rétrospective, la pièce finale.
- Description courte : ce que fait l'agent, pourquoi, pour qui.
- Dépôt de code avec README.

**Critères de réussite :**

- [ ] Au moins 48 h de fonctionnement sans intervention.
- [ ] Masse du châssis réduite d'au moins 15 % avec toutes les contraintes respectées.
- [ ] Au moins une rétrospective suivie d'une vraie progression, visible dans le cahier.
- [ ] Le design final passe la vérification de fabricabilité et s'exporte en STL.

**Plan B, l'aile :** mêmes principes, mais AeroSandbox remplace FreeCAD FEM. L'agent optimise une aile de drone à voilure fixe (autonomie, stabilité, masse) et choisit ses conditions d'essai : croisière, virage, vent de travers, rafale. AeroSandbox exporte la géométrie en STL, FreeCAD ne sert plus qu'à la fabricabilité.
