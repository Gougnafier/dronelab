# Audit du travail de l’agent — épreuve v3 et atelier (nuit du 28 au 29 septembre 2026)

Période : cycles 74 à 109 (28 septembre 18 h 30 → 29 septembre matin), après le passage sur DeepSeek et l’ouverture de l’atelier. Arrêt manuel par le porteur le 29 septembre à 8 h 39 : budget de tokens presque épuisé, et record plafonné depuis le cycle 104, limité par l’énergie de la batterie.
Sources : `runs/lift_challenge/` (cahier, audits, limites signalées, notes de terrain, catalogue, pièces, assemblages, épreuves), compétences du dépôt.

## Verdict

**Le système fonctionne comme prévu : l’ingénieur conçoit de vraies pièces à partir de vraies fiches, vole, se corrige ; le vérificateur, l’éclaireur et le canal de signalement des limites d’épreuve ont réellement joué leur rôle.** Le record simulé est 2,30:1 (125 lb pour 24,6 kg) sur un hexacoptère à hélices décalées ; l’agent lui-même le qualifie de non robuste au réel, preuves à l’appui. Deux points exigent une décision : des compétences ont été modifiées par un auteur non identifié, et la tentation d’optimiser contre les plafonds de l’épreuve subsiste à la marge.

| Domaine | Appréciation |
| --- | --- |
| Démarche d’ingénieur | **Très bonne** : catalogue sourcé, pièces conçues et calculées, montée en charge par paliers, bancs chaleur/altitude/vent, enveloppe de robustesse mesurée |
| Honnêteté sur le réel | **Très bonne** : l’agent chiffre lui-même que son record dépend d’hypothèses de l’épreuve (pertes ohmiques non modélisées) et qu’il échoue en chaleur et en altitude |
| Contrôle par le vérificateur | **Bonne** : relève les masses non lisibles sur les sources, la puissance moteur « 180 s » présentée comme continue, les estimations non sourcées, les conceptions collées aux planchers |
| Remontée des limites de l’épreuve | **Excellente** : 7 signalements, dont un bug réel (maillages non transmis, corrigé en 6 min) et des biais de modèle chiffrés |
| Respect des plafonds | **À surveiller** : moyeu et avionique au plancher de masse (0,2 % de marge), batterie à 25,0 C pour un plafond de 25 C, puissance moteur déclarée via une entrée de catalogue dédiée à l’épreuve |
| Intégrité du laboratoire | **Problème** : deux compétences modifiées hors de nos changements, auteur à identifier |

## 1. Ce que l’agent a produit

- **Trajectoire du record** (score = ratio sur le parcours nominal) : cycle 79 dossier refusé (bug d’outillage) → cycle 80 premier vol, échec au retour à vide → **cycle 81 premier parcours qualifiant, 2,084** → 2,315 (cycle 84) → 2,416 (cycle 88, meilleur score brut) → corrections d’assemblabilité demandées par l’éclaireur et le vérificateur, le record du design en cours tombe à 2,212 (cycle 98) → 2,258 (cycle 102, 122,5 lb) → **2,304 (cycle 104, 125 lb, marge d’énergie 0,32 %)**. Détail au § 5.
- **Conception** : hexacoptère `a2l_hexa_mn1118_stagger`, moteurs T-Motor MN1118, hélices VZ40, variateurs V200A, batterie Tattu Pro 14S 22 Ah (155 Wh/kg), tubes carbone Easy Composites 30 mm (35 mm dans les premières versions), **hélices décalées en hauteur** (idée du porteur, pénalité de 3,1 % par rotor), pièces aluminium conçues par l’agent : supports moteur (37 g), moyeu (versions v1 à v5, allégé à 0,557 kg), train, crochet de charge ; verrouillage des vis documenté.
- **Calcul des pièces** : jusqu’à cinq cas de charge par pièce (poussée, couple, choc, torsion, charge suspendue), facteurs de sécurité 1,79 à 217 ; correction d’un perçage mal placé sur le moyeu (hub v4).
- **Bancs d’essai** : chaleur 38 °C et altitude 1 500 m échouent au-dessus de 115 lb et 112,5 lb respectivement ; vent traversier passé à 117,5 lb. Vitesse de croisière optimale trouvée à 17 m/s.
- **Scripts de l’agent** : dimensionnement, flexion des bras, pertes ohmiques, basculement au posé, aire frontale réelle ; le vérificateur a exigé leur présence et les a retrouvés.

## 2. Ce que le reste du système a fait

- **Vérificateur** (33 audits sur la période) : il a trouvé seul, au cycle 74, la puissance moteur « Max Power (180s) » présentée comme continue (gravité forte), relevé à chaque cycle les masses non lisibles sur les pages citées (moteur, variateur, hélice, carte de distribution, câblage), refusé de valider des prédictions de scripts non éprouvées, signalé les conceptions au plancher. Il a posé un verdict « problème » quand la fiche de réalisme manquait (cycles 62 et 104).
- **Éclaireur** : plusieurs dizaines de notes de terrain sourcées (supports moteur cassés, flexion des bras, oscillations, vent traversier, balancement de charge, capacité réelle des batteries, verrouillage des vis…) et des demandes d’essai que l’ingénieur a traitées (tubes 28 à 35 mm comparés, 30 mm retenu dans la version finale, verrouillage des interfaces, stabilité au posé).
- **Limites de l’épreuve signalées par l’ingénieur** (`exam_limitations.jsonl`) :

| Id | Constat | Évaluation |
| --- | --- | --- |
| lim-001 | Maillages des pièces non transmis à la RTX 5090 | **Bug réel**, corrigé et vérifié le soir même |
| lim-003, lim-004 | Aire frontale calculée sur les sphères englobantes : les bras gonflent la traînée d’un facteur ~7 (1,06 m² contre 0,15 m² projetés) | **Défaut réel de l’épreuve** ; il pénalise le banc vent et l’assiette à vide ; à corriger |
| lim-005 | Paliers batterie excluant les packs semi-solides commerciaux (350 Wh/kg, 10 C) | **Fondé** (source produit) ; choix prudent de l’épreuve à réviser |
| lim-006 | Résistance interne de la batterie non modélisée : pertes 38–60 Wh, supérieures à la marge du record | **Fondé** ; limite déjà connue (tension constante), désormais chiffrée |
| lim-007 | Paliers batterie supposant « plus dense ⇒ moins de C », contredit par les packs UHV 4,45 V (240 Wh/kg à 10 C) | **Fondé** (source produit) |
| lim-008 | La marge de poussée statique n’utilise que la puissance continue alors que l’épreuve vole avec la puissance de pointe | **Incohérence réelle** ; elle a poussé l’agent à déclarer une puissance « 80 % pendant 10 min » comme continue |

## 3. Points de vigilance

1. **Compétences modifiées hors de nos changements** (auteur identifié le 30/09, voir § 5). `skills/engineering-cycle/SKILL.md` et `skills/audit-claims/SKILL.md` contiennent une section « Physical Reality Check » (fiche de réalisme en 10 domaines, obligatoire, contrôlée par le vérificateur) qui n’a pas été écrite dans cette session de développement. Elle est apparue le 28 septembre avant 13 h (premier audit qui la cite : cycle 62). Auteurs possibles : le porteur, l’ingénieur (outils de fichiers et de terminal, compétences liées au dépôt par liens symboliques), ou la maintenance automatique de compétences de Hermes. Le contenu va dans le bon sens et le système l’applique, mais **un agent ne doit pas pouvoir réécrire les consignes de son propre vérificateur**. À identifier et à verrouiller (copies en lecture seule dans les profils, contrôle d’empreinte des compétences par `check_lab.py`, historique Git).
2. **Optimisation contre les planchers et plafonds.** Moyeu et avionique à 0,2 % du minimum de l’épreuve, batterie exactement à 25 C, puissance moteur déclarée par une entrée de catalogue créée pour l’épreuve (« mn1118-kv90-continu-80 »). Chaque cas est relevé par le vérificateur et discuté par l’ingénieur, mais le motif est le même qu’à l’audit du 28 septembre, en plus mesuré.
3. **Record fragile.** La marge d’énergie du record (3,3 Wh) est inférieure aux pertes ohmiques non modélisées ; l’agent le dit. Pour la communication, le chiffre honnête est la plage « 2,26 à 2,30 au nominal, ~2,1 en chaleur ou en altitude ».
4. **Données partiellement sourcées.** Plusieurs masses de composants ne sont pas lisibles sur les pages citées (pages dynamiques, onglets) ; la carte de distribution (0,27 kg) et le câblage (0,735 kg) sont des estimations assumées.
5. **Fichiers écrits par l’agent dans le dépôt.** Des scripts de l’agent ont été cherchés dans `scripts/` ; tout ce que l’agent produit doit rester dans `runs/lift_challenge/workspace/`. À vérifier avant le prochain commit.

## 4. Recommandations

- **Avant toute nouvelle course** : identifier l’auteur des sections « Physical Reality Check » ; les garder si elles viennent du porteur (et les consigner), sinon décider de leur sort ; rendre les compétences non modifiables par les agents.
- **Épreuve v4** (si une nouvelle course est lancée) : aire frontale projetée réelle (lim-003/004) ; résistance interne de batterie ou capacité dépendant du courant (lim-006) ; paliers batterie révisés sur sources (lim-005/007) ; marge de poussée cohérente avec la puissance de pointe (lim-008).
- **Pour la vidéo** : le matériau est suffisant et démonstratif sans nouvelle course : premier refus et bug trouvé par l’agent, premier échec puis premier vol qualifiant, progression du record, pièces conçues, bancs chaleur/altitude, audits et limites signalées. Présenter le record avec sa réserve de robustesse, comme l’agent le fait lui-même.

## 5. Compléments du 30 septembre (questions du porteur)

**Auteur des sections « Physical Reality Check ».** Il s'agit de l'interlocuteur Discord (`dronedesk`), le 28/09 entre 10 h 26 et 10 h 29, à la demande du porteur : « Je ne sais pas si tu dois améliorer le skills pour qu'il soit vraiment prêt » (échange Discord du 28/09, conservé hors du dépôt). Sa session (`~/.hermes/profiles/dronedesk/sessions/request_dump_20260928_095031_…json`) contient le texte ajouté et touche `engineering-cycle` et `audit-claims`. L'origine est donc humaine et légitime, mais le canal n'est pas bon : l'interlocuteur avait alors accès au terminal et aux fichiers du dépôt. Il faut le consigner dans `docs/decisions.md` et retirer à l'interlocuteur tout droit d'écriture sur les compétences.

**Origine des hélices décalées : fuite, pas découverte.** L'idée vient du porteur. Nous l'avons transmise par trois canaux :

- l'épreuve v3 elle-même (règle et pénalité) ;
- le message d'équipe msg-0007 (« Nouveau : des hélices décalées en hauteur… peuvent se recouvrir ») ;
- les compétences : `assembly-design` (« pour rapprocher les rotors : bras plus courts ») et `drone-from-scratch`, dont l'exemple de nom `a2_hexa_stagger` a été repris mot pour mot (`a2_hexa_mn1118_stagger`).

Ce qui revient à l'agent : le choix de l'utiliser au cycle 81 pour réduire l'aire frontale, le dimensionnement, et la correction de Z/D (de 0,108 à 0,152) d'après un seuil de banc d'essai sourcé par l'éclaireur (note-0017). Leçon : une compétence doit décrire les règles et la méthode, jamais une solution ou un nom d'exemple qui en suggère une.

**Pas une course repartie de zéro.** Les cycles 74 à 109 prolongent la course commencée le 28/09 à 01 h 11. Au cycle 74, le catalogue, les pièces et les assemblages étaient vides. En revanche, l'agent disposait encore :

- du cahier des cycles 1 à 73 (résumé fourni à chaque cycle) ;
- de ses scripts de dimensionnement ;
- des messages msg-0001 (le doute du porteur), msg-0003 (l'audit) et msg-0007 et msg-0009 (annonces de l'équipe).

La course propre prévue par `scripts/start_clean_run.sh` n'a pas été lancée. Formulation juste : « course de développement continue ; aucune intervention humaine sur la conception pendant les cycles 74 à 109 ».

**Meilleur score brut et corrections.** Le superviseur garde 2,416 comme meilleur score (cycle 88, `a2e`, puis `a2g`), mais ce drone n'était pas assemblable. Les corrections suivantes ont abaissé le record du design en cours :

| Cycle | Correction | Origine | Record du design en cours |
| --- | --- | --- | --- |
| 87 | Crochet et élingue ajoutés | Éclaireur, msg-0026 | 2,305 |
| 95 | Joint bras-moyeu réellement engagé, vrai largueur | Éclaireur, msg-0038 et msg-0039 | 2,257 |
| 96 | Train d'atterrissage allongé | Éclaireur, msg-0035 | 2,224 |
| 97 | Engagement des tubes dans les supports, fixations | Vérificateur, audit du cycle 95 | 2,215 |
| 98 | Masses oubliées ajoutées (visserie, servo, câbles) | Éclaireur, msg-0042 | 2,212 |

Le record remonte ensuite à 2,304 sur `a2l`. Le graphique « Progression » du tableau de bord marque ces corrections par des barres verticales (`docs/demo/corrections-lift_challenge.json`). Le superviseur devrait lui-même savoir invalider un record ; c'est à prévoir avant toute nouvelle course.

**Catalogue.** Il compte 17 entrées pour 14 pièces distinctes :

- T-Motor : 2 moteurs, 1 hélice, 1 variateur ;
- Tattu : 1 batterie ;
- Easy Composites : 2 tubes ;
- Holybro : 3 éléments d'avionique ;
- un servo ;
- deux références génériques, un tableau de sections de fils (PowerStream) et un tableau de résistance des câbles acier (Engineering Toolbox). Ce ne sont pas des fiches produit.

Comparaisons réellement faites :

| Sujet | Comparaison |
| --- | --- |
| Moteurs | MN1315 contre MN1118, soit hexa contre octo (cycles 74-75) |
| Tubes | 28, 30, 32 et 35 mm par calcul de flexion et éléments finis (cycles 76-77) |
| Batteries | LiPo 155 Wh/kg, Li-ion 21700, UHV 240 Wh/kg, semi-solide ; fournisseurs Amicell, Grepow et MaxAmps cherchés, sans pack standard trouvé (cycles 93 à 106) |
| Hélices, variateurs | Aucune alternative : une seule référence chacun |

**Déformation des bras.** L'agent a calculé la flèche (15 à 49 mm selon le tube), la contrainte à la racine et les modes propres (8 à 16 Hz). L'éclaireur a fait traiter le blocage en rotation des 12 interfaces (msg-0022 et msg-0047 : friction d'une vis unique contre un blocage positif). En revanche, le vol MuJoCo reste en corps rigides : il ne modélise ni l'inclinaison de la poussée due à la flèche, ni le couplage vibratoire, ni la fatigue.

**Recouvrement des hélices.** L'épreuve applique +20 % de puissance multiplié par la fraction de disque recouverte. Pour le design retenu, qui recouvre 23 % du disque, cela donne +4,6 %. Pour un coaxial complet, la théorie de la quantité de mouvement donne plutôt +28 % de puissance induite (facteur d'interférence ≈ 1,28 selon Leishman, *Principles of Helicopter Aerodynamics* ; valeur à vérifier). Si l'on retient ce facteur, la pénalité du design serait d'environ +6,4 %. L'écart de près de 2 % d'énergie dépasse la marge du record (0,32 %) : **le record de 125 lb ne tiendrait probablement pas**, la charge de 120 lb resterait plausible. L'agent avait lui-même signalé cette pénalité comme non validée (cycle 89). À corriger dans une épreuve v4, avec une pénalité calibrée sur des mesures et fonction de Z/D.
