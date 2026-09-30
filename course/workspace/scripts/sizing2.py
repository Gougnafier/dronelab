import math

# From brief
rho = 1.225
g = 9.81
FM = 0.7
induced_factor = 1.15
powertrain_eff = 0.85
battery_usable = 0.9
motor_spec_power_max = 5000
battery_spec_energy_max = 300

# Mission
loaded_dist = 7408
unloaded_dist = 1852
cruise_alt = 45.72
climb_rate = 2.5
descent_rate = 1.5
hover_before = 5
hover_after = 5
cruise_v = 12.0

# Back-calculate from exam-0046 (97.52 kg payload, 24.93 kg aircraft)
# Total mass loaded = 122.45 kg
# Telemetry: P_cruise_loaded ~ 17664 W, P_climb ~ 21840 W
# Disk area = 4.15 m² (8x32")
# T_loaded = 122.45 * 9.81 = 1201 N
# T_empty = 24.93 * 9.81 = 244.5 N

T_loaded = 122.45 * g
T_empty = 24.93 * g
A = 4.15

# Ideal induced power
P_ideal_loaded = T_loaded**1.5 / math.sqrt(2 * rho * A)
P_ideal_empty = T_empty**1.5 / math.sqrt(2 * rho * A)

print(f"P_ideal_loaded: {P_ideal_loaded:.0f} W")
print(f"P_ideal_empty: {P_ideal_empty:.0f} W")

# With FM and factors
P_ind_loaded = P_ideal_loaded / FM * induced_factor / powertrain_eff
P_ind_empty = P_ideal_empty / FM * induced_factor / powertrain_eff

print(f"P_ind_loaded (model): {P_ind_loaded:.0f} W")
print(f"P_ind_empty (model): {P_ind_empty:.0f} W")

# Actual from telemetry: ~17664 W cruise loaded, ~1246 W cruise empty
# Parasite = actual - induced
P_parasite_loaded_actual = 17664 - P_ind_loaded
P_parasite_empty_actual = 1246 - P_ind_empty

print(f"P_parasite_loaded (implied): {P_parasite_loaded_actual:.0f} W")
print(f"P_parasite_empty (implied): {P_parasite_empty_actual:.0f} W")

# The model's parasite drag: 0.5 * rho * v^2 * (Cd_body + Cd_payload) * v
# Actually P_parasite = D * v = 0.5 * rho * v^3 * (CdA_body + CdA_payload)
# CdA_payload = 0.06 m² (given)
# So 0.5 * 1.225 * 12^3 * 0.06 = 0.5 * 1.225 * 1728 * 0.06 = 63.5 W
# That's tiny!

# The body drag must be: P_parasite = 0.5 * rho * v^3 * CdA_body
# So CdA_body = P_parasite / (0.5 * rho * v^3)
v = 12.0
CdA_body_loaded = P_parasite_loaded_actual / (0.5 * rho * v**3)
CdA_body_empty = P_parasite_empty_actual / (0.5 * rho * v**3)

print(f"CdA_body implied (loaded): {CdA_body_loaded:.3f} m²")
print(f"CdA_body implied (empty): {CdA_body_empty:.3f} m²")

# The brief says body_drag_coefficient = 0.8, but not the reference area.
# If Cd = 0.8, then A_ref = CdA / Cd
# For loaded: A_ref = 0.067 / 0.8 = 0.084 m² (seems small)
# Actually maybe the coefficient is already CdA (drag area in m²)?
# 0.8 m² would give P_parasite = 0.5 * 1.225 * 12^3 * 0.8 = 847 W
# But we need ~17664 - 25000 = negative! So induced is overestimated.

# Let's re-examine: maybe the simulation uses a different induced power model.
# The brief says "poussée max et puissance électrique de chaque rotor calculées par la théorie de la quantité de mouvement à partir du diamètre d'hélice et de la puissance moteur"
# So max thrust is from momentum theory: T_max = (2 * rho * A * P_shaft * FM)^(2/3) * induced_factor?
# Or P = T^1.5 / sqrt(2*rho*A) / FM * induced_factor?

# Let's check the climb phase: P_climb ~ 21840 W at start
# At start, z=0, climb rate 2.5 m/s
# Power for climb = induced + climb power (T * climb_rate) + parasite
# Climb power = T * v_climb = 1201 * 2.5 = 3002 W
# So induced + parasite = 21840 - 3002 = 18838 W
# In level cruise: induced + parasite = 17664 W
# Difference = 1174 W, close to climb power component (but less because induced changes with climb)

# Maybe the simulation uses a different FM or the induced factor applies differently.
# Let me calculate effective FM from cruise data:
# P_cruise = T^1.5 / sqrt(2*rho*A) / FM_eff / powertrain_eff + parasite
# If parasite is small (body CdA = 0.8 m² -> 847 W), then:
# 17664 - 847 = 16817 = P_ideal / FM_eff / 0.85
# FM_eff = P_ideal / (16817 * 0.85) = 13050 / 14294 = 0.91
# That's higher than 0.7!

# Or maybe the induced_factor of 1.15 is NOT applied in cruise (only for max thrust calc)?
# P = P_ideal / FM / powertrain_eff = 13050 / 0.7 / 0.85 = 21887 W
# Still higher than 17664.

# What if the simulation uses a simpler model: P = T * v_induced / FM / eff, where v_induced = sqrt(T/(2*rho*A))?
# That gives same as momentum theory.

# Let me try: maybe the "figure_of_merit" in the simulation is actually higher, or the induced_factor is only for max thrust.
# Let's just use empirical scaling from the working design.

# From exam-0046:
# P_cruise_loaded = 17664 W at 97.5 kg payload, 24.93 kg aircraft
# P_cruise_empty = 1246 W at 24.93 kg aircraft
# P_climb = 21840 W at 97.5 kg payload
# P_hover_drop = 21958 W at 97.5 kg payload

# Scale with disk loading and velocity
# P_ind ~ T^1.5 / sqrt(A)
# P_parasite ~ v^3 * CdA

# For new designs, I'll use empirical coefficients calibrated from this data.

# Calibrate: at T=1201N, A=4.15m², v=12m/s, P_cruise=17664W
# Assume P = k_ind * T^1.5 / sqrt(A) + k_par * v^3
# At empty: T=244.5N, P=1246W
# 1246 = k_ind * 244.5^1.5 / sqrt(4.15) + k_par * 12^3
# 17664 = k_ind * 1201^1.5 / sqrt(4.15) + k_par * 12^3

# 244.5^1.5 = 3818, 1201^1.5 = 41635
# sqrt(4.15) = 2.037
# 1246 = k_ind * 1874 + k_par * 1728
# 17664 = k_ind * 20439 + k_par * 1728
# Subtract: 16418 = k_ind * 18565 -> k_ind = 0.884
# Then k_par * 1728 = 1246 - 0.884*1874 = 1246 - 1657 = -411 -> negative!

# So parasite is not constant; it depends on mass/attitude too.
# Or the induced power scaling is not exactly T^1.5.

# Let's use a simpler approach: power scales roughly with T * v_induced
# v_induced = sqrt(T / (2*rho*A))
# P_ind = T * v_induced / FM / eff = T^1.5 / sqrt(2*rho*A) / FM / eff

# From data: P_cruise / (T^1.5 / sqrt(A)) = constant
# Loaded: 17664 / (1201^1.5 / sqrt(4.15)) = 17664 / 20439 = 0.864
# Empty: 1246 / (244.5^1.5 / sqrt(4.15)) = 1246 / 1874 = 0.665
# Not constant - parasite drag is significant at low thrust.

# Better: P = a * T^1.5 / sqrt(A) + b * v^3
# Two equations:
# 1246 = a * 1874 + b * 1728
# 17664 = a * 20439 + b * 1728
# Subtract: 16418 = a * 18565 -> a = 0.884
# b * 1728 = 1246 - 1657 = -411 -> b negative. Doesn't work.

# The issue: at empty weight, the drone is not at the same attitude. Parasite drag depends on tilt.
# In cruise_empty, tilt is small (tracking error 0), so parasite is low.
# In cruise_loaded, tilt is higher to overcome drag, so parasite is higher.

# Let me use the data points I have to build an empirical model for the specific configurations I want to test.
# Key insight: the current design at max payload uses ~17.7 kW cruise, ~22 kW climb/hover, ~1.2 kW cruise empty.
# Total energy from telemetry: battery went from 100% to 11.1% = 88.9% of 3747 Wh = 3331 Wh used.
# My model gave 4830 Wh - too high by 45%.

# Let me calculate actual energy from telemetry phases:
# From exam-0046 telemetry (every 10s):
# Climb: ~0-50s, avg ~21.8 kW -> 50s * 21.8/3600 = 0.30 kWh = 303 Wh
# Cruise loaded: ~50-640s (590s), avg ~17.7 kW -> 590 * 17.7/3600 = 2.90 kWh = 2900 Wh
# Hover drop: ~640-650s (10s), avg ~22 kW -> 10 * 22/3600 = 0.061 kWh = 61 Wh
# Cruise empty: ~650-830s (180s), avg ~1.2 kW -> 180 * 1.2/3600 = 0.06 kWh = 60 Wh
# Descent: ~830-860s (30s), avg ~2 kW -> 30 * 2/3600 = 0.017 kWh = 17 Wh
# Total = 303 + 2900 + 61 + 60 + 17 = 3341 Wh
# Matches ~3331 Wh from battery!

# So the empirical energy for 97.5 kg payload on v2_octo32_maxbat is ~3340 Wh.

# Now for new designs, I need to estimate how power scales.
# P_cruise_loaded ~ 17.7 kW at disk loading 289 N/m²
# If I increase disk area, disk loading decreases, induced power decreases.

# Momentum theory: P_ind ~ T^1.5 / sqrt(A)
# At same T, P_ind ~ 1/sqrt(A)
# At same disk loading (T/A constant), P_ind ~ T^1.5 / sqrt(A) ~ (DL*A)^1.5 / sqrt(A) = DL^1.5 * A
# So at constant disk loading, induced power scales linearly with disk area.

# But parasite power: P_par ~ v^3 * CdA_body. If I scale the frame with rotors, CdA might scale with rotor count or disk area.

# Let me try a practical approach: design v3 with more disk area, less structural mass, same or better motors.

print("\n=== Empirical scaling for new designs ===")

# Base: v2_octo32_maxbat
base = {
    'n': 8, 'd': 0.813, 'A': 4.15, 'motor_p': 5000, 'motor_kg': 1.0,
    'struct_kg': 24.93 - 12.52,  # 12.41 kg structure
    'bat_kg': 12.52, 'bat_wh': 3747,
    'payload': 97.5, 'P_cruise': 17.66, 'P_climb': 21.8, 'P_hover': 22.0, 'P_empty': 1.25,
    'E_total': 3340
}

print(f"Base struct mass: {base['struct_kg']:.1f} kg")
print(f"Base disk area: {base['A']:.2f} m²")
print(f"Base disk loading (at 97.5kg): {97.5*g/base['A']:.0f} N/m²")

# Target: v3_hexa36 - 6 rotors 36" (0.914m), 10kW motors
# Motor mass at 5000 W/kg: 10000/5000 = 2 kg each
# 6 motors = 12 kg (vs 8 kg for 8x5kW)
# Props: 36" carbon ~0.3 kg each -> 1.8 kg (vs 1.76 kg)
# Arms: 6 x 0.18 = 1.08 kg (vs 1.44 kg)
# Center: 0.7 kg (smaller, 6 arms) (vs 0.9 kg)
# Avionics: 0.5 kg
# Payload attach: 0.1 kg
# Total struct = 12 + 1.8 + 1.08 + 0.7 + 0.5 + 0.1 = 16.18 kg
# Battery = 24.94 - 16.18 = 8.76 kg -> 2628 Wh at 300 Wh/kg
# Usable = 2365 Wh

# Disk area: 6 * pi * (0.914/2)^2 = 6 * 0.656 = 3.94 m² (slightly less than 4.15)
# Wait, that's LESS disk area! 8x32" = 4.15, 6x36" = 3.94.
# Need larger props for hexa to beat octo.

# Try 6x38" (0.965m): A = 6 * pi * (0.965/2)^2 = 6 * 0.731 = 4.39 m² (+6%)
# Try 6x40" (1.016m): A = 6 * pi * (1.016/2)^2 = 6 * 0.811 = 4.87 m² (+17%)

# But 10kW motors at 5000 W/kg = 2kg each. 6 motors = 12kg.
# If we use 5kW motors (1kg each) on hexa: 6kg motors, struct ~10.18 kg, battery ~14.76 kg -> 4428 Wh usable 3985 Wh.
# Disk area 6x38" = 4.39 m².

# Let's calculate for several configs using empirical scaling from base.

configs = [
    # (name, n, d_m, motor_kW, motor_kg_per, struct_other_kg, notes)
    ("v3_hexa38_5kW", 6, 0.965, 5, 1.0, 1.8+1.08+0.7+0.5+0.1, "6x38\", 5kW motors"),
    ("v3_hexa40_5kW", 6, 1.016, 5, 1.0, 1.8+1.08+0.7+0.5+0.1, "6x40\", 5kW motors"),
    ("v3_hexa38_7.5kW", 6, 0.965, 7.5, 1.5, 1.8+1.08+0.7+0.5+0.1, "6x38\", 7.5kW motors (1.5kg)"),
    ("v3_hexa40_7.5kW", 6, 1.016, 7.5, 1.5, 1.8+1.08+0.7+0.5+0.1, "6x40\", 7.5kW motors"),
    ("v3_octo36_5kW", 8, 0.914, 5, 1.0, 1.76+1.44+0.9+0.5+0.1, "8x36\", 5kW motors"),
    ("v3_octo38_5kW", 8, 0.965, 5, 1.0, 1.76+1.44+0.9+0.5+0.1, "8x38\", 5kW motors"),
    ("v3_octo40_5kW", 8, 1.016, 5, 1.0, 1.76+1.44+0.9+0.5+0.1, "8x40\", 5kW motors"),
]

for name, n, d, motor_kW, motor_kg, struct_other, note in configs:
    motor_total = n * motor_kg
    prop_kg = n * 0.22 * (d/0.813)**2  # scale from 32" prop
    arm_kg = n * 0.18
    struct = motor_total + prop_kg + struct_other
    bat_kg = 24.94 - struct
    if bat_kg <= 0:
        print(f"{name}: struct {struct:.1f}kg > max, INVALID")
        continue
    bat_wh = bat_kg * 300
    usable_wh = bat_wh * 0.9
    
    A = n * math.pi * (d/2)**2
    
    # Scale power from base using momentum theory for induced, assume parasite similar
    # P_ind ~ T^1.5 / sqrt(A)
    # At same payload, P_ind_new / P_ind_base = sqrt(A_base / A_new) * (T_new/T_base)^1.5
    # But T changes with payload and aircraft mass.
    
    # Try to find max payload
    for payload in range(80, 130, 5):
        T_loaded = (24.94 + payload) * g  # aircraft at max mass
        T_empty = 24.94 * g
        
        # Induced power scaling
        P_ind_loaded = base['P_cruise'] * 1000 * (T_loaded/base['T_loaded'])**1.5 * math.sqrt(base['A']/A)
        P_ind_empty = base['P_empty'] * 1000 * (T_empty/base['T_empty'])**1.5 * math.sqrt(base['A']/A)
        
        # Parasite power: assume scales with v^3 and CdA
        # CdA_body might scale with rotor count or frame size
        # Assume CdA ~ n * d (roughly frontal area of arms)
        CdA_scale = (n * d) / (base['n'] * base['d'])
        P_par = (base['P_cruise'] - base['P_ind_loaded_base']) * 1000 * CdA_scale
        # But we don't have base P_ind separated.
        
        # Simpler: use total cruise power scaling
        # From base: at DL=289 N/m², P_cruise=17.66 kW
        # P ~ DL^1.5 * A (at constant v) + parasite
        # Actually P_ind ~ T^1.5/sqrt(A) = (DL*A)^1.5/sqrt(A) = DL^1.5 * A
        # So at same DL, P_ind ~ A
        # At same T, P_ind ~ 1/sqrt(A)
        
        DL = T_loaded / A
        # Assume P_cruise ~ a * DL^1.5 * A + b * v^3 * CdA_scale
        # Calibrate a,b from base
        pass
    
    print(f"{name}: n={n}, d={d*39.37:.0f}\", A={A:.2f}m², motor={motor_kW}kW({motor_kg}kg), struct={struct:.1f}kg, bat={bat_kg:.1f}kg({bat_wh:.0f}Wh)")

print("\n=== Let's do proper empirical model ===")

# From base: P_cruise_loaded = 17.664 kW at T=1201N, A=4.15
# P_cruise_empty = 1.246 kW at T=244.5N, A=4.15
# P_climb = 21.84 kW at T=1201N, A=4.15 (plus climb rate power)
# P_hover = 21.96 kW at T=1201N, A=4.15

# Assume P = k1 * T^1.5 / sqrt(A) + k2 * v^3 * f(n,d) + k3 * T * v_climb (for climb)

# Two equations for cruise:
# 17664 = k1 * 1201^1.5 / sqrt(4.15) + k2 * 12^3 * f(8,0.813)
# 1246 = k1 * 244.5^1.5 / sqrt(4.15) + k2 * 12^3 * f(8,0.813)

# f(n,d) = CdA_body. Assume CdA_body = c * n * d (frontal area of arms)
# f_base = 8 * 0.813 = 6.504

# 1201^1.5/sqrt(4.15) = 41635/2.037 = 20439
# 244.5^1.5/sqrt(4.15) = 3818/2.037 = 1874

# 17664 = k1 * 20439 + k2 * 1728 * c * 6.504
# 1246 = k1 * 1874 + k2 * 1728 * c * 6.504
# Subtract: 16418 = k1 * 18565 -> k1 = 0.884
# Then k2*1728*c*6.504 = 1246 - 0.884*1874 = 1246 - 1657 = -411

# Still negative. The issue is that at low thrust, the drone flies with less tilt, so parasite drag is lower.
# Parasite depends on tilt angle, which depends on thrust.
# In hover/climb, tilt=0, parasite=0 (only induced).
# In cruise, tilt = drag/thrust.

# Let me use a different approach: use the hover/climb data for induced, cruise for parasite.
# Hover: P_hover = 21958 W at T=1201N -> P_hover = k1 * T^1.5/sqrt(A)  (no parasite in hover)
# k1 = 21958 * sqrt(4.15) / 1201^1.5 = 21958 * 2.037 / 41635 = 1.075

# Check climb: P_climb = P_hover + T * v_climb = 21958 + 1201*2.5 = 21958 + 3002 = 24960 W
# But telemetry says 21840 W. So climb power is LESS than hover + climb rate? That doesn't make sense.
# Unless the induced power decreases in climb (which it does - axial flow reduces induced velocity).
# In climb, v_induced = sqrt(T/(2*rho*A)) - v_climb (approximately)
# So P_ind_climb = T * (v_ind_hover - v_climb) / FM / eff
# P_ind_climb = P_ind_hover - T * v_climb / FM / eff
# Then total climb power = P_ind_climb + T * v_climb / eff (potential energy rate)
# = P_ind_hover - T*v_climb/FM/eff + T*v_climb/eff
# = P_hover + T*v_climb/eff * (1 - 1/FM)
# With FM=0.7: 1 - 1/0.7 = -0.43 -> climb power < hover power!
# That matches: 21958 + 1201*2.5/0.85*(1-1/0.7) = 21958 + 3532*(-0.43) = 21958 - 1519 = 20439 W
# But telemetry says 21840 W. Close but not exact.

# OK, let's just use the hover power as induced power reference.
# k1 = P_hover * sqrt(A) / T^1.5 = 21958 * 2.037 / 41635 = 1.075

# Then cruise loaded: P_cruise = k1 * T^1.5/sqrt(A) + P_parasite
# 17664 = 1.075 * 20439 + P_par = 21972 + P_par -> P_par = -4308 W. Impossible.

# The hover power in telemetry is at the END of cruise_loaded (hover_drop phase), not at the same condition.
# At hover_drop, mass is still loaded (payload attached), so T=1201N.
# But power is 21958 W. In cruise, power is 17664 W.
# So cruise power < hover power! That's because in forward flight, induced power is lower (translational lift).
# Effective induced velocity in forward flight: v_ind = sqrt(T/(2*rho*A)) * (1 - something)
# Or the figure of merit improves in forward flight.

# This is getting complex. Let me just use the empirical data points directly for scaling.

# Key data points from v2_octo32_maxbat (exam-0046):
# - 97.5 kg payload, 24.93 kg aircraft, 8x32" (4.15 m²), 40 kW total motor power
# - P_cruise_loaded: 17.66 kW
# - P_hover_loaded: 21.96 kW
# - P_climb: 21.84 kW (avg)
# - P_cruise_empty: 1.25 kW
# - Total energy: 3340 Wh for 3372 Wh usable (98.9% used)

# For a new design, I'll estimate:
# 1. Hover power scales as T^1.5 / sqrt(A) * k_hover
# 2. Cruise loaded power scales similarly but with translational lift benefit
# 3. Cruise empty power is small
# 4. Energy = sum of phase powers * times

# Calibrate k_hover from base:
k_hover = 21958 * math.sqrt(4.15) / (1201**1.5)
print(f"k_hover = {k_hover:.3f}")

# For cruise, use ratio: P_cruise / P_hover = 17664 / 21958 = 0.804
# So P_cruise_loaded = 0.804 * P_hover_loaded

# For cruise empty: P_cruise_empty / P_hover_empty
# P_hover_empty = k_hover * T_empty^1.5 / sqrt(A) = 1.075 * 1874 = 2015 W
# Ratio = 1246 / 2015 = 0.618

# Climb: P_climb / P_hover = 21840 / 21958 = 0.995 (almost same as hover)

# Descent: ~2 kW observed, model: P_descent = P_hover_empty * 0.5 = 1000 W, close enough.

# Times:
# t_climb = 45.72/2.5 = 18.3 s
# t_cruise_loaded = 7408/12 = 617.3 s
# t_hover_drop = 5 s
# t_cruise_empty = 1852/12 = 154.3 s
# t_hover_after = 5 s
# t_descent = 45.72/1.5 = 30.5 s

# Total time ~ 830 s (matches telemetry ~860s with accel/decel)

def estimate_energy(payload, aircraft_mass, n, d, motor_kW, bat_wh):
    A = n * math.pi * (d/2)**2
    T_loaded = (aircraft_mass + payload) * g
    T_empty = aircraft_mass * g
    
    P_hover_loaded = k_hover * T_loaded**1.5 / math.sqrt(A)
    P_hover_empty = k_hover * T_empty**1.5 / math.sqrt(A)
    
    P_cruise_loaded = 0.804 * P_hover_loaded
    P_cruise_empty = 0.618 * P_hover_empty
    P_climb = 0.995 * P_hover_loaded  # plus potential energy? included in hover model
    P_hover_drop = P_hover_loaded
    P_descent = 0.5 * P_hover_empty
    
    E = (P_climb * 18.3 + P_cruise_loaded * 617.3 + P_hover_drop * 5 + 
         P_cruise_empty * 154.3 + P_hover_empty * 5 + P_descent * 30.5) / 3600
    
    usable = bat_wh * 0.9
    margin = usable - E
    
    # Throttle check
    total_motor_power = n * motor_kW * 1000
    throttle_climb = P_climb / total_motor_power
    throttle_cruise = P_cruise_loaded / total_motor_power
    throttle_hover = P_hover_loaded / total_motor_power
    
    return {
        'E': E, 'usable': usable, 'margin': margin,
        'P_hover_l': P_hover_loaded, 'P_cruise_l': P_cruise_loaded,
        'P_cruise_e': P_cruise_empty, 'P_climb': P_climb,
        'thr_climb': throttle_climb, 'thr_cruise': throttle_cruise, 'thr_hover': throttle_hover,
        'disk_area': A, 'disk_loading': T_loaded/A
    }

# Test on base
base_res = estimate_energy(97.5, 24.93, 8, 0.813, 5, 3747)
print(f"\nBase validation:")
print(f"  E={base_res['E']:.0f} Wh, usable={base_res['usable']:.0f}, margin={base_res['margin']:.0f}")
print(f"  P_hover_l={base_res['P_hover_l']/1000:.1f} kW, P_cruise_l={base_res['P_cruise_l']/1000:.1f} kW")
print(f"  Throttles: climb={base_res['thr_climb']:.2f}, cruise={base_res['thr_cruise']:.2f}, hover={base_res['thr_hover']:.2f}")

# Now test new configs
print("\n=== New configs ===")
for name, n, d, motor_kW, motor_kg, struct_other, note in configs:
    motor_total = n * motor_kg
    prop_kg = n * 0.22 * (d/0.813)**2
    arm_kg = n * 0.18
    struct = motor_total + prop_kg + struct_other
    bat_kg = 24.94 - struct
    if bat_kg <= 0:
        print(f"{name}: struct {struct:.1f}kg > max, INVALID")
        continue
    bat_wh = bat_kg * 300
    
    for payload in range(80, 130, 5):
        res = estimate_energy(payload, 24.94, n, d, motor_kW, bat_wh)
        ratio = payload / 24.94
        if res['margin'] > 0 and res['thr_climb'] < 1.0 and res['thr_cruise'] < 1.0 and res['thr_hover'] < 1.0:
            print(f"  {name}: payload={payload}kg ratio={ratio:.3f} E={res['E']:.0f}Wh margin={res['margin']:.0f}Wh thr_c={res['thr_climb']:.2f}/{res['thr_cruise']:.2f}/{res['thr_hover']:.2f} DL={res['disk_loading']:.0f}")

