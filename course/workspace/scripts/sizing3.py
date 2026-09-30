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

# Calibrate from exam-0046 (v2_octo32_maxbat at 97.52 kg payload)
# Observed:
# P_cruise_loaded = 17.664 kW (steady state)
# P_hover_loaded = 21.958 kW (hover_drop phase)
# P_climb = 21.840 kW (initial climb)
# P_cruise_empty = 1.246 kW
# P_descent ~ 2 kW
# Total energy = 3340 Wh (from battery delta)

T_loaded_base = (24.93 + 97.52) * g  # 1201.6 N
T_empty_base = 24.93 * g  # 244.6 N
A_base = 8 * math.pi * (0.813/2)**2  # 4.15 m²

# Hover power model: P_hover = k_hover * T^1.5 / sqrt(A)
k_hover = 21958 * math.sqrt(A_base) / (T_loaded_base**1.5)
print(f"k_hover = {k_hover:.4f}")

# Cruise loaded ratio
r_cruise_loaded = 17664 / 21958
print(f"r_cruise_loaded = {r_cruise_loaded:.3f}")

# Cruise empty: need P_hover_empty
P_hover_empty_base = k_hover * T_empty_base**1.5 / math.sqrt(A_base)
print(f"P_hover_empty_base = {P_hover_empty_base:.0f} W")
r_cruise_empty = 1246 / P_hover_empty_base
print(f"r_cruise_empty = {r_cruise_empty:.3f}")

# Climb ratio
r_climb = 21840 / 21958
print(f"r_climb = {r_climb:.3f}")

# Descent ratio
r_descent = 0.5  # assumed

# Phase times
t_climb = cruise_alt / climb_rate  # 18.3 s
t_cruise_loaded = loaded_dist / cruise_v  # 617.3 s
t_hover_drop = hover_before  # 5 s
t_cruise_empty = unloaded_dist / cruise_v  # 154.3 s
t_hover_after = hover_after  # 5 s
t_descent = cruise_alt / descent_rate  # 30.5 s

print(f"\nPhase times: climb={t_climb:.1f}s, cruise_l={t_cruise_loaded:.1f}s, hover_drop={t_hover_drop}s, cruise_e={t_cruise_empty:.1f}s, hover_after={t_hover_after}s, descent={t_descent:.1f}s")

# Validate on base
P_hover_l = k_hover * T_loaded_base**1.5 / math.sqrt(A_base)
P_hover_e = k_hover * T_empty_base**1.5 / math.sqrt(A_base)
P_cruise_l = r_cruise_loaded * P_hover_l
P_cruise_e = r_cruise_empty * P_hover_e
P_climb = r_climb * P_hover_l
P_hover_drop = P_hover_l
P_descent = r_descent * P_hover_e

E = (P_climb * t_climb + P_cruise_l * t_cruise_loaded + P_hover_drop * t_hover_drop + 
     P_cruise_e * t_cruise_empty + P_hover_e * t_hover_after + P_descent * t_descent) / 3600
print(f"\nBase validation: E={E:.0f} Wh (target 3340 Wh)")

# Now test new configs
configs = [
    # (name, n, d_m, motor_kW, motor_kg_per, struct_other_kg, notes)
    ("v3_hexa36_5kW", 6, 0.914, 5, 1.0, 1.8+1.08+0.7+0.5+0.1, "6x36\", 5kW motors"),
    ("v3_hexa38_5kW", 6, 0.965, 5, 1.0, 1.8+1.08+0.7+0.5+0.1, "6x38\", 5kW motors"),
    ("v3_hexa40_5kW", 6, 1.016, 5, 1.0, 1.8+1.08+0.7+0.5+0.1, "6x40\", 5kW motors"),
    ("v3_hexa38_7.5kW", 6, 0.965, 7.5, 1.5, 1.8+1.08+0.7+0.5+0.1, "6x38\", 7.5kW motors"),
    ("v3_hexa40_7.5kW", 6, 1.016, 7.5, 1.5, 1.8+1.08+0.7+0.5+0.1, "6x40\", 7.5kW motors"),
    ("v3_octo36_5kW", 8, 0.914, 5, 1.0, 1.76+1.44+0.9+0.5+0.1, "8x36\", 5kW motors"),
    ("v3_octo38_5kW", 8, 0.965, 5, 1.0, 1.76+1.44+0.9+0.5+0.1, "8x38\", 5kW motors"),
    ("v3_octo40_5kW", 8, 1.016, 5, 1.0, 1.76+1.44+0.9+0.5+0.1, "8x40\", 5kW motors"),
]

print("\n=== New configs analysis ===")
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
    usable_wh = bat_wh * 0.9
    
    A = n * math.pi * (d/2)**2
    total_motor_power = n * motor_kW * 1000
    
    best_payload = 0
    best_ratio = 0
    best_margin = -1
    
    for payload in range(80, 140, 2):
        aircraft_mass = 24.94  # at max
        T_loaded = (aircraft_mass + payload) * g
        T_empty = aircraft_mass * g
        
        P_hover_l = k_hover * T_loaded**1.5 / math.sqrt(A)
        P_hover_e = k_hover * T_empty**1.5 / math.sqrt(A)
        P_cruise_l = r_cruise_loaded * P_hover_l
        P_cruise_e = r_cruise_empty * P_hover_e
        P_climb = r_climb * P_hover_l
        P_hover_drop = P_hover_l
        P_descent = r_descent * P_hover_e
        
        E = (P_climb * t_climb + P_cruise_l * t_cruise_loaded + P_hover_drop * t_hover_drop + 
             P_cruise_e * t_cruise_empty + P_hover_e * t_hover_after + P_descent * t_descent) / 3600
        
        margin = usable_wh - E
        thr_climb = P_climb / total_motor_power
        thr_cruise = P_cruise_l / total_motor_power
        thr_hover = P_hover_l / total_motor_power
        
        if margin > 0 and thr_climb < 1.0 and thr_cruise < 1.0 and thr_hover < 1.0:
            ratio = payload / aircraft_mass
            if ratio > best_ratio:
                best_ratio = ratio
                best_payload = payload
                best_margin = margin
                best_thr = (thr_climb, thr_cruise, thr_hover)
                best_powers = (P_climb, P_cruise_l, P_cruise_e, P_hover_l)
    
    if best_payload > 0:
        print(f"{name}: A={A:.2f}m² struct={struct:.1f}kg bat={bat_kg:.1f}kg({bat_wh:.0f}Wh) -> payload={best_payload}kg ratio={best_ratio:.3f} margin={best_margin:.0f}Wh thr={best_thr[0]:.2f}/{best_thr[1]:.2f}/{best_thr[2]:.2f} DL={((24.94+best_payload)*g/A):.0f}")
    else:
        print(f"{name}: A={A:.2f}m² struct={struct:.1f}kg bat={bat_kg:.1f}kg -> NO VALID PAYLOAD")

