# Cadrage

## Direction

**Ingénieur produit autonome** (décisions des 27 et 28 septembre 2026, voir [décisions](decisions.md)). L'agent reçoit un problème d'ingénierie produit. Il choisit ses pièces et ses essais, lance les calculs, tient un cahier de labo et rend compte sur Discord. D'autres agents le contrôlent : un vérificateur audite chaque cycle, un éclaireur ramène les problèmes du monde réel.

**Démonstration :** concevoir de zéro un multirotor lourd pour l'épreuve simulée du DARPA Lift Challenge (aéronef < 55 lb, charge ≥ 110 lb, 5 nmi ; score = charge / masse).

## Réponses aux questions de cadrage

1. **Public :** équipes et ingénieurs qui conçoivent un produit matériel sous contraintes et n'ont pas le temps d'explorer des centaines de variantes ni de tenir la trace de leurs essais.
2. **Tâche longue :** des cycles hypothèse → essais → conclusion pendant des heures ou des jours, avec audit indépendant, veille terrain et rétrospectives imposées quand le progrès plafonne.
3. **Résultat mesurable :** ratio charge / masse sur l'épreuve, robustesse aux bancs d'essai, cahier de labo et sources.
4. **Démonstration :** progression du record avec les corrections de réalisme, pièces conçues, échanges sur Discord, rapports rédigés par l'agent.
5. **Ressources :** Hermes Agent (quatre profils), machine de développement, RTX 5090 par SSH pour la simulation et les éléments finis.

## Règlement et soumission (lu le 30 septembre 2026)

Source : règlement officiel « Paris Claw Agent Challenge », transmis par le porteur.

- **Date limite** : 2 octobre 2026 à 23 h 59, heure du Pacifique. Le règlement écrit « PST », mais la côte ouest est à l'heure d'été (PDT, UTC−7) à cette date. Retenir l'heure la plus prudente : **samedi 3 octobre, 8 h 59 à Paris**. Objectif interne : soumettre le **vendredi 2 octobre au soir**.
- **Soumission** : l'inscription vaut soumission, par le formulaire Airtable `https://airtable.com/appREoLM7BnGWxRzJ/pagLOxwVLzgiOaunm/form`. Champs relevés : vidéo de 3 min maximum (30 à 90 s de préférence, YouTube ou Loom) ou lien vers le projet. C'est le porteur qui soumet, pas un agent.
- **Éligibilité** : particulier majeur résidant en France ; aucune candidature d'entreprise ou d'institution. La candidature est donc individuelle, même si la démonstration parle de « l'équipe » d'agents.
- **Critères du jury (NVIDIA)** : exécution technique, innovation, valeur dans le monde réel (liste non limitative). Deux lauréats, annoncés vers le 6 octobre ; 7 jours pour répondre à la notification.
- **Points d'attention** : une candidature peut être retirée en cas de réclamation de droits d'auteur. Ne montrer ni vidéos YouTube de tiers ni images sous licence dans la démo ; les citations courtes des notes de terrain, avec leur source, restent possibles. Le nom et le lieu de résidence des lauréats peuvent être publiés. Avant de rendre le dépôt public, vérifier qu'il ne contient ni secret ni donnée personnelle.
