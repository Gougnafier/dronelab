---
name: reality-review
description: Revue de réalisme - confronter la meilleure conception et l'épreuve simulée au monde réel (notes de terrain, sources), dire ce qui est encore trop simple ou irréaliste, et répartir les écarts entre essais, conception et limites de l'épreuve. Charger pour l'éclaireur en mode revue.
version: 1.0.0
category: engineering
---

# Revue de réalisme

Le simulateur n'est pas le monde. Ta question : **si l'on construisait ce drone demain, qu'est-ce qui casserait, chaufferait, vibrerait ou ne volerait pas comme prévu ?**

## Méthode

1. Rassemble : meilleur design (`best_designs`, `check_design`, rapport `designs/<nom>/compile.json` et `view.png`), ses épreuves (`exam_list`, `exam_telemetry` : puissance, température moteurs, inclinaison, batterie), ses composants (`catalog_search`), le cahier de l'ingénieur, les notes de terrain (`field_notes`).
2. Pour chaque domaine (moteurs, variateurs, batterie, hélices, structure, vibrations, aérodynamique, vent, commande, charge suspendue, intégration), compare **ce que la simulation suppose** à **ce que le terrain montre** (note de terrain, source). Exemples de questions :
   - les moteurs tournent-ils près de leur puissance continue pendant des minutes ? leur température simulée est-elle crédible ?
   - la batterie peut-elle vraiment délivrer ce courant sans chute de tension ? (l'épreuve suppose une tension constante)
   - les bras et supports ont-ils un cas de choc ou d'atterrissage dur, pas seulement la poussée ?
   - la fréquence propre des bras (rapport de compilation) est-elle loin des rotations ?
   - a-t-on testé le vent, les rafales, la chaleur (`run_exam` avec `scenario`) ?
   - des pièces manquent-elles (fixations, connecteurs, protection de la batterie) ?
3. Classe chaque écart :
   - **essai** : un banc existant répond à la question → l'ingénieur doit le faire (`request_test` avec protocole) ;
   - **conception** : le design doit changer (pièce à renforcer, composant à changer) ;
   - **épreuve** : la simulation elle-même ignore le phénomène (ex. chute de tension batterie, interaction aérodynamique) → transmis à l'équipe, seule habilitée à modifier l'épreuve.

## Verdict (`record_reality_review`)

- **réaliste** : rien d'important ne manque au regard des preuves disponibles ;
- **à renforcer** : des essais ou des corrections sont nécessaires avant d'y croire ;
- **irréaliste** : le design ne tiendrait pas dans le réel (preuve à l'appui).

Chaque écart porte une preuve (URL, note de terrain, télémétrie). Pas de critique vague : « trop simple » doit dire ce qui manque et comment le vérifier.
