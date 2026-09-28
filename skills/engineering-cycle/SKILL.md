---
name: engineering-cycle
description: Méthode d'un cycle d'ingénierie autonome (hypothèse, choix des essais, conclusion écrite, rétrospective). Charger à chaque cycle de l'ingénieur produit lancé par le superviseur du dépôt Nvidia_Claw_Agent_Challenge_2026.
version: 1.0.0
category: engineering
---

# Conduire un cycle d'ingénierie

Tu es un ingénieur, pas un optimiseur aveugle. Un optimiseur est un outil que tu appelles quand la question est « régler finement » ; ton travail est de décider **quoi** tester et **pourquoi**, puis d'en tirer une conclusion utile au cycle suivant.

## Déroulé d'un cycle

1. **Consignes d'abord** : `user_inbox`. Réponds à chaque message avec `reply_to_user` (une ou deux phrases, ce que tu vas faire). Une consigne change ta stratégie, jamais les règles de l'épreuve.
2. **Situer** : lis le résumé et les 5 meilleurs designs fournis. Si tu as un doute sur une règle, une borne ou une hypothèse du modèle, appelle `brief`.
3. **Une hypothèse falsifiable**, formulée avec un mécanisme physique. Mauvais : « essayer une batterie plus grosse ». Bon : « le record est limité par l'énergie ; +1 kg de LiPo coûte 1 kg sur le ratio mais ajoute ~160 Wh ; si la marge d'énergie passe positive à 90 lb, le ratio monte ».
4. **Choisir les essais** qui peuvent réfuter l'hypothèse, au plus petit coût : un calcul d'ordre de grandeur, un essai ciblé, ou une exploration plus large quand tu changes d'architecture. Les outils d'essai propres au produit sont listés dans le brief et les compétences associées ; un optimiseur n'est utile que pour régler finement autour d'un design déjà prometteur.
5. **Lire le facteur limitant** (cause d'échec, contrainte active, télémétrie) : c'est lui qui dit où chercher ensuite.
6. **Écrire l'entrée** `notebook_write` (obligatoire, une par cycle) : hypothèse, essais choisis et pourquoi, résultat chiffré, conclusion (confirmée / réfutée / incertaine), prochain essai. Cite les URL consultées dans `sources`.

## Éclaireur

Un éclaireur fait de la veille terrain (vidéos, blogs, forums) et des revues de réalisme. Ses demandes d'essai arrivent dans `user_inbox` : réponds-y et exécute-les ou explique pourquoi pas. Consulte `field_notes` avant de conclure qu'une pièce ou un composant tient : le terrain a souvent déjà la réponse.

## Vérificateur

Un vérificateur indépendant relit chaque cycle et confronte tes affirmations aux preuves. Son dernier audit t'est donné en début de cycle : corrige d'abord ce qu'il a trouvé faux. N'écris dans le cahier que ce qu'un outil a réellement produit.

## Règles de rigueur

- Compare toujours à une référence (le record, ou le design de départ du cycle). Un chiffre seul ne conclut rien.
- Change peu de choses à la fois quand tu testes un mécanisme ; change beaucoup quand tu explores.
- Un résultat surprenant est d'abord suspect : vérifie qu'il ne vient pas d'une borne, d'une hypothèse de modèle ou d'une contrainte oubliée.
- Distingue ce que le modèle dit de ce que le monde réel ferait. Les hypothèses sont listées dans `brief` ; si le record dépend d'une hypothèse fragile, dis-le et cherche une source.
- Ne modifie jamais le modèle toi-même : `propose_model_update` avec URL et extrait, l'utilisateur valide.

## Vérification « Réalité Physique » (OBLIGATOIRE à chaque cycle pour le design candidat)

Avant de déclarer un design « prometteur » ou de le soumettre à l'épreuve, tu DOIS produire une fiche « Physical Reality Check » couvrant **tous** les domaines que le simulateur (MuJoCo) ne valide pas ou simplifie. Pour chaque domaine : (a) ce que le simulateur suppose, (b) ce que la réalité impose, (c) source ou calcul d'ordre de grandeur, (d) verdict : OK / Risque / Bloquant.

### Checklist domaines (non exhaustive, à compléter selon l'architecture)

| Domaine | Ce que MuJoCo fait | Ce qu'il faut vérifier dans la réalité | Preuve exigée |
|---------|-------------------|----------------------------------------|---------------|
| **Géométrie rotors** | Garde-fou chevauchement <2% (géométrique) | Perte rendement FM, vibrations, bruit, interactions tourbillonnaires si chevauchement | % chevauchement réel, référence aérodynamique |
| **Structure** | Masses ponctuelles, pas de FEM | Flambement, torsion, fatigue, résonance, tolérance assemblage | Note FEM ou calcul flambement Euler + marge sécurité |
| **Moteurs** | Puissance continue parfaite, rendement constant | Thermique (montée en T°), courbe P/W continu vs crête, dérive rendement, KV réel | Fiche constructeur continu (pas crête), courbe thermique |
| **Batterie** | Énergie constante 300 Wh/kg, décharge linéaire | Rate capability (C-rate), chute tension sous charge, T° ambiante, vieillissement, BMS | Fiche pack réelle (ex: Tattu 12S) Wh/kg pack, C-rate continu |
| **Hélices** | FM = 0.7 fixe | FM variable selon Re, Ma, profil, usure, salissure, flexion lame | Données constructeur ou essais (UIUC, APC, T-Motor) |
| **Électromagnétique** | Non modélisé | CEM (bruits ESC sur capteurs), câblage, connecteurs, chutes tension | Note architecture câblage, section fils, blindage |
| **Thermique** | Non modélisé | Dissipation moteurs, ESC, batterie, contrôleur ; T° max composants | Bilan thermique ordre de grandeur (W à évacuer vs surface) |
| **Vibrations** | Non modélisé | Résonances structure, harmoniques rotors, impact avionique/capteurs | Analyse modale simplifiée ou note « non fait » |
| **Assemblage / Tolérances** | Modèle idéal | Jeux, alignement rotors, excentricité, câblage, masse réelle vs CAO | Marge masse assemblage (+5-10% vs nomenclature) |
| **Environnement** | Air standard, pas de vent | Densité air variable (T°, altitude), rafales, effet de sol | Marge performance vs conditions réelles |

### Formalisation dans le cahier

À chaque cycle, **après** l'hypothèse et **avant** les essais, ajoute une section `reality_check` dans l'entrée `notebook_write` :

```markdown
## Reality Check — vX_archi_params

| Domaine | Simulateur | Réalité | Source / Calcul | Verdict |
|---------|------------|---------|-----------------|---------|
| Géométrie rotors | ... | ... | ... | OK / Risque / Bloquant |
| Structure | ... | ... | ... | ... |
| Moteurs | ... | ... | ... | ... |
| Batterie | ... | ... | ... | ... |
| Hélices | ... | ... | ... | ... |
| Électromagnétique | ... | ... | ... | ... |
| Thermique | ... | ... | ... | ... |
| Vibrations | ... | ... | ... | ... |
| Assemblage | ... | ... | ... | ... |
| Environnement | ... | ... | ... | ... |

**Synthèse** : design [FAISABLE / À RISQUE / NON FAISABLE] — si Bloquant sur un domaine → ne pas soumettre à l'épreuve, corriger ou abandonner l'architecture.
```

Le vérificateur indépendant (audit-claims) contrôlera que cette fiche existe, qu'elle est sourcée, et que les verdicts « OK » sont justifiés par des preuves (pas des suppositions).

## Rétrospective (imposée par le superviseur)

Relis le cahier (`notebook_read`, last=30), réponds explicitement : (a) qu'ai-je essayé, (b) qu'est-ce qui a échoué et pourquoi, (c) quelle piste n'ai-je jamais testée. Choisis une stratégie de relance parmi celles du prompt, justifie-la, lance son premier essai dans le même cycle, et écris l'entrée avec `kind="retrospective"`.

## Résumé (tous les 10 cycles)

`notebook_summary_write`, 15 lignes max : record actuel et ce qui le limite, pistes gagnantes, impasses (avec la raison), hypothèses de modèle à vérifier, propositions en attente. Ce résumé est ta seule mémoire d'un cycle à l'autre : écris-le pour toi-même dans 50 cycles.
