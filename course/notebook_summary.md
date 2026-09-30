RECORD v3 qualifiant (c105) : a2l_hexa_mn1118_stagger, ratio 2,304 (56,699/24,606 kg), exam-0188, 125 lb, 17 m/s, marge énergie 0,32 % (1022,7/1026 Wh) — FRAGILE : < R_int 38-60 Wh (lim-006). Record robuste : 2,258 (122,5 lb, marge 2,51 %).
FACTEUR LIMITANT : ÉNERGIE, verrouillée par le palier batterie (155 Wh/kg vs 200/260). Poussée jamais limitante (80,55 kg, marge 1,6).
ALLÈGEMENT STRUCTUREL CLOS (c105) : hub v5 (−0,092 kg, SF 1,79) REFUSÉ par assembly_compile — la frame est AU PLANCHER (0,986 kg vs plancher 0,04×masse = 0,984 kg). Frame et avionics (0,406 vs 0,4) au plancher → plus AUCUN gain de masse possible dans les règles.
LEVIER BATTERIE : (1) UHV 240 Wh/kg @ 10C REFUSÉ (lim-007) → ratio ~2,81 si assoupli ; (2) Li-ion 21700 ~190 Wh/kg @ 8C : pas de produit standard publié (sur-mesure Amicell/Grepow) → ~2,72.
LEVIERS ÉPUISÉS : chaîne MN1118 (4854 W/kg) ; 12S MN1005 ; LiHV 178 (100A) ; semi-solide 350 ; vitesses 12/14 échec, 17 plafonné assiette ; allègement structurel (plancher frame).
ARTEFACTS/LIMITES : traînée sphères (lim-004, tilt 35°) ; palier 260 (lim-005) ; R_int non modélisée (lim-006, 38-60 Wh) ; palier bloque UHV 10C (lim-007).
RÉSERVES : CEM compas 0,16 m (note-0016) ; essais MuJoCo basculement/pendule (msg-0043/0050/0051) en attente.
À FAIRE : décision lim-007 (UHV 240 → ~2,81) OU source d'un pack 21700 standard ~190 Wh/kg ≥8C (~2,72) — seule voie de score restante.
