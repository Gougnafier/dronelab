# Brainstorming — 27 septembre 2026 (soir)

Trace des échanges entre le porteur et Claude après le bloc K02. Les décisions retenues sont reprises dans [decisions.md](decisions.md).

## 1. Un agent d’ingénierie, pas seulement un agent drone

**Porteur :** l’agent ne doit pas être spécifique au drone. Il doit accepter différents travaux d’ingénierie, surtout l’optimisation d’un produit, avec des compétences qui lui apprennent à tester correctement, un accès à Internet pour chercher comment bien tester un produit, et un lien avec l’utilisateur (consignes, retours sur l’avancement).

**Réponse et propositions :**

- Le brief demande un agent qui avance « sans surveillance à chaque étape » : cela n’interdit pas l’interaction. Modèle retenu : l’agent ne bloque jamais sur l’utilisateur, il rend compte de lui-même (record, blocage, résumé), lit les consignes au cycle suivant, et demande validation avant de modifier une contrainte.
- Architecture en **noyau générique** (boucle, cahier de labo, détecteur de plateau, budget, canal utilisateur, recherche) et **paquets produit** (spec, générateur paramétrique, cas de charge décrits en données, compétence de test). Environ 70 % du code K02 est déjà générique.
- Compétences de test : fiches lisibles par l’agent (choix des cas, facteurs de sécurité usuels, singularités, anisotropie de l’impression), plus deux garde-fous codés : validation contre un calcul à la main avant de faire confiance à un paquet, et vérification de convergence de maillage sur chaque record.
- Internet : recherche au cadrage et en rétrospective seulement, sources citées dans le cahier, jamais de changement de contrainte sans accord, budget d’appels dédié, contenu web traité comme donnée et non comme instruction.

## 2. Nouvelle démonstration : un drone qui porte quatre fois son poids

**Porteur :** s’inspirer d’une compétition mondiale où le drone doit porter quatre fois son poids. L’agent cherche en ligne les composants (fiches techniques, masses, performances, fichiers 3D), intègre le tout en 3D, produit un fichier OpenUSD et simule l’épreuve de la compétition (Omniverse, ou bibliothèques plus légères). Rapport une à deux fois par jour par tâche planifiée, avec graphiques, images et vidéo de l’avancement.

**Compétition identifiée :** [DARPA Lift Challenge](https://www.darpa.mil/research/challenges/lift) ([règlement](https://www.darpa.mil/research/challenges/lift/rules)), relevé du 27 septembre 2026 :

| Élément | DLC-1 (août 2026) | DLC-2 (été 2028) |
| --- | --- | --- |
| Masse de l’aéronef, énergie comprise, charge exclue | < 55 lb (24,9 kg) | ≤ 55 lb |
| Charge minimale qualifiante | 110 lb (49,9 kg) | 220 lb (99,8 kg) |
| Parcours | 4 nmi chargé, largage, 1 nmi à vide, à 150 ft | 8 nmi chargé, 2 nmi à vide |
| Score | charge max / masse de l’aéronef ; départage par charge puis par temps | idem, objectif > 4:1 |

Autres règles : décollage et atterrissage verticaux, plus lourd que l’air, charge en disques de fonte Olympic (2,5 à 45 lb) regroupés en un point, vol à vue avec pilote Part 107, coupe-circuit obligatoire. L’inscription est réservée aux entités américaines : **on ne concourt pas**, on utilise l’épreuve comme banc d’essai public et exigeant.

**Réponse et propositions :**

- Bonne idée : vrai problème de dimensionnement couplé (rotors, moteurs, batterie, structure), tâche longue par nature (base de composants construite et vérifiée au fil des jours), et le calcul de bras de K02 devient l’outil de vérification structurelle.
- Ordre de grandeur : à 4:1, la masse totale vaut 5 fois la masse à vide ; avec une marge de poussée de ~2, il faut ~10 fois le poids à vide en poussée. Sur batterie, la puissance de sustentation d’un appareil de 125 kg rend 4:1 très difficile : c’est précisément l’enjeu.
- Données composants : oui, avec provenance et contrôles de cohérence (poussée/puissance, unités) ; repli sur une petite base vérifiée à la main si l’extraction web n’est pas fiable.
- Fichiers 3D des fabricants : non (accès, licences). Maquettes paramétriques aux bonnes cotes et masses.
- Simulation : modèle maison en Python (puissance par théorie de la quantité de mouvement, énergie de mission, marges, structure), export OpenUSD pour la visualisation. Omniverse / Isaac Sim seulement en bonus.
- Rapports : la recherche tourne en continu sur la 5090 ; une tâche planifiée deux fois par jour produit courbes, images, timelapse et résumé, envoyés sur Discord. Hermes gère nativement les tâches planifiées et la livraison Discord ([documentation cron](https://hermes-agent.nousresearch.com/docs/user-guide/features/cron)).

## 3. Réponses du porteur

- Compétition : DARPA Lift Challenge.
- Canal : **Discord**.
- Démarrer tout de suite, sans attendre lundi.

## Questions ouvertes

- Viser DLC-1 (110 lb, 5 nmi) ou DLC-2 (220 lb, 10 nmi) comme épreuve de référence ? Par défaut : DLC-1, DLC-2 en variante.
- Recherche web libre dans un budget ou soumise à validation ? Par défaut : libre dans un budget, validation obligatoire pour tout changement de contrainte.
- Deuxième paquet produit pour prouver la généralité (dissipateur thermique, support) : après le lancement continu.

## 4. Nuit du 28 septembre : qui fait quoi, et une vraie simulation

**Porteur :** pourquoi est-ce Claude qui construit le drone et pas l'agent ? Les résultats envoyés sur Discord sont-ils de la simulation ? Souhaits : une épreuve simulée qui produit des chiffres dans le temps (pour que l'agent comprenne le vol) et une vidéo (pour que l'humain vérifie que le rapport colle à ce qu'il voit) ; partir d'un projet vide, l'agent cherche lui-même des ressources en ligne ou fabrique ses propres drones simples ; un agent parallèle qui vérifie que l'ingénieur n'hallucine pas.

**Constat honnête :** jusque-là, les résultats venaient d'un modèle analytique écrit par Claude (équations, pas de simulation 3D) ; l'agent ne réglait que 9 paramètres. Seul le calcul par éléments finis des bras était une simulation numérique, et l'agent ne l'avait pas encore utilisé.

**Nouveau partage :** nous construisons le laboratoire (outils génériques) et l'examen (épreuve simulée fixe, tirée du règlement) ; l'agent construit le drone, de zéro.
