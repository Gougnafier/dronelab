# Cadrage

## Direction

**Ingénieur produit autonome** (décisions des 27 et 28 septembre 2026, voir [décisions](decisions.md) et [brainstorming](brainstorming.md)). L’agent reçoit un problème d’optimisation de produit, choisit ses essais, lance les calculs, tient un cahier de labo, remet en cause son modèle avec des sources validées par l’utilisateur, et rend compte sur Discord.

**Démonstration :** dimensionner un multirotor lourd pour l’épreuve du DARPA Lift Challenge (aéronef < 55 lb, charge ≥ 110 lb sur 4 nmi chargé + 1 nmi à vide, score = charge / masse). **Plan B :** allègement du bras imprimé d’un quadricoptère 7 pouces ([cahier des charges initial](cahier-des-charges.md)).

## Réponses aux questions de cadrage

1. **Public :** équipes et ingénieurs qui conçoivent un produit sous contraintes et n’ont pas le temps d’itérer sur des centaines de variantes ni de tenir la trace de leurs essais.
2. **Tâche longue :** des cycles hypothèse → essais → conclusion pendant des jours, avec rétrospectives imposées quand le progrès plafonne et recherche de données réelles.
3. **Résultat mesurable :** ratio charge / masse sur l’épreuve, marges de chaque contrainte, cahier de labo et sources.
4. **Démonstration :** courbe du meilleur score, plateau puis reprise après rétrospective, consigne envoyée sur Discord et prise en compte, rapport avec graphiques.
5. **Ressources :** Hermes (profil `dronelab`), endpoints build.nvidia.com, machine de développement, RTX 5090 par SSH pour les calculs lourds.
