# Décisions

## 27 septembre 2026 — Nouveau départ

**Demande du porteur :** repartir dans une nouvelle direction, car les pistes précédentes ne correspondent pas à ce qu’il souhaite construire.

**Décision :** créer un dépôt Git local vierge pour le même challenge. Il contient seulement le cadre, les consignes et le suivi. Le problème, le public, la stack et le nom public du projet restent ouverts.

**Raison :** permettre un nouveau choix sans hériter implicitement de l’architecture, des modèles, des dépendances ou des conclusions des dépôts 3D et radio.

**Conservation :** les dépôts voisins restent séparés et intacts. Aucun dépôt distant n’est créé et aucune ressource externe n’est publiée.

## 27 septembre 2026 — Direction : agent ingénieur drone

**Demande du porteur :** « lire et démarrer » le cahier des charges initial de l’agent ingénieur drone (archivé hors du dépôt).

**Décision :** la direction du dépôt est un agent qui allège en continu un châssis de quadricoptère imprimable en 3D (bras, puis plaques), en choisissant lui-même ses essais, sous contraintes de résistance, de flèche, de fréquence propre et de fabricabilité. Plan B consigné dans le cahier : aile à voilure fixe avec AeroSandbox.

**Raison :** tâche réelle, longue et mesurable (masse, facteurs de sécurité, fréquences) ; la progression dans le temps se voit dans `runs/results.jsonl` et le cahier de labo.

**Adaptations au cadre du dépôt :**

- Structure : le code va dans `src/drone_agent/` (`cad/`, `fem/`, `tools/`, puis `agent/`), les tests dans `tests/`, les commandes dans `scripts/` (`scripts/evaluate.py` remplace `evaluate.py` à la racine). La spec machine est `spec/cahier_des_charges.yaml`. `runs/` est hors Git.
- Journaux : `runs/results.jsonl` contient une ligne par **évaluation** (format du cahier) ; chaque **appel d’outil** va dans `runs/calls.jsonl`, pour que le tableau de bord lise un seul format par fichier.

## 27 septembre 2026 — Géométrie Gmsh/OpenCASCADE et CalculiX pilotés directement

**Décision :** le bras est construit avec le noyau OpenCASCADE de Gmsh (export STEP et STL, maillage C3D10 dans le même outil) et le fichier CalculiX est écrit par notre code. FreeCAD et son atelier FEM ne sont pas utilisés à ce stade.

**Raison :** le cahier fixe comme risque principal la fiabilité de FreeCAD FEM (point de décision lundi soir). Cette chaîne évite ce risque tout en gardant CalculiX et Gmsh prévus par la stack, avec moins de dépendances (environnement conda-forge `environment.yml`). Elle est validée contre la théorie des poutres (compte rendu K02, archivé hors du dépôt). FreeCAD reste possible plus tard pour des pièces que Gmsh construirait mal.

**Hypothèses de modélisation :** matériau isotrope et prudent (valeurs indicatives de pièces imprimées), pièce pleine, bras encastré sur toute la zone de serrage, moteur rigide sur son empreinte Ø 28 mm, masse moteur de 60 g en bout de bras pour le modal, contrainte max hors d’une bande de 3 mm à l’encastrement (singularité).

## 27 septembre 2026 — Calculs sur la RTX 5090 par SSH

**Demande du porteur :** passer par SSH sur la machine RTX 5090.

**Décision :** les calculs longs tournent dans WSL2 sur cette machine (Ryzen 9 9950X3D, 32 fils, 70 Gio), dans un environnement micromamba isolé `~/drone-agent/env` ; le code y est copié par flux `tar` sur SSH dans `~/drone-agent/repo`. L’alias SSH est dans `data/local/ssh_config`, hors Git. CalculiX calcule sur CPU : le GPU reste libre.

## 27 septembre 2026 (soir) — Agent d’ingénierie produit, démonstration « DARPA Lift »

**Demande du porteur :** un agent d’ingénierie généraliste (optimisation de produit), démontré sur la conception d’un multirotor lourd inspiré du [DARPA Lift Challenge](https://www.darpa.mil/research/challenges/lift) ; retours à l’utilisateur par Discord, rapports planifiés avec graphiques, images et vidéo ; démarrer immédiatement. Détails dans le brainstorming du 27 septembre (archivé hors du dépôt).

**Décision :**

- Démonstration principale : dimensionner un multirotor (rotors, moteurs, batterie, bras) qui maximise *charge max / masse de l’aéronef* sur l’épreuve DLC-1 (< 55 lb, ≥ 110 lb, 4 nmi chargé + 1 nmi à vide à 150 ft), DLC-2 en variante. On ne s’inscrit pas (compétition réservée aux entités américaines) ; l’épreuve sert de banc d’essai.
- Évaluation rapide par modèle physique maison (théorie de la quantité de mouvement, énergie de mission, marges, bras en tube carbone analytique). CalculiX (K02) sert à vérifier la structure des records.
- Composants : d’abord des lois d’échelle déclarées comme hypothèses, puis une base de composants réels construite par l’agent avec provenance et contrôles. Pas de fichiers 3D des fabricants.
- Visualisation : export OpenUSD des assemblages ; Omniverse / Isaac Sim hors périmètre avant la soumission.
- Utilisateur : canal Discord via la passerelle Hermes ; rapports planifiés deux fois par jour ; l’agent ne bloque jamais sur une réponse et demande validation avant de modifier une contrainte.
- Le bras imprimé 7 pouces (K02) reste un paquet validé et le plan B.

**Remplace :** la démonstration « châssis 7 pouces allégé » comme cas principal. Le cahier des charges initial reste la référence pour les principes (outils JSON, cahier de labo, anti-plateau, garde-fous).

## 28 septembre 2026 — Architecture de l’agent autonome

**Rappel du porteur :** l’objectif est un agent qui travaille seul ; Claude construit l’agent et vérifie ses outils, sans faire le travail d’ingénierie à sa place.

**Décision :**

- **Superviseur Python** (`src/drone_agent/agent/supervisor.py`) : boucle codée en dur, état sur disque, un cycle = un contexte neuf (résumé du cahier, 5 meilleurs designs, dernière entrée, consignes en attente), détecteur de plateau (1 % sur 15 cycles → rétrospective imposée), résumé tous les 10 cycles, cycle raté sans entrée de cahier, alerte après 3 échecs, quota de cycles par jour, arrêt par fichier `STOP`, rapports à 8 h et 20 h.
- **Hermes, profil dédié `dronelab`** : cloné du profil par défaut, sans passerelle démarrée pour ne pas concurrencer le bot Discord personnel. Modèle `nvidia/nemotron-3-ultra-550b-a55b` via build.nvidia.com. Lancé en mode non interactif (`dronelab chat -q … -Q`) à chaque cycle, avec les compétences du dépôt (`skills/`, liées dans le profil).
- **Serveur MCP du dépôt** (`src/drone_agent/agent/mcp_server.py`), deux rôles : *engineer* (brief, évaluations, exploration, réglage fin, sensibilité, cahier, dialogue, propositions de modèle) et *desk* (état, consignes, validation des propositions). L’ingénieur ne peut pas valider ses propres propositions.
- **Produits** (`src/drone_agent/products.py`) : le noyau est générique ; `heavylift` et `printed_arm` sont les deux premiers.
- **Notifications** : `hermes send` vers Discord (record qualifiant, blocage, question, proposition, rapport), toujours journalisées dans `outbox.jsonl`.

**Raison :** garder ce qui doit être garanti (plateau, budget, reprise, traçabilité) hors du LLM, et laisser au LLM la démarche d’ingénieur.

## 28 septembre 2026 (nuit) — Rapports rédigés par l’agent, calcul sur la 5090, canal Discord

**Demandes du porteur :** les rapports ne doivent pas être du code propre à un produit ; Hermes tourne sur la machine de développement et utilise la RTX 5090 par SSH ; second bot « drone lab » et salon dédié ; preuve de concept, pas de fonctionnement de trois jours exigé.

**Décision :**

- **Rapports** : le superviseur ouvre une session de rapport ; l’agent la rédige avec la compétence `progress-report` et des outils génériques (`result_fields`, `plot_results` sur n’importe quel champ numérique, `plot_progress`, `send_report`). Le module `report.py` ne garde qu’un rapport de secours générique, envoyé seulement si la session échoue.
- **RTX 5090** : outil `verify_arm_fem` (modèle coque Gmsh + CalculiX, exécuté sur la 5090 par SSH, repli local) pour vérifier les bras des designs prometteurs contre le modèle analytique. Code synchronisé par `scripts/sync_5090.sh`.
- **Discord** : salon `#drone-lab` créé sur le serveur du porteur (identifiant dans `data/local/notify_target`, hors Git). Profil Hermes `dronedesk` préparé pour la passerelle du futur bot « Drone Lab » (serveur MCP *desk* seulement) ; en attendant, les notifications partent par le bot existant via `hermes send`.
- **Personnalités** : `hermes/dronelab.SOUL.md` et `hermes/dronedesk.SOUL.md`, liées dans les profils.
- **Exécution** : service utilisateur systemd `dronelab-agent` (redémarrage automatique en cas d’échec).

**Complément (28 septembre, 0 h 40) — bot existant :** à la demande du porteur, pas de second bot. Le bot Discord existant (inutilisé) est rattaché au profil `dronedesk` : passerelle du profil par défaut arrêtée et désactivée (`systemctl --user enable --now hermes-gateway` pour la rétablir ; aucune tâche planifiée n’en dépendait), passerelle `dronedesk` installée en service, limitée au salon `#drone-lab` et sans mention obligatoire. Les notifications de l’ingénieur (`hermes send`) passent par le même bot.

## 28 septembre 2026 (nuit) — Conception de zéro, épreuve simulée MuJoCo, vérificateur indépendant

**Demandes du porteur :** issues du brainstorming du 27 septembre (archivé hors du dépôt).

**Décision :**

- **Nouveau produit `lift_challenge`**, espace de travail vide (`runs/lift_challenge/workspace/`). L’agent y écrit ses scripts, ses calculs et ses dossiers de conception (`drone.xml` MuJoCo + `design.json`) avec les outils de fichiers, de terminal et de recherche web de Hermes.
- **Épreuve simulée** (`src/drone_agent/lift/exam.py`, `spec/lift_exam.yaml`) : MuJoCo 3.14 (Apache-2.0), parcours DLC-1 complet, charge en disques soudée puis larguée, pilote automatique et physique fixés par l’épreuve (poussée et puissance par la théorie de la quantité de mouvement, batterie, traînée), garde-fous de plausibilité sur les déclarations. Exécutée sur la RTX 5090 par SSH ; renvoie un résumé, la télémétrie à 10 Hz (pour l’agent) et la trajectoire. La vidéo est produite sur la machine de développement en rejouant exactement cette trajectoire (EGL, le rendu WSL de la 5090 échoue).
- **Vérificateur indépendant** : profil Hermes `dronecheck`, autre modèle (`deepseek-ai/deepseek-v4-flash`), sans terminal ni exécution de code. Lancé en parallèle après chaque cycle réussi ; confronte le cahier aux appels d’outils, résultats et télémétrie (`cycle_evidence`) et enregistre un verdict (`record_audit`). Ses derniers audits sont placés en tête du prompt de l’ingénieur ; un problème grave est signalé sur Discord.
- **Outils Hermes de l’ingénieur** : désactivés pour l’autonomie et la sûreté : contrôle de l’ordinateur, génération d’images, synthèse vocale, questions bloquantes, tâches planifiées, mémoire persistante (le cahier reste la seule mémoire).
- Les produits `heavylift` (modèle analytique) et `printed_arm` restent disponibles mais ne sont plus la démonstration.

## 28 septembre 2026 (midi) — Épreuve v2 et corrections après l’audit

**Contexte :** [audit du travail de l’agent](validation/audit-agent-2026-09-28.md). Le porteur a demandé d’appliquer toutes les recommandations.

**Décision :**

- **Épreuve v2** (`spec/lift_exam.yaml`, `version: 2`) : non-chevauchement des hélices (coaxial permis, +20 % de puissance), masses minimales par famille de pièces (variateurs, hélices, câblage, avionique, train, moyeu), batterie par paliers (≤ 200 Wh/kg jusqu’à 25 C, ≤ 260 Wh/kg jusqu’à 6 C), flexion des bras (tube déclaré, 400 MPa / 1,5), poussée max ≥ 1,6 × poids chargé, signalement des déclarations collées aux plafonds (`near_limits`). Les 16 conceptions de l’agent sont refusées (détail archivé hors du dépôt) ; les résultats v1 sont archivés (`results-exam-v1.jsonl`), le cahier et l’espace de travail sont conservés.
- **Vérificateur** : mandat élargi au réalisme d’ingénierie (compétence `audit-claims`) : `near_limits`, masses par famille, sources des composants, suivi des réponses de l’ingénieur.
- **Boucle d’audit fermée** : `notebook_write` refuse l’entrée tant que l’ingénieur n’a pas répondu point par point (`audit_response`) au dernier audit comportant des points.
- **Superviseur** : un refus HTTP 429 n’est plus un échec de cycle (numéro rendu, attente de 2 min doublée jusqu’à 30 min, une alerte après 6 refus) ; vérificateur et ingénieur ne sollicitent plus l’API en même temps ; une seule alerte par épisode de blocage puis un avis de reprise ; le détecteur de plateau ignore les cycles en échec.
- **Épreuve** : la réponse indique la charge demandée et la charge appliquée (pas de 2,5 lb) et la raison d’un refus.

## 28 septembre 2026 (après-midi) — Atelier de conception et épreuve v3

**Demande du porteur :** éviter que l’agent ne fasse que du réglage d’hyperparamètres ; lui permettre de composer un squelette de drone, d’instancier des pièces achetées (tubes carbone…) et de concevoir ses propres pièces (supports moteur imprimés ou usinés en aluminium, choix selon la thermique), d’essayer des hélices décalées en hauteur ; tout en place le soir même.

**Décision :** nous fournissons la grammaire (catalogue, atelier, règles d’interfaces, compilateur, épreuve), l’agent écrit le squelette et les pièces.

- **Catalogue** (`src/drone_agent/lift/catalog.py`) : pièces achetées par catégorie, spécifications obligatoires, page source ouverte par l’outil (404 et page d’accueil refusées), plausibilité (puissance continue, paliers batterie, masses minimales).
- **Atelier de pièces** (`parts.py`, `partfem.py`, `spec/materials.yaml`) : CAO par script Gmsh/OpenCASCADE (mm), matériaux PETG, PLA-CF, PA12-CF, AL6061-T6, AL7075-T6 et procédés FDM/CNC (volume, paroi minimale, abattement de résistance), masse et inertie calculées, estimation thermique par modèle d’ailette, rendu, calcul par éléments finis de chaque cas de charge sur la RTX 5090 (facteur de sécurité ≥ 1,5 exigé).
- **Assemblage** (`assembly.py`) : `assembly.json` écrit par l’agent (instances catalogue et sur mesure, tubes par extrémités, rotors, connexions) → modèle MuJoCo avec masses calculées, dossier d’épreuve signé, OpenUSD, image ; contrôle des interfaces (diamètre tube/manchon, motif de vis moteur), des pièces calculées et à jour.
- **Épreuve v3** : seuls les dossiers compilés sont acceptés ; hélices décalées en hauteur (≥ 10 % du diamètre) permises avec +20 % de puissance × fraction de disque recouverte ; règles v2 conservées.
- **Compétences** : nouvelles `part-design` et `assembly-design` ; `drone-from-scratch`, `lift-exam`, `component-research`, `audit-claims` mises à jour.
- Les conceptions v1/v2 de l’agent (écrites à la main) sont refusées par la v3 ; son cahier et ses scripts restent.

## 28 septembre 2026 (soir) — Modèles : OpenAI pour l’ingénieur, NVIDIA pour le vérificateur

**Constat :** avec les modèles de build.nvidia.com (quota gratuit partagé par l’ingénieur et le vérificateur), la majorité des cycles échouaient sur des refus HTTP 429. Le porteur pensait Hermes connecté à OpenAI : c’est le cas pour son profil par défaut (`gpt-5.6-sol`, compte ChatGPT, fournisseur `openai-codex`), pas pour les profils du projet, qui avaient été volontairement mis sur NVIDIA.

**Décision :**

- Ingénieur (`dronelab`) et interlocuteur Discord (`dronedesk`) sur OpenAI, avec une connexion propre à chaque profil (`<profil> auth add openai-codex --type oauth`), pour ne pas partager les jetons du profil personnel. Bascule par `scripts/use_openai.sh`.
- Vérificateur (`dronecheck`) sur `deepseek-ai/deepseek-v4-flash` (NVIDIA) : famille de modèle différente de l’ingénieur, donc vérification plus indépendante ; une seule session par cycle, compatible avec le quota ; un modèle NVIDIA reste dans la boucle.
- Réessais d’API portés à 10 dans les trois profils ; un cycle est réussi dès que l’entrée de cahier est écrite ; les changements de cadre (épreuves v2 et v3) sont rappelés en tête de chaque prompt.

**Mise à jour (même soir) :** le porteur préfère sa clé API DeepSeek à une connexion OpenAI. `scripts/use_deepseek.sh` (clé saisie masquée, écrite seulement dans le `.env` des profils `dronelab` et `dronedesk`) passe l’ingénieur sur `deepseek-v4-pro` et le bot Discord sur `deepseek-v4-flash` via l’API DeepSeek directe, et le vérificateur sur `nvidia/nemotron-3-ultra-550b-a55b` pour rester d’une autre famille que l’ingénieur. L’API DeepSeek est payante à l’usage : garder un quota de cycles par jour raisonnable. Les crédits Lambda proposés par NVIDIA (calcul GPU dans le cloud, carte bancaire requise) ne sont pas nécessaires : le calcul se fait sur la RTX 5090, le goulot est l’API des modèles.

## 28 septembre 2026 (soir) — Éclaireur, veille YouTube et bancs d’essai

**Demande du porteur :** un profil qui fait des recherches sur les drones (retours d’expérience, YouTube, blogs, problèmes rencontrés), qui transmet à l’ingénieur des essais variés (thermiques, fluidiques…), et qui ramène le travail au réel : critiquer ce qui est trop simple face au terrain.

**Décision :**

- **Profil `dronescout` (éclaireur)**, `deepseek-v4-flash` (clé DeepSeek), sans terminal ni exécution de code. Deux modes, lancés par le superviseur tous les 3 cycles réussis, en alternance, jamais en même temps que l’ingénieur : **veille** (compétence `field-research`) et **revue de réalisme** (compétence `reality-review`).
- **Outils YouTube gratuits** (`src/drone_agent/research/youtube.py`) : recherche par yt-dlp (licence Unlicense, sans clé), transcription par sous-titres (youtube-transcript-api, MIT) puis, à défaut, transcription locale faster-whisper (MIT, modèle Whisper « small », GPU). Transcriptions gardées hors Git dans `runs/…/research/`, citées par extraits horodatés.
- **Base de terrain** : `field_note_add` / `field_notes` (problème, preuve citée, conséquence, essai recommandé, gravité) ; `request_test` dépose une demande d’essai dans la boîte de l’ingénieur, qui doit y répondre ; `record_reality_review` classe les écarts en essai, conception ou **limite de l’épreuve** (transmise à l’équipe sur Discord, seule habilitée à modifier l’épreuve). La dernière revue apparaît en tête du prompt de l’ingénieur.
- **Bancs d’essai** : `run_exam(..., scenario=…)` : `vent`, `rafales`, `chaleur`, `altitude` (hors score) ; modèle d’échauffement des moteurs à chaque vol (pertes, puissance continue, puissance de pointe optionnelle, échec au-delà de 150 °C) ; analyse de résonance des bras (fréquence propre face aux bandes 1P et 2P) dans le rapport de compilation.
- Vérification : 40 tests, et une session réelle de l’éclaireur a consigné une première note sourcée (supports moteur en contreplaqué cassés sur un drone de 100 kg, vidéo horodatée).

## 30 septembre 2026 — Soumission : dépôt GitHub présentable et vidéo courte

**Contexte :** d'après le formulaire, on peut soumettre soit une vidéo (3 min maximum, 30 à 90 s de préférence, sur YouTube ou Loom), soit un lien vers le projet.

- **README en français, tourné vers le jury.** Il présente le résultat, les quatre profils Hermes et leur personnalité, quatre schémas Mermaid (principe, architecture, cycle, atelier), le graphique de progression avec ses corrections, les pièces conçues, les limites et les licences des logiciels tiers.
- **Médias dans `docs/media/`** (2,4 Mo) : une animation GIF de 10 s du vol exam-0188, les rendus des pièces et de l'assemblage final, le graphique de progression. Ce sont des copies choisies ; `runs/` reste hors Git.
- **Recommandation :** mettre la vidéo dans le champ du formulaire, et le lien GitHub dans la description. Le lien vers la vidéo ne sera ajouté au README qu’une fois la vidéo en ligne.
- **Schémas noir sur fond blanc** (demande du porteur) : GitHub dessine le Mermaid intégré selon le thème du lecteur, donc sombre en mode sombre. Les sources restent dans `docs/diagrams/*.mmd` ; `scripts/render_diagrams.sh` les rend en SVG à fond blanc, avec du texte SVG simple, via @mermaid-js/mermaid-cli 11.17 (licence MIT, installé hors du dépôt). Le README affiche ces images.
- La mise en ligne du dépôt et de la vidéo relève du porteur.

## 30 septembre 2026 (soir) — Nettoyage du dépôt avant publication

- **Présentation sans noms de modèles.** Le README, les diapositives et la description du formulaire ne citent plus les modèles utilisés. La cible du projet est un modèle plus petit, exécuté en local ; aucun texte ne prétend pour autant que la course a tourné en local. Les décisions historiques gardent leurs faits.
- **Qui a fait quoi, mis en avant.** Nous avons configuré Hermes (profils, règles, boucle Python, outils scientifiques, épreuve, Discord). Les agents ont fait toute l'ingénierie du drone.
- **Traces de la course publiées** dans `course/` (11 Mo) par `scripts/export_run.py`. Chemins de la machine retirés, journal des appels allégé, journaux bruts des modèles, maillages et vidéos exclus.
- **Archivés hors du dépôt** (`data/local/archives/`, ignoré) : brainstorming, cahier des charges initial (bras 7 pouces), cadre du challenge, méthode de travail (reprise dans `AGENTS.md`), comptes rendus K02 et K04, contrôle v2 des anciens designs, échange Discord privé, scripts du plan B (`evaluate.py`, `random_designs.py`) et `use_openai.sh`. Les documents de travail pour la vidéo et le formulaire sont dans `data/local/demo/`.
- **Compétences neutralisées** : plus d'exemple de nom `a2_hexa_stagger` ni d'avantage suggéré des hélices décalées ; la règle reste décrite dans `lift-exam`.
- **Code conservé** : les produits `heavylift` et `printed_arm` partagent des modules avec l'atelier (éléments finis, outils) et sont couverts par les tests. Produit par défaut des scripts : `lift_challenge`.
