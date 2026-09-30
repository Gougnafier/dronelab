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

## Pièges (rencontrés au cycle 91)

- **Un chiffre de modèle suspect se démontre, il ne s'affirme pas.** Avant de qualifier un écart d'artefact, relire le code de l'épreuve (`src/drone_agent/lift/exam.py`) et reconstruire le chiffre à la main depuis la géométrie compilée (`designs/<nom>/drone.xml`, `assemblies/<nom>/assembly.json`). Exemple traité : l'aire frontale est la boîte des sphères englobantes (`exam.py:490-499`) ; `geom_rbound` d'un bras tubulaire vaut L/2 + r, donc un tube Ø30 de 0,68 m « occupe » ±0,355 m — l'inflation se lit dans le champ `frontal_area_m2` du `summary.json` face aux cotes réelles des geoms. Citer les champs publiés par l'épreuve (`frontal_area_m2`, `span_m`, `max_tilt_deg`) rend le chiffre vérifiable par l'ingénieur.
- **Ne pas confondre effet sur l'assiette et effet sur l'énergie.** Une traînée surestimée ne coûte pas `D·v` au pack : `_power` (`exam.py:709-722`) ne facture que la puissance induite ; la traînée n'entre que par l'inclinaison (T ≈ mg/cos θ) et le terme (1/FM − κ)·T·vh. Sur ce design, gonfler le cda de 4-5× fait passer l'assiette à vide de ~8° à 32,6° mais ne change l'énergie de mission que de quelques pour cent : l'annoncer comme « 244 Wh d'écart » serait faux. Recalculer la puissance de croisière avec la formule de l'épreuve avant de conclure.
- **Séparer « plafond du pilote » et « propriété de la machine ».** Un plafond codé en dur dans l'autopilote de l'épreuve (35° d'assiette, `exam.py:551`) n'est pas une limite physique : en exploitation c'est un réglage (ArduPilot ATC_ANGLE_MAX, plage 10-80° ; PX4 MPC_TILTMAX_AIR). Le signaler à l'équipe d'épreuve, et vérifier que l'ingénieur ne paie pas de masse pour respecter un réglage qui lui échappe.
- **Contrôler les éléments déclarés sous le plan de posé.** Comparer les z de tous les geoms et instances (`battery`, `payload_attach`, élingue, pieds du train, plans d'hélices) : l'épreuve translate tout le modèle pour dégager la plus grosse sphère englobante à 2 cm du sol (`exam.py:463-465`), ce qui masque un pack ou un crochet qui pendrait sous le train.
- **Deux domaines que la liste ci-dessus oublie, et que l'épreuve ne peut pas voir.** (a) La **masse au pesage** : `check_design` donne `aircraft_mass_kg` et `masses_by_family_kg` — comparer au plafond (24,94 kg = 55 lb) et inventorier ce qui est *déclaré mais à 0 g* (interfaces `servo`/`manual_pull` des part.json sans masse, actionneur, visserie, fiche dont la masse est « estimée »). Cas a2j : marge 0,368 kg contre 0,31–0,47 kg d'incertitudes documentées — le dépassement vaut « hors règlement ». (b) La **stabilité au posé** : relever les pieds dans `assembly.json`, reconstruire le centre de gravité compilé (Σ m_i·z_i sur les instances — le pack domine), puis l'angle de basculement atan(demi-base / hauteur_cg). Cas a2j : base 0,185 m (pieds à ±92,6 mm), cg à 0,283 m → 21°, alors que le train n'a été dimensionné que pour la garde au sol ; l'épreuve n'a aucun contact sol et atterrit à assiette nulle, donc un renversement y est invisible (3 retournements sur 4 au décollage-posé d'un grand multirotor carbone, note-0021).
- **Charge soudée, pas suspendue.** Lire comment la charge est tenue dans `build_model_xml`/`run_exam` : ici une `equality weld` posée 2 cm sous `payload_attach` (`exam.py:127` et `458`), libérée d'un coup (`exam.py:537`). Aucun balancement, aucune charge latérale sur l'élingue pendant les 4 nmi à 17 m/s ; comparer la fréquence du pendule réel ((1/2π)√(g/L), L = mors→accroche) à la bande du contrôle d'assiette (`exam.py:560`, wn ≈ 1,2 Hz) et à la pratique (anti-swing DJI, note-0006).

## Verdict (`record_reality_review`)

- **réaliste** : rien d'important ne manque au regard des preuves disponibles ;
- **à renforcer** : des essais ou des corrections sont nécessaires avant d'y croire ;
- **irréaliste** : le design ne tiendrait pas dans le réel (preuve à l'appui).

Chaque écart porte une preuve (URL, note de terrain, télémétrie). Pas de critique vague : « trop simple » doit dire ce qui manque et comment le vérifier.
