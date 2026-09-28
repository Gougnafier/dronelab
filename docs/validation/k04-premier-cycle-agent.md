# K04 — Premier cycle réel de l’agent autonome

Date : 28 septembre 2026, 0 h. Machine de développement.

**Objectif :** vérifier la chaîne complète superviseur → Hermes (profil `dronelab`, Nemotron 3 Ultra via build.nvidia.com) → serveur MCP → modèle heavylift → cahier de labo.
**Résultat :** chaîne fonctionnelle sur un cycle réel.

## Commande

```bash
python scripts/run_agent.py --product heavylift --hermes-cmd dronelab --max-cycles 1 --pause 0 --cycle-timeout 1500
```

## Observé

- Cycle réussi en ~7 min : 198 évaluations (aléatoires ciblées, essais un par un, 2 réglages fins), une entrée de cahier en français, chiffrée, avec facteurs limitants et prochaine étape.
- Raisonnement pertinent : l’agent identifie seul deux verrous (puissance continue des batteries Li-ion, 1re fréquence des bras dans la bande 1P) et propose des pistes pour chacun.
- Une erreur de raisonnement visible : il attribue au coaxial un gain de surface de disque, ce que le modèle ne donne pas. C’est au cycle suivant de le réfuter par l’essai.
- Aucun design qualifiant au premier cycle (meilleur : 51 kg pour 24,9 kg, bloqué par la puissance batterie) ; pas de notification de record, comme prévu.
- Avertissements Hermes sans effet : jeu d’outils `messaging` inconnu, scanner `tirith` absent.

## Tests sans LLM

`python -m pytest -q` : 24 tests (bras imprimé, modèle heavylift, noyau de l’agent). Le faux runner des tests joue l’ingénieur pour vérifier : cycle sans entrée = échec, alerte après 3 échecs, record notifié seulement s’il qualifie, reprise après redémarrage, rétrospective imposée au plateau, consigne transmise et traitée, proposition appliquée seulement après validation, prompt borné aux 5 meilleurs, rapports une fois par créneau.

## Vérification du modèle heavylift (hors agent)

Contrôles faits par Claude pour valider l’outil, pas pour résoudre le problème : théorie de la quantité de mouvement retrouvée à vitesse nulle, charge max = dernier pas qui passe tous les contrôles. Une recherche par évolution différentielle atteint 3,24:1 sous les hypothèses actuelles : le modèle paramétrique seul se résout en minutes. La valeur de l’agent dans la durée doit donc venir de la remise en cause des hypothèses (sources, sensibilité), de l’élargissement de l’espace de conception et des vérifications.

## Limites

- Machine de développement : le fonctionnement 24 h/24 n’est pas encore garanti (pas de service ni de redémarrage automatique).
- Messages entrants Discord (consignes, validations) : outils prêts (rôle *desk*), branchement à une passerelle à décider.
- Budget build.nvidia.com : consommation par cycle non mesurée.
