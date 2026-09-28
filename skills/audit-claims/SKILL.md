---
name: audit-claims
description: Vérifier le travail d'un ingénieur autonome - confronter chaque affirmation de son cahier de labo aux preuves (appels d'outils, résultats d'épreuve, télémétrie, sources). Charger pour chaque session de vérification.
version: 1.0.0
category: engineering
---

# Auditer un cycle

Tu es indépendant de l'ingénieur. Ton travail n'est pas de refaire sa conception mais de dire si ce qu'il affirme est **vrai et justifié par des preuves**.

## Méthode

1. `cycle_evidence(cycle)` : cahier du cycle, appels d'outils réels et leurs résultats, épreuves.
2. Relève chaque affirmation vérifiable de l'entrée du cahier : chiffres (masse, ratio, énergie, poussée), verdicts (« réussi », « échec pour cause de … »), causalités (« la batterie est le facteur limitant »), sources citées.
3. Pour chacune, cherche la preuve :
   - chiffre ou verdict d'épreuve → résultat de `run_exam` ou `exam_telemetry` (relis la télémétrie autour de l'événement si besoin) ;
   - causalité → la télémétrie la montre-t-elle (batterie à 0, poussée à 100 %, écart qui diverge) ?
   - source web → l'URL existe-t-elle et contient-elle la valeur ? (outil web si disponible) ;
   - fichier de conception → lis-le si l'affirmation porte sur son contenu.
4. Classe : **confirmée**, **non vérifiable** (pas de preuve, sans être fausse), **contredite** (la preuve dit autre chose).

## Réalisme d'ingénierie (à faire à chaque cycle où un nouveau dossier de conception a été testé)

Un chiffre peut être exact dans l'épreuve et faux dans le monde réel. Pour le ou les dossiers testés dans le cycle :

1. Lance `check_design` : lis `near_limits` (déclarations à moins de 2 % d'un plafond), `masses_by_family_kg` face à `minimum_masses_kg`, `arms`, `max_payload_for_thrust_margin_kg`.
2. Lis `design.json` (outil de fichiers) : chaque composant a-t-il une masse tirée d'une source précise (fiche produit, pas une page d'accueil) ? Une note du type « at limit », « pour respecter le plafond », une masse ronde sans source, sont des signaux d'**optimisation contre l'épreuve**.
3. Pièces oubliées ou irréalistes pour un vrai appareil de cette puissance (variateurs, câblage, train, fixations) : signale-les même si l'épreuve les accepte.
4. Sources : ouvre les URL citées (outil web) ; une page introuvable ou qui ne contient pas la valeur est une affirmation **contredite**.
5. Suivi : l'ingénieur doit répondre à tes points précédents (`audit_response` dans son entrée). S'il ne les a pas traités ou les écarte sans preuve, signale-le.

Une conception qui ne tient qu'en se collant aux plafonds de l'épreuve mérite au moins « réserves » ; si elle repose sur une source morte ou une masse inventée, « problème ».

## Catalogue, pièces et assemblage (produit lift_challenge)

- `catalog_search` : pour chaque pièce ajoutée pendant le cycle, ouvre `source_url` et vérifie que l'extrait et les valeurs y figurent (`excerpt_numbers_found_on_page` est un indice, pas une preuve). Puissance crête présentée comme continue, énergie cellule présentée comme pack : contredit.
- Pièces sur mesure (fichiers `workspace/parts/<nom>/`) : les cas de charge couvrent-ils les efforts réels (poussée max du rotor, atterrissage) ? Une zone chargée minuscule ou un effort sous-estimé pour passer le calcul est un problème.
- Assemblage : lis `designs/<nom>/compile.json` et regarde `view.png` (vision) ; pièces manquantes, bras non reliés, hélices en contact.

## Verdict

- `ok` : tout ce qui compte est confirmé.
- `réserves` : affirmations non vérifiables ou imprécisions mineures.
- `problème` : au moins une affirmation importante contredite (chiffre inventé, épreuve déclarée réussie à tort, source qui ne dit pas ce qui est cité) ou un résultat présenté sans épreuve.

`record_audit(cycle, verdict, summary, issues)` : résumé en 3 phrases maximum, puis une entrée par problème avec l'affirmation, la preuve et la gravité. Sois précis et factuel ; ne sanctionne pas un désaccord de méthode, seulement ce qui est faux ou non prouvé.

## Contrôle « Physical Reality Check » (NOUVEAU)

En plus des affirmations chiffrées, le vérificateur DOIT contrôler que l'ingénieur a produit une fiche `reality_check` dans son entrée de cahier pour le design candidat, et que :

1. **La fiche existe** (section `## Reality Check — ...` présente)
2. **Tous les 10 domaines** de la checklist sont au minimum mentionnés (même avec « non fait »)
3. **Chaque verdict « OK » est sourcé** : une URL, une fiche constructeur, un calcul d'ordre de grandeur explicite — pas une supposition
4. **Aucun domaine « Bloquant » n'est ignoré** : si un domaine est Bloquant, le design ne doit pas être soumis à l'épreuve sans correction ou abandon explicite
5. **La synthèse finale** (FAISABLE / À RISQUE / NON FAISABLE) est cohérente avec les verdicts par domaine

Si la fiche manque, est incomplète, ou contient des verdicts « OK » non sourcés → verdict `problème` avec issue « Physical Reality Check absent / incomplet / non sourcé ».
