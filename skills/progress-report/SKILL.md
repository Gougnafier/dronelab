---
name: progress-report
description: Rédiger un rapport d'avancement utile à l'utilisateur, pour n'importe quel produit, avec des graphiques choisis par l'agent (plot_progress, plot_results) et envoyé par send_report. Charger pour les sessions de rapport et quand l'utilisateur demande où en est le projet.
version: 1.0.0
category: engineering
---

# Rédiger un rapport d'avancement

Le lecteur est l'utilisateur, sur son téléphone, entre deux choses. Il doit comprendre en 30 secondes où en est le projet, ce qui a changé et s'il doit décider quelque chose.

## Contenu (dans cet ordre, 12 lignes et 1 900 caractères maximum)

1. **Chiffre clé par rapport à l'objectif** : le record actuel, avec son unité et ce qu'il signifie (« 3,1 kg portés par kg d'aéronef ; seuil de qualification 2:1, objectif 4:1 »). S'il n'y a pas encore de design qualifiant, le dire franchement et donner le plus proche.
2. **Ce qui a changé depuis le dernier rapport** : progression chiffrée, nombre de cycles, rétrospectives.
3. **Ce qui a marché, ce qui a échoué** : une ligne chacun, avec la raison physique.
4. **Ce qui limite maintenant** : la contrainte active et la piste pour la desserrer.
5. **Confiance** : ce qui a été vérifié (par exemple `verify_arm_fem`) et les hypothèses de modèle encore non sourcées dont dépend le résultat.
6. **Décisions attendues de l'utilisateur** : propositions de modèle en attente, questions. Rien si rien.
7. **Suite** : les prochaines pistes.

## Graphiques (1 à 3)

- Toujours `plot_progress` : la courbe du meilleur score montre la progression et les rétrospectives.
- Puis un ou deux `plot_results` choisis pour **ce** produit et **ce** moment : le compromis central du problème (par exemple la grandeur objectif contre la grandeur qui la limite), avec `reference_lines` pour les seuils des règles. Utilise `result_fields` pour connaître les champs disponibles.
- Un graphique doit répondre à une question que le texte pose ; sinon, ne pas l'envoyer.

## Style

Français, phrases courtes, chiffres avec unités, pas de jargon d'outil (pas de noms de fonctions ni d'identifiants internes, sauf l'identifiant du record). Honnête : ne pas présenter une hypothèse de modèle comme un fait mesuré.
