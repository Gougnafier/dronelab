# Consignes pour ce dépôt

- Écrire la documentation et les comptes rendus en français ; utiliser des noms de code explicites en anglais.
- Lire `README.md`, `docs/project.md`, `docs/decisions.md` et `docs/kanban.md` avant un bloc ; suivre `docs/workflow.md`.
- Le dépôt est volontairement neutre. Ne pas transformer les pistes 3D ou radio en direction décidée, ni importer leur code ou leurs dépendances sans décision consignée dans `docs/decisions.md`.
- Commencer par clarifier le problème, le public, la tâche autonome et la preuve visible du résultat. Ne pas choisir une stack, un agent existant ou une interface sur la seule base des anciens essais.
- Un agent qui tourne longtemps doit conserver son état, reprendre après interruption, borner délais et tentatives, respecter un budget et garder un journal de décisions exploitable. Adapter ces exigences au cas d’usage retenu.
- Travailler par blocs courts et vérifiables. Tenir `docs/kanban.md` à jour ; ne pas confondre essai ponctuel, test prévu et capacité validée.
- Quand une implémentation sera décidée, placer le code dans `src/`, les tests utiles dans `tests/`, les commandes reproductibles dans `scripts/` et les comptes rendus dans `docs/`.
- Garder secrets, données personnelles, conversations privées et artefacts volumineux hors Git. Vérifier et consigner la provenance ainsi que la licence de toute ressource externe utilisée.
- Ne pas envoyer de message, publier, déployer ou modifier un service externe sans instruction explicite correspondante.
- La candidature est annoncée pour le 2 octobre 2026 ; l’heure et le règlement restent à vérifier avant soumission. Favoriser une démonstration réelle de la tâche choisie.
