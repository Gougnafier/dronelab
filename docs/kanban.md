# Kanban

Direction : ingénieur produit autonome qui conçoit de zéro un multirotor lourd pour une épreuve simulée DARPA Lift, contrôlé par un vérificateur et un éclaireur ([décisions](decisions.md)). Soumission avant le 2 octobre 2026 à 23 h 59, heure du Pacifique, soit le samedi 3 octobre à 8 h 59 à Paris ([règlement](project.md#règlement-et-soumission-lu-le-30-septembre-2026)). Viser le vendredi soir.

| À faire | En cours | Terminé |
| --- | --- | --- |
| K12 · Épreuve v4 (limites signalées par l'agent) · K13 · Course propre de bout en bout | K11 · Vidéo et soumission | K04 · K05 · K06 · K07 · K10 |

## K11 — Vidéo et soumission (en cours)

- Fait : audit de la course ([audit du 29/09](validation/audit-agent-2026-09-29.md)), tableau de bord et vidéo des temps forts, chronologie Discord, README présentable, export des traces dans `course/`, brouillon des réponses au formulaire et plan de la vidéo de 90 s (documents de travail du porteur, hors dépôt).
- Reste au porteur : enregistrer et mettre en ligne la vidéo, publier le dépôt, remplir et envoyer le formulaire.

## K04 à K07, K10 — Laboratoire et course (terminés)

- Superviseur (contexte neuf par cycle, cahier obligatoire, plateau → rétrospective, reprise, attente sur limite de débit, arrêt par `STOP`), serveur MCP à outils filtrés par rôle, quatre profils Hermes, passerelle Discord.
- Épreuve MuJoCo sur la RTX 5090 (v3 : dossiers compilés seulement, bancs vent, rafales, chaleur, altitude), atelier (catalogue vérifié, pièces CAO, éléments finis CalculiX, compilateur d'assemblage), veille YouTube.
- Validé en conditions réelles : course continue des cycles 74 à 109 (28-29 septembre, environ 14 h), arrêtée manuellement.

## K12 — Épreuve v4 (à faire)

Corriger les limites signalées par l'agent : aire frontale projetée réelle, résistance interne de la batterie, paliers batterie révisés sur sources, marge de poussée cohérente avec la puissance de pointe, pénalité de recouvrement calibrée selon Z/D.

## K13 — Course propre de bout en bout (à faire)

Lancer `scripts/start_clean_run.sh` : espace de travail vide, mission envoyée sur Discord, compétences non modifiables par les agents.
