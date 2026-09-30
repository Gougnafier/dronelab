"""
Cycle 101 — msg-0046 (éclaireur) : perte ohmique interne du pack Tattu Pro 22 Ah 14S.
Calcule l'énergie dissipée dans la résistance interne du pack, ∫ I²·R_int dt, à partir
des puissances et durées par phase relevées dans la télémétrie exam-0185 (122,5 lb),
et la compare à la marge énergétique de l'épreuve (1000,2 / 1026 Wh = 25,8 Wh).

Hypothèses (ordre de grandeur, documentées) :
- tension de pack constante 51,8 V (nominale 14S), I = P / 51,8
- R_int du pack = 14 cellules en série x R_cellule + connexions internes (busbars, soudures)
- R_cellule LiPo haute capacité ~1,0-1,5 mOhm (ordre de grandeur documenté)
"""
import math

V = 51.8  # V nominal 14S

# (phase, durée s, puissance moyenne W) relevées depuis exam_telemetry exam-0185
phases = [
    ("climb (montee)",            18.0, 11000.0),   # pic 12614 -> plateau 11078
    ("cruise_loaded (charge)",   453.0,  6705.0),   # plateau 6705 (4 nmi @ 17 m/s)
    ("hover avant largage",        4.0, 11200.0),
    ("hover apres largage",        5.0,  1900.0),
    ("cruise_empty (a vide)",    109.0,  1086.0),   # plateau 1086 (1 nmi)
    ("descente + atterrissage",   30.0,  1000.0),
]

# Integrale ∫ I² dt (A²·s) par phase
integral_A2s = 0.0
print("Phase                         duree(s)   P_moy(W)   I(A)   I2*dt(A2.s)")
for name, dur, P in phases:
    I = P / V
    i2dt = I * I * dur
    integral_A2s += i2dt
    print(f"{name:28s} {dur:8.1f} {P:10.1f} {I:7.1f} {i2dt:12.0f}")

integral_A2h = integral_A2s / 3600.0
print(f"\nIntegrale totale ∫ I² dt = {integral_A2s:.0f} A².s = {integral_A2h:.0f} A².h")

margin_wh = 1026.0 - 1000.2  # marge épreuve exam-0185
print(f"Marge énergie épreuve (exam-0185, 122,5 lb) = {margin_wh:.1f} Wh")

print("\nPerte ohmique = R_int x ∫ I² dt :")
print("R_int(mOhm)  R_cellule(mOhm)  Perte(Wh)  Marge_nette(Wh)  Verdict")
for R_pack_mohm in [5, 8, 10, 12, 15, 18, 20, 25]:
    loss_wh = (R_pack_mohm / 1000.0) * integral_A2h
    net = margin_wh - loss_wh
    verdict = "marge > 0" if net > 0 else "EFFACE la marge"
    # R_cellule = (R_pack - connexions ~2 mOhm)/14
    R_cell = (R_pack_mohm - 2.0) / 14.0
    print(f"{R_pack_mohm:9d}  {R_cell:14.2f}  {loss_wh:8.1f}  {net:14.1f}  {verdict}")

# Fourchette réaliste du pack : 14 x (1,0-1,5 mOhm) + 2-4 mOhm connexions
print("\nFourchette réaliste R_int pack : 14 x (1,0..1,5) + (2..4) = 16..25 mOhm")
for R in [16, 21, 25]:
    loss = (R / 1000.0) * integral_A2h
    print(f"  R_int={R} mOhm -> perte {loss:.1f} Wh -> marge nette {margin_wh-loss:.1f} Wh")
