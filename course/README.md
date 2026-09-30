# Traces de la course `lift_challenge`

Ce dossier contient ce que les agents ont réellement produit pendant la course, sans retouche. Seuls les chemins de la machine ont été rendus relatifs. Il est généré par `python scripts/export_run.py --run runs/lift_challenge --out course`.

Les cycles 1 à 73 se sont déroulés sur les premières versions de l'épreuve, dont les résultats sont dans `results-exam-v1.jsonl`. Les cycles 74 à 109 correspondent à l'épreuve v3 et à l'atelier ; c'est la course présentée dans le README du dépôt.

## Par où commencer

| Fichier | Contenu |
| --- | --- |
| [`notebook.md`](notebook.md) | Le cahier de labo de l'ingénieur. Une entrée par cycle : hypothèse, essais, résultat, conclusion, suite, sources |
| [`audits.jsonl`](audits.jsonl) | Les audits du vérificateur, cycle par cycle : affirmations contrôlées, preuves, gravité |
| [`field_notes.jsonl`](field_notes.jsonl) | Les notes de terrain de l'éclaireur : problème réel, citation exacte, source horodatée, essai recommandé |
| [`test_requests.jsonl`](test_requests.jsonl), [`inbox.jsonl`](inbox.jsonl) | Les demandes d'essai de l'éclaireur et les messages reçus par l'ingénieur |
| [`reality_reviews.jsonl`](reality_reviews.jsonl) | Les revues de réalisme du meilleur design |
| [`exam_limitations.jsonl`](exam_limitations.jsonl) | Les défauts de l'épreuve signalés par les agents |
| [`catalog.jsonl`](catalog.jsonl) | Les pièces achetées, avec l'URL et l'extrait de la fiche produit |
| [`results.jsonl`](results.jsonl), [`exams/`](exams/) | Chaque vol : charge, masse, énergie, verdict, facteurs limitants |
| [`outbox.jsonl`](outbox.jsonl) | Les messages envoyés sur Discord |
| [`calls.jsonl`](calls.jsonl) | Chaque appel d'outil, en version allégée : outil, cycle, heure, durée, succès, début des arguments |

## Ce que l'agent a dessiné et calculé

- **`workspace/parts/<pièce>/`** : pour chaque pièce sur mesure, le script CAO écrit par l'agent (`part.py`), son matériau et son procédé (`part.json`), le rapport de construction (`build.json`), les calculs par éléments finis (`fem-*.json`), le fichier `part.step`, qu'on peut ouvrir dans n'importe quel logiciel de CAO, et une image.
- **`workspace/assemblies/<assemblage>/assembly.json`** : le squelette du drone décrit par l'agent. **`workspace/designs/`** contient le rapport de compilation : masses calculées, poussée, résonance des bras.
- **`workspace/scripts/`** : les scripts de calcul que l'agent a écrits (dimensionnement, aire frontale, basculement au posé, pertes électriques, sensibilité).

Les vidéos, les maillages, la télémétrie complète et les journaux bruts des modèles ne sont pas inclus, faute de place.
