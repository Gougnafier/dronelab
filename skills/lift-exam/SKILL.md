---
name: lift-exam
description: Passer et comprendre l'épreuve simulée DARPA Lift (MuJoCo) - format du dossier de conception, lecture de la télémétrie, diagnostic des échecs. Charger pour le produit lift_challenge.
version: 1.0.0
category: engineering
---

# L'épreuve simulée

`run_exam(design_dir, payload_kg, hypothesis)` fait voler ton drone sur le parcours : décollage avec la charge (disques de fonte), montée à 150 ft, 4 nmi chargé, largage en stationnaire, 1 nmi à vide, descente, atterrissage. L'épreuve impose sa physique (poussée max et puissance électrique de chaque rotor calculées par la théorie de la quantité de mouvement à partir du diamètre d'hélice et de la puissance moteur, traînée, batterie) et son pilote automatique. Elle est la seule mesure qui fait foi.

Avant chaque épreuve : `check_design` (format, masses, garde-fous). Un dossier refusé coûte un essai pour rien.

## Bancs d'essai (scénarios)

`run_exam(..., scenario=...)` : `nominal` (seul compté pour le score), `vent` (traversier 8 m/s), `rafales` (4 m/s + rafales de 5 m/s), `chaleur` (38 °C, air moins dense, moteurs plus chauds), `altitude` (1 500 m). Un design sérieux passe le nominal **et** tient les bancs pertinents ; l'éclaireur et le vérificateur peuvent te les demander.

## Échauffement des moteurs

Chaque vol calcule la température des moteurs (`motor_temp_max_c` dans la télémétrie, `max_motor_temp_c` dans le résultat) à partir des pertes et de la puissance continue du catalogue. Une puissance de pointe (`peak_power_w` au catalogue) est utilisable brièvement ; au-delà de 150 °C, échec « surchauffe moteur ». Déclarer une puissance de pointe comme continue est une erreur de sourçage.

## Résonance des bras

Le rapport de compilation donne, pour chaque bras, la première fréquence propre et les bandes de rotation (1P) et de passage des pales (2P) de l'hélice, à vide et à pleine charge. Un avertissement « résonance probable » impose de changer le bras (diamètre, paroi, longueur) ou la masse en bout.

## Version 3 : seulement des assemblages compilés

Un dossier d'épreuve se produit avec `assembly_compile` (compétence assembly-design) ; un drone.xml écrit ou modifié à la main est refusé. Les masses viennent du catalogue et de la CAO.

## Règles héritées de la version 2

- Hélices : dans un même plan, entraxe ≥ demi-somme des diamètres + 2 %. Un recouvrement est permis si les deux hélices sont décalées en hauteur d'au moins 10 % du plus petit diamètre ; chaque rotor concerné paie alors +20 % de puissance × fraction de disque recouverte (coaxial complet : +20 %).
- Masses minimales par famille de pièces (variateurs par kW, hélices selon le diamètre, câblage, avionique, train, moyeu) : voir `mass_floors` du brief et `minimum_masses_kg` de `check_design`.
- Batterie par paliers : ≤ 200 Wh/kg jusqu'à 25 C ; ≤ 260 Wh/kg jusqu'à 6 C ; au-delà, refusé.
- Bras en tube : `structure` dans design.json ; contrainte de flexion à poussée max ≤ 400 MPa / 1,5 ; masse des geoms arm_* ≥ masse des tubes déclarés.
- Poussée statique max ≥ 1,6 × poids chargé : `check_design` donne `max_payload_for_thrust_margin_kg`.
- `near_limits` liste les déclarations collées à un plafond : le vérificateur les examine. Des valeurs sourcées, pas calées sur les plafonds.
- La charge appliquée est le multiple de 2,5 lb inférieur ou égal à la charge demandée (`payload_requested_kg` / `payload_kg`) : ne répète pas un essai qui arrondit à la même charge.

## Lire le résultat

- `passed`, `failure` (`reason`, `t`, `phase`, `context` : batterie, puissance, limitation de puissance batterie, poussée max, altitude au moment de l'échec) et `score`.
- `phases` : pour chaque phase, énergie consommée, poussée max relative (`max_throttle` ; 1,0 = moteurs à fond), puissance moyenne, écart de trajectoire max.
- `exam_telemetry(exam_id, columns, t_from, t_to, every_s)` : séries temporelles. Pour comprendre un échec, lis la fenêtre qui le précède à pas fin (every_s=0.5), puis la tendance globale à pas large.

## Diagnostics types

| Symptôme dans la télémétrie | Cause probable | Piste |
| --- | --- | --- |
| `throttle_max` ≈ 1 en montée, `z` en retard sur `z_ref`, échec « montée impossible » | poussée insuffisante | plus de puissance ou de surface de disque, moins de masse |
| `battery_pct` décroît linéairement jusqu'à 0 en croisière, « batterie épuisée » | énergie insuffisante | énergie = puissance × temps : réduire la puissance de croisière (disque plus grand, masse), plus de Wh, vitesse de croisière optimale |
| `power_limited` = 1, `power_w` plafonne, `tracking_error_m` grandit ou chute | limite de puissance batterie (C) | batterie plus puissante ou puissance demandée plus faible |
| `tilt_deg` oscille puis dépasse 70° | contrôle instable ou rotors mal placés/orientés | vérifier sites, spins alternés, symétrie, centre de gravité sous le plan des rotors |
| « dossier refusé » | format, plausibilité, masses minimales, hélices, bras, marge de poussée | lire `refused_because` et corriger |

Calcule les ordres de grandeur toi-même avant d'essayer : puissance de sustentation idéale P = T^1,5 / √(2ρA), temps de mission, énergie nécessaire. Un essai doit tester une hypothèse chiffrée, pas deviner.

## Trouver la charge maximale

Le score récompense la charge. Une fois un parcours réussi, augmente la charge par pas (2,5 lb minimum) ou par dichotomie pour trouver la limite, et note ce qui casse en premier.
