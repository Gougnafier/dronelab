#!/usr/bin/env python
"""Cycle 100 (retrospective) — extrapolation d'energie par cran de charge sur a2k.

Baseline mesuree : exam-0183, a2k a 120 lb (54,431 kg), 17 m/s.
  masse aero = 24,606 kg -> masse totale M0 = 79,037 kg
  energie totale E0 = 977,9 Wh, batterie utilisable = 1026 Wh (marge 4,69 %)

Modele empirique : l'energie croit en ~M^1.29 (exposant cale sur le record a2g a
127,5 lb : M = 81,768 kg -> E = 1021,7 Wh, marge 0,42 %), entre a2g(127,5 lb)
et a2k(120 lb) : ln(1021,7/977,9)/ln(81,768/79,037) = 1,29.

Controle croise (decomposition sustentation/trainee depuis exam-0183) :
  trainee parasite en croisiere D = W*tan(tilt) = 79,037*9,81*tan(12,72 deg)
  -> D ~ 175 N, P_trainee = D*V = 175*17 ~ 2975 W ; sustentation = 6544-2975 ~ 3569 W.
  Postes dependant de la charge : montee (43,4 Wh) + sustentation croisiere
  (~55 % de 837,4 Wh = 460,6 Wh) + hover_drop (37,4 Wh) ~ 541,4 Wh.
  Postes independants : trainee croisiere + croisiere vide + descente ~ 429,5 Wh.
  E(M) = 541,4*(M/M0)^1.5 + 429,5.
"""
import math

M0 = 79.037          # masse totale a 120 lb (a2k 24,606 + 54,431)
E0 = 977.9           # energie totale mesuree exam-0183
EBAT = 1026.0        # batterie utilisable (22 Ah * 51,8 V * 0,9)
M_AERO = 24.606      # masse aeronef a2k

# modeles
def e_empirique(m):
    return E0 * (m / M0) ** 1.29

def e_decomp(m):
    return 541.4 * (m / M0) ** 1.5 + 429.5

print("cran_lb | payload_kg | M_total | E_empir(Wh) | marge% | E_decomp(Wh) | marge% | ratio")
for lb in [120.0, 122.5, 125.0, 127.5]:
    payload = lb * 0.45359237
    m = M_AERO + payload
    ee = e_empirique(m)
    ed = e_decomp(m)
    print(f"{lb:6.1f} | {payload:9.4f} | {m:7.3f} | {ee:11.1f} | {100*(EBAT-ee)/EBAT:5.2f} | {ed:12.1f} | {100*(EBAT-ed)/EBAT:5.2f} | {payload/M_AERO:.4f}")
