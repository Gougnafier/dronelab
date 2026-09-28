# Kanban

Direction : agent d’ingénierie produit autonome qui conçoit de zéro un multirotor pour une épreuve simulée DARPA Lift (MuJoCo), vérifié par un second agent ([décisions](decisions.md), [brainstorming](brainstorming.md)). Soumission avant le 2 octobre 2026.

| À faire | Prêt | En cours | À valider | Terminé |
| --- | --- | --- | --- | --- |
| K08 · Export OpenUSD des conceptions de l’agent | K09 · Vidéo et soumission | K10 · Conception de zéro en continu (lift_challenge) | K04 · K05 · K06 | K00 · K01 · K02 · K07 (remplacé par la recherche de l’agent) |

## K02 — Évaluation sans LLM du bras imprimé (plan B)

Terminé : [compte rendu](validation/k02-evaluation-bras.md). Produit `printed_arm` enregistré dans le registre.

## K03 — Calage sur le drone 7 pouces réel

Seulement si le plan B est réactivé : seuil de fréquence, bras de référence, masses, efforts de chute, fiches filaments.

## K04 — Agent autonome

- Fait : modèle heavylift (`spec/darpa_lift.yaml`), superviseur, serveur MCP deux rôles, profil Hermes `dronelab` (Nemotron 3 Ultra), 3 compétences, rapports graphiques, notifications `hermes send`, 24 tests.
- Essai réel : un cycle réussi ([compte rendu](validation/k04-premier-cycle-agent.md)).
- À valider : plusieurs cycles d’affilée, dont une rétrospective réelle ; consommation d’API par cycle.

## K05 — Canal Discord

- Fait : salon `#drone-lab`, notifications sortantes, profil `dronedesk` (outils *desk*, personnalité dédiée).
- Fait : bot existant rattaché à `dronedesk` (passerelle en service, salon `#drone-lab` seulement). À valider : un échange réel (question d’avancement, consigne transmise puis traitée par l’ingénieur).

## K06 — Fonctionnement continu (preuve de concept)

- En cours : service `dronelab-agent` sur la machine de développement, calcul de vérification sur la RTX 5090 par SSH, rapports rédigés par l’agent à 8 h et 20 h dans `#drone-lab`.
- Arrêt propre : `touch runs/heavylift/STOP` ; relance : même commande, reprise au cycle suivant.

## K07 — Base de composants sourcés

- Catalogue moteurs, hélices, batteries avec provenance et contrôles ; conception à partir de composants réels plutôt que de lois d’échelle.

## K08 — OpenUSD et essai simulé

- Export de l’assemblage en OpenUSD ; essai de levage simulé en Python ; rendus et timelapse pour les rapports et la vidéo.

## K10 — Conception de zéro, épreuve simulée, vérificateur

- Fait : épreuve MuJoCo (5090) + vidéo (rejeu local), outils `check_design`, `run_exam`, `exam_telemetry`, `exam_list`, vérificateur `dronecheck` en parallèle, compétences `lift-exam`, `drone-from-scratch`, `audit-claims`, 28 tests.
- En cours : lancement continu ; à observer : premier dossier écrit par l’agent, premier vol réussi, premier audit, première rétrospective.
