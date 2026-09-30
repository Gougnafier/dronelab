# Consignes pour ce dépôt

Ces consignes s'adressent aux assistants de code qui travaillent sur le dépôt.

- Écrire la documentation et les comptes rendus en français ; utiliser des noms de code explicites en anglais.
- Lire `README.md`, `docs/project.md`, `docs/decisions.md` et `docs/kanban.md` avant un bloc de travail.
- **Construire le laboratoire, pas le travail de l'agent.** Les outils, la boucle, l'épreuve et les compétences décrivent des règles et une méthode, jamais une solution de conception ni un exemple qui en suggère une. Les messages de l'équipe à l'agent annoncent des outils ou des changements de règles, sans conseil d'ingénierie.
- L'épreuve officielle (`spec/lift_exam.yaml`, `src/drone_agent/lift/exam.py`) reste hors de portée des agents. Une limite signalée par un agent se corrige par une décision consignée dans `docs/decisions.md`.
- Un agent qui tourne longtemps doit conserver son état, reprendre après interruption, borner délais et tentatives, respecter un budget et garder un journal de décisions exploitable.
- Travailler par blocs courts et vérifiables : définir l'entrée, la sortie et le critère de réussite, faire le plus petit essai qui éclaire la décision, vérifier le cas normal et un échec pertinent. Tenir `docs/kanban.md` à jour ; ne pas confondre essai ponctuel, test prévu et capacité validée.
- Placer le code dans `src/`, les tests dans `tests/`, les commandes reproductibles dans `scripts/` et les comptes rendus dans `docs/`. Les agents écrivent uniquement dans `runs/<produit>/workspace/`.
- Garder secrets, clés, données personnelles, conversations privées et artefacts volumineux hors Git (`runs/` et `data/` sont ignorés ; `course/` est un export nettoyé par `scripts/export_run.py`). Vérifier et consigner la provenance ainsi que la licence de toute ressource externe utilisée.
- Ne pas envoyer de message, publier, déployer ou modifier un service externe sans instruction explicite correspondante.
- La candidature se clôt le 2 octobre 2026 à 23 h 59, heure du Pacifique, soit le samedi 3 octobre à 8 h 59 à Paris. Le règlement est résumé dans `docs/project.md`.
