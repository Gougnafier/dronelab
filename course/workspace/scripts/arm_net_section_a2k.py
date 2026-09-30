"""
Cycle 101 — msg-0047 (éclaireur) : section nette du tube carbone Ø30 paroi 1,5 mm
au droit des perçages M4 d'anti-rotation, et chiffrage du joint de blocage.

1) Couple réactif rotor = torque_to_thrust_per_m x T_max = 0,02 x 275,1 N = 5,5 N.m
2) Force de cisaillement sur la vis M4 (rayon moyen du tube = 13,5 mm)
3) Pression d'appui de la vis M4 dans la paroi carbone (2 parois x 1,5 mm)
4) Section nette du tube (2 trous Ø4 aux fibres extrêmes z=±15) sous flexion max
"""
import math

# --- Tube carbone Ø30 paroi 1,5 mm ---
D = 30.0    # mm
d = 27.0    # mm (D - 2*1.5)
t = 1.5     # mm

I_brut = math.pi / 64.0 * (D**4 - d**4)   # mm^4
W_brut = I_brut / (D / 2.0)                # mm^3
A_brut = math.pi / 4.0 * (D**2 - d**2)     # mm^2

# 2 trous Ø4 aux fibres extrêmes (z = +/-15 mm)
hole_d = 4.0
z_fibre = D / 2.0
I_removed = 2.0 * (hole_d * t) * (z_fibre ** 2)   # mm^4 (theoreme des axes paralleles)
I_net = I_brut - I_removed
W_net = I_net / (D / 2.0)
A_net = A_brut - 2.0 * (hole_d * t)

sigma_brut = 205.2          # MPa (compile a2k, bras en flexion max)
sigma_lim = 400.0 / 1.5     # 266,7 MPa (resistance 400 MPa / SF 1,5)

sigma_net = sigma_brut * (W_brut / W_net)
marge_net = sigma_lim / sigma_net - 1.0

print("=== Section nette tube Ø30 paroi 1,5 mm, 2 trous Ø4 ===")
print(f"I_brut = {I_brut:.0f} mm^4, W_brut = {W_brut:.1f} mm^3, A_brut = {A_brut:.1f} mm^2")
print(f"I_enleve (2 trous Ø4) = {I_removed:.0f} mm^4")
print(f"I_net  = {I_net:.0f} mm^4, W_net = {W_net:.1f} mm^3, A_net = {A_net:.1f} mm^2")
print(f"sigma_brut (compile) = {sigma_brut} MPa")
print(f"sigma_nette = sigma_brut x (W_brut/W_net) = {sigma_net:.1f} MPa")
print(f"Limite = {sigma_lim:.1f} MPa -> marge nette = {marge_net*100:.1f} % (critere eclaireur : >= 20 %)")

print("\n=== Joint de blocage (vis M4 anti-rotation) ===")
T_max = 275.1        # N (poussee max par rotor, source eclaireur/exam)
r_arm = 0.02         # m (torque_to_thrust_per_m, brief)
C_react = r_arm * T_max
print(f"Couple reactif rotor = {r_arm} x {T_max} = {C_react:.2f} N.m")

r_bolt = 13.5e-3     # m (rayon moyen du tube, bras de levier de la vis)
F_shear = C_react / r_bolt
print(f"Force de cisaillement sur la vis M4 = {C_react:.2f}/{r_bolt*1000:.1f} mm = {F_shear:.0f} N")

# Resistance au cisaillement vis M4 classe 8.8 (ordre de grandeur)
d_M4 = 4.0
A_bolt = math.pi / 4.0 * d_M4**2
sigma_y_88 = 640.0   # MPa
F_shear_ult = 0.6 * sigma_y_88 * A_bolt
print(f"Vis M4 8.8 : section {A_bolt:.1f} mm^2, cisaillement ultime ~{F_shear_ult:.0f} N")
print(f"  -> marge vis en cisaillement = {F_shear_ult/F_shear:.1f}")

# Pression d'appui de la vis sur le carbone (2 parois x 1,5 mm)
bearing_area = 2.0 * d_M4 * t
P_bearing = F_shear / bearing_area
print(f"Portee de la vis dans la paroi carbone = 2 x {d_M4} x {t} = {bearing_area:.0f} mm^2")
print(f"Pression d'appui = {F_shear:.0f}/{bearing_area:.0f} = {P_bearing:.1f} MPa")
print(f"  (resistance en matage du carbone roll-wrapped transverse ~150-250 MPa)")

# Distance au bord : vis au centre du manchon (r~50 pour le hub), bord du manchon r=60
print("\n=== Distance au bord (hub) ===")
print("Vis hub a r=70 mm, manchon alu r=40..60 mm -> vis 10 mm AU-DELA du manchon (defaut)")
print("Vis mount a x=-12 mm, manchon x=-60..+25 -> vis 12 mm du bout du tube, 48 mm du bord interieur")
