#!/usr/bin/env python3
"""
Cycle 94 — chiffrage des deux leviers restants face au facteur limitant ÉNERGIE.

(1) Architecture 12S : moteur MN1005 V2.0 (source T-Motor) — poussée max 9,3 kg/rotor.
(2) Raccourcissement des bras R 0,80 -> 0,70 m : gain masse + traînée contre coût recouvrement.

Références (épreuve v3) :
  - cda_body = body_drag_coefficient (0,8) x frontal (boîte des sphères englobantes), exam.py:490-499
  - traînée = 0.5*rho*cda*|vel|*vel (force ajoutée à la poussée désirée), exam.py:549,594
  - payload_cda_m2 = 0.06 (sizing_v3.py)
  - power_factor = 1 + 0.2 * fraction_recouverte (brief v3)
Télémétrie de référence : exam-0171 (a2g, 127,5 lb, ratio 2,416, énergie 1021,7 Wh).
"""

import math

rho = 1.225
g = 9.81
v = 17.0

# ---- Données a2g (compile.json + assembly.json + exam-0171) ----
aircraft_kg = 23.935
payload_kg = 57.833
m_loaded = aircraft_kg + payload_kg          # 81,768 kg
battery_wh = 1140.0
usable_wh = battery_wh * 0.9                 # 1026 Wh
energy_used_wh = 1021.7
margin_wh = usable_wh - energy_used_wh

arm_L = 0.68              # m (R 0.80 - hub 0.12)
arm_mass_per_m = 0.214    # kg/m (tube 30mm Easy Composites)
arm_mass = 6 * arm_L * arm_mass_per_m        # 0,873 kg

prop_D = 1.018            # m
power_factor = 1.046      # recouvrement ~23 %
max_thrust_n = 275.1      # N/rotor

cda_body = 0.848          # m² (0,8 x 1,0599)
payload_cda = 0.06        # m²

# Phases exam-0171 (télémétrie, puissance stabilisée x durée)
phases = {  # name: (durée s, puissance W)
    "climb":       (15.0, 11404.0),
    "cruise_loaded":(472.0, 6880.0),
    "hover_drop":  (2.5, 1832.0),
    "cruise_empty":(110.0, 999.0),
    "descent_land":(40.0, 1770.0),
}

print("=" * 70)
print("CYCLE 94 — leviers restants contre le facteur limitant ÉNERGIE")
print("=" * 70)
print(f"Référence a2g : ratio {payload_kg/aircraft_kg:.3f}, énergie {energy_used_wh} Wh "
      f"/ {usable_wh:.0f} Wh utiles, marge {margin_wh:.1f} Wh ({margin_wh/usable_wh*100:.2f} %)")

# =====================================================================
# (1) Architecture 12S : MN1005 V2.0
# =====================================================================
print("\n--- (1) Architecture 12S : MN1005 V2.0 ---")
mn1005_mass = 0.282          # kg ("Motor weighs only 282g", page T-Motor)
mn1005_max_thrust_kg = 9.3   # kg ("Maximum Thrust: 9.3kg")
mn1005_max_thrust_n = mn1005_max_thrust_kg * g
n_rotors = 6
total_thrust_n = n_rotors * mn1005_max_thrust_n
total_thrust_kg = total_thrust_n / g
margin = 1.6
max_payload_total_kg = total_thrust_kg / margin
print(f"  MN1005 : {mn1005_mass} kg, poussée max {mn1005_max_thrust_kg} kg/rotor "
      f"({mn1005_max_thrust_n:.0f} N)")
print(f"  Poussée statique 6 rotors : {total_thrust_kg:.1f} kg")
print(f"  Charge max (marge 1,6) : {max_payload_total_kg:.1f} kg "
      f"(record a2g chargé = {m_loaded:.1f} kg) -> RÉFUTÉ "
      f"({max_payload_total_kg/m_loaded*100:.0f} % du besoin)")

# =====================================================================
# (2) Raccourcissement bras R 0,80 -> 0,70 m
# =====================================================================
print("\n--- (2) Raccourcissement bras R 0,80 -> 0,70 m ---")
R_new = 0.70
arm_L_new = R_new - 0.12      # 0,58 m
arm_mass_new = 6 * arm_L_new * arm_mass_per_m
gain_mass_arm = arm_mass_new - arm_mass       # négatif = gain
aircraft_new = aircraft_kg + gain_mass_arm
print(f"  Bras L {arm_L:.2f} -> {arm_L_new:.2f} m ; masse {arm_mass:.3f} -> {arm_mass_new:.3f} kg "
      f"(gain {gain_mass_arm:+.3f} kg)")
print(f"  Aircraft {aircraft_kg:.3f} -> {aircraft_new:.3f} kg")

# Recouvrement / power_factor
overlap_new = (prop_D - R_new) / prop_D
pf_new = 1 + 0.2 * overlap_new
dpf = pf_new / power_factor - 1
print(f"  Recouvrement {overlap_new*100:.1f} % -> power_factor {pf_new:.4f} "
      f"(vs {power_factor}), +{dpf*100:.2f} %")

# cda_body : boîte des sphères englobantes. span_y ~ 2*(0.6928+0.0654),
# span_z ~ 2*max(rbound_bras, ...). rbound_bras = sqrt((L/2)^2 + r^2), r=0.015.
r_tube = 0.015
rbound_old = math.sqrt((arm_L/2)**2 + r_tube**2)
rbound_new = math.sqrt((arm_L_new/2)**2 + r_tube**2)
span_y_old, span_z_old = 1.5164, 0.6989
span_y_new = 2 * (R_new * math.sin(math.radians(60)) + 0.0654)
span_z_new = span_z_old * (rbound_new / rbound_old)
frontal_old = span_y_old * span_z_old
frontal_new = span_y_new * span_z_new
cda_new = cda_body * frontal_new / frontal_old
dcd = cda_new / cda_body - 1
print(f"  rbound bras {rbound_old:.4f} -> {rbound_new:.4f} m ; "
      f"span_z {span_z_old:.4f} -> {span_z_new:.4f} m ; span_y {span_y_old:.4f} -> {span_y_new:.4f} m")
print(f"  frontal {frontal_old:.4f} -> {frontal_new:.4f} m² ; "
      f"cda_body {cda_body:.3f} -> {cda_new:.3f} m² ({dcd*100:+.1f} %)")

# Gain de traînée : la traînée est une force -> T = W/cos(theta), P ~ T^1.5.
# A vide et chargé, on recalcule l'assiette et la variation de poussée.
def drag_force(cda):
    return 0.5 * rho * v**2 * cda

def tilt_deg(cda, W):
    return math.degrees(math.atan(drag_force(cda) / W))

def p_rel_change(cda_old_, cda_new_, W):
    """Variation relative de puissance induite via T = W/cos(theta), P ~ T^1.5."""
    t_old = W / math.cos(math.atan(drag_force(cda_old_) / W))
    t_new = W / math.cos(math.atan(drag_force(cda_new_) / W))
    return (t_new / t_old) ** 1.5 - 1

W_empty = aircraft_kg * g
W_loaded = m_loaded * g
cda_loaded_old = cda_body + payload_cda
cda_loaded_new = cda_new + payload_cda

print(f"\n  Assiette à vide : {tilt_deg(cda_body, W_empty):.2f}° -> "
      f"{tilt_deg(cda_new, W_empty):.2f}° (artefact lim-004)")
print(f"  Assiette chargée : {tilt_deg(cda_loaded_old, W_loaded):.2f}° -> "
      f"{tilt_deg(cda_loaded_new, W_loaded):.2f}°")

# Énergie de traînée gagnée (croisière vide + chargée, P ~ T^1.5)
gain_drag_empty_wh = phases["cruise_empty"][1] * phases["cruise_empty"][0] / 3600 \
                     * p_rel_change(cda_body, cda_new, W_empty)
gain_drag_loaded_wh = phases["cruise_loaded"][1] * phases["cruise_loaded"][0] / 3600 \
                      * p_rel_change(cda_loaded_old, cda_loaded_new, W_loaded)
gain_drag_wh = gain_drag_empty_wh + gain_drag_loaded_wh
print(f"  Gain traînée croisière à vide : {gain_drag_empty_wh:+.1f} Wh")
print(f"  Gain traînée croisière chargée : {gain_drag_loaded_wh:+.1f} Wh")
print(f"  Gain traînée total : {gain_drag_wh:+.1f} Wh")

# Coût recouvrement : power_factor s'applique à la puissance aéro (toute la
# puissance moins la traînée), approximé sur l'énergie totale.
total_energy = sum(d * p for d, p in phases.values()) / 3600
aero_energy = total_energy - (-gain_drag_wh)   # énergie aéro actuelle
cost_overlap_wh = dpf * aero_energy
print(f"  Coût recouvrement : +{dpf*100:.2f} % x {aero_energy:.0f} Wh (aéro) "
      f"= {cost_overlap_wh:+.1f} Wh")

# Gain masse : sustentation ~ W^1.5 (croisière vide + chargée)
frac_vide = gain_mass_arm / aircraft_kg
frac_loaded = gain_mass_arm / m_loaded
gain_mass_vide = phases["cruise_empty"][1] * phases["cruise_empty"][0] / 3600 \
                 * ((1 + frac_vide)**1.5 - 1)
gain_mass_loaded = phases["cruise_loaded"][1] * phases["cruise_loaded"][0] / 3600 \
                   * ((1 + frac_loaded)**1.5 - 1)
gain_mass_wh = gain_mass_vide + gain_mass_loaded
print(f"  Gain masse (sustentation ~ W^1.5) : {gain_mass_wh:+.1f} Wh "
      f"({gain_mass_vide:+.1f} vide + {gain_mass_loaded:+.1f} chargé)")

net_wh = gain_drag_wh + cost_overlap_wh + gain_mass_wh
print(f"\n  BILAN NET = traînée {gain_drag_wh:+.1f} + recouvrement {cost_overlap_wh:+.1f} "
      f"+ masse {gain_mass_wh:+.1f} = {net_wh:+.1f} Wh")
print(f"  (marge actuelle {margin_wh:.1f} Wh ; variation {net_wh/margin_wh*100:+.0f} %)")
print("  -> ordre de grandeur : NEUTRE, pas un levier décisif")
