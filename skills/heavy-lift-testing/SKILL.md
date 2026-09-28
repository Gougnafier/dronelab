---
name: heavy-lift-testing
description: Comment tester correctement un multirotor lourd sur l'épreuve DARPA Lift avec le modèle du dépôt (marges, facteurs limitants, contrôles de vraisemblance, limites du modèle). Charger pour le produit heavylift.
version: 1.0.0
category: engineering
---

# Tester un multirotor lourd

## Ce que mesure l'évaluation

`evaluate_design` cherche la plus grande charge, par pas de 2,5 lb (plus petit disque autorisé), qui passe **tous** les contrôles sur le parcours (décollage, montée à 150 ft, croisière chargée, largage en stationnaire, croisière à vide, descente, atterrissage) :

- `energy` : énergie de mission + réserve ≤ énergie utilisable de la batterie ;
- `thrust_to_weight` : poussée statique max ≥ marge × poids chargé (autorité de commande) ;
- `battery_power` : puissance demandée à cette poussée ≤ puissance continue de la batterie (C) ;
- `arm_strength`, `arm_deflection` : bras en tube carbone encastré au moyeu ;
- hors charge : masse de l'aéronef < 55 lb et 1re fréquence du bras écartée des bandes 1P et passage de pales.

Une valeur de `checks_at_max` proche de 0 est une contrainte active : c'est elle qu'il faut desserrer. Plusieurs contraintes actives à la fois indiquent un design équilibré ; il faut alors changer d'architecture ou de technologie pour progresser.

## Contrôles de vraisemblance avant de croire un record

- **Charge alaire du disque** (`disk_loading_n_m2`) : les gros multirotors efficaces sont vers 100–300 N/m². Au-delà, la puissance de sustentation explose ; en dessous, l'encombrement devient déraisonnable (`span_m`).
- **Efficacité en stationnaire** : poids / puissance électrique. Pour de grandes hélices, quelques g/W à 10 g/W ; une valeur plus haute signale une hypothèse trop optimiste (facteur de mérite, rendement).
- **Masses** (`mass_breakdown_kg`) : vérifier que chaque poste reste plausible face à des produits réels (moteur d'une dizaine de kW, hélices de 40 pouces et plus, pack de 12S). Les lois de masse sont des hypothèses.
- **Vitesse de croisière** : une valeur collée à la borne supérieure est suspecte ; la traînée de la charge et du corps est une hypothèse simple.

## Limites connues du modèle (à mentionner, pas à ignorer)

Pas de vent latéral ni de rafale, pas d'échauffement moteur, pas de dynamique de commande, pas de fatigue ni de calcul des liaisons, facteur de mérite constant, batterie à tension constante. Un design qui n'a de marge sur aucun de ces points est fragile en réalité. Tu peux proposer d'ajouter un essai (par exemple vent de face via `environment.headwind_m_s`) en le justifiant dans le cahier ; le changement passe par `propose_model_update`.

## Bonnes pratiques

- Tester l’édition DLC-2 (`edition="dlc2"`, 220 lb, 10 nmi) sur les meilleurs designs pour mesurer la robustesse.
- Après un record, lancer `sensitivity` : si le score dépend surtout d'une hypothèse non sourcée, la sourcer devient la priorité.
- Règlement : https://www.darpa.mil/research/challenges/lift/rules (VTOL, charge en disques de fonte regroupés en un point, masse aéronef énergie comprise).
