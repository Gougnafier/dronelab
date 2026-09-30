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

# Mission - use actual durations from exam-0046
t_climb = 20.0
t_cruise_loaded = 620.0
t_hover_drop = 10.0
t_cruise_empty = 190.0
t_descent = 20.0
t_hover_after = 5.0  # not clearly separated in telemetry

# Calibrate from exam-0046 (v2_octo32_maxbat at 97.52 kg payload)
T_loaded_base = (24.93 + 97.52) * g
T_empty_base = 24.93 * g
A_base = 8 * math.pi * (0.813/2)**2

# Power at key points from telemetry
P_climb_avg = 21840  # W (at t=10s)
P_cruise_l = 17664   # W (steady state)
P_hover_drop = 21958 # W (at t=650s)
P_cruise_e = 1246    # W (steady state)
P_descent = 1956     # W (at t=840s)

# Hover power model: P_hover = k_hover * T^1.5 / sqrt(A)
k_hover = P_hover_drop * math.sqrt(A_base) / (T_loaded_base**1.5)
print(f"k_hover = {k_hover:.4f}")

# Ratios from telemetry
r_cruise_loaded = P_cruise_l / P_hover_drop
print(f"r_cruise_loaded = {r_cruise_loaded:.3f}")

P_hover_empty_base = k_hover * T_empty_base**1.5 / math.sqrt(A_base)
print(f"P_hover_empty_base = {P_hover_empty_base:.0f} W")
r_cruise_empty = P_cruise_e / P_hover_empty_base
print(f"r_cruise_empty = {r_cruise_empty:.3f}")

r_climb = P_climb_avg / P_hover_drop
print(f"r_climb = {r_climb:.3f}")

r_descent = P_descent / P_hover_empty_base
print(f"r_descent = {r_descent:.3f}")

# Validate on base
P_hover_l = k_hover * T_loaded_base**1.5 / math.sqrt(A_base)
P_hover_e = k_hover * T_empty_base**1.5 / math.sqrt(A_base)
P_climb_m = r_climb * P_hover_l
P_cruise_l_m = r_cruise_loaded * P_hover_l
P_cruise_e_m = r_cruise_empty * P_hover_e
P_descent_m = r_descent * P_hover_e

E = (P_climb_m * t_climb + P_cruise_l_m * t_cruise_loaded + P_hover_drop * t_hover_drop + 
     P_cruise_e_m * t_cruise_empty + P_hover_e * t_hover_after + P_descent_m * t_descent) / 3600
print(f"\nBase validation: E={E:.0f} Wh (actual ~3340 Wh)")
print(f"Phase energies: climb={P_climb_m*t_climb/3600:.0f}, cruise_l={P_cruise_l_m*t_cruise_loaded/3600:.0f}, hover_drop={P_hover_drop*t_hover_drop/3600:.0f}, cruise_e={P_cruise_e_m*t_cruise_empty/3600:.0f}, hover_after={P_hover_e*t_hover_after/3600:.0f}, descent={P_descent_m*t_descent/3600:.0f}")

# Fixed structural masses
center_kg = 0.7
avionics_kg = 0.5
payload_attach_kg = 0.1
struct_fixed = center_kg + avionics_kg + payload_attach_kg  # 1.3 kg
arm_kg_per = 0.18
prop_kg_ref = 0.22
prop_d_ref = 0.813

# Test configs with corrected times
configs = [
    ("v3_hexa36_5kW", 6, 0.914, 5, 1.0),
    ("v3_hexa38_5kW", 6, 0.965, 5, 1.0),
    ("v3_hexa40_5kW", 6, 1.016, 5, 1.0),
    ("v3_hexa42_5kW", 6, 1.067, 5, 1.0),
    ("v3_hexa44_5kW", 6, 1.118, 5, 1.0),
    ("v3_octo36_5kW", 8, 0.914, 5, 1.0),
    ("v3_octo38_5kW", 8, 0.965, 5, 1.0),
    ("v3_octo40_5kW", 8, 1.016, 5, 1.0),
]

print("\n=== Configs with actual phase times ===")
for name, n, d, motor_kW, motor_kg in configs:
    motor_total = n * motor_kg
    prop_kg = n * prop_kg_ref * (d/prop_d_ref)**2
    arm_kg = n * arm_kg_per
    struct = motor_total + prop_kg + arm_kg + struct_fixed
    bat_kg = 24.94 - struct
    if bat_kg <= 0:
        print(f"{name}: struct {struct:.1f}kg > max")
        continue
    bat_wh = bat_kg * 300
    usable_wh = bat_wh * 0.9
    
    A = n * math.pi * (d/2)**2
    total_motor_power = n * motor_kW * 1000
    
    best_payload = 0
    best_ratio = 0
    best_margin = -1
    best_thr = (0,0,0)
    best_DL = 0
    
    for payload in range(80, 160, 2):
        aircraft_mass = 24.94
        T_loaded = (aircraft_mass + payload) * g
        T_empty = aircraft_mass * g
        
        P_hover_l = k_hover * T_loaded**1.5 / math.sqrt(A)
        P_hover_e = k_hover * T_empty**1.5 / math.sqrt(A)
        P_cruise_l = r_cruise_loaded * P_hover_l
        P_cruise_e = r_cruise_empty * P_hover_e
        P_climb = r_climb * P_hover_l
        P_descent = r_descent * P_hover_e
        
        E = (P_climb * t_climb + P_cruise_l * t_cruise_loaded + P_hover_l * t_hover_drop + 
             P_cruise_e * t_cruise_empty + P_hover_e * t_hover_after + P_descent * t_descent) / 3600
        
        margin = usable_wh - E
        thr_climb = P_climb / total_motor_power
        thr_cruise = P_cruise_l / total_motor_power
        thr_hover = P_hover_l / total_motor_power
        
        if margin > 50 and thr_climb < 0.95 and thr_cruise < 0.95 and thr_hover < 0.95:
            ratio = payload / aircraft_mass
            if ratio > best_ratio:
                best_ratio = ratio
                best_payload = payload
                best_margin = margin
                best_thr = (thr_climb, thr_cruise, thr_hover)
                best_DL = T_loaded / A
    
    if best_payload > 0:
        print(f"{name}: A={A:.2f}m² struct={struct:.1f}kg bat={bat_kg:.1f}kg({bat_wh:.0f}Wh) -> payload={best_payload}kg ratio={best_ratio:.3f} margin={best_margin:.0f}Wh thr={best_thr[0]:.2f}/{best_thr[1]:.2f}/{best_thr[2]:.2f} DL={best_DL:.0f}")
    else:
        print(f"{name}: A={A:.2f}m² struct={struct:.1f}kg bat={bat_kg:.1f}kg -> NO VALID (margin={margin:.0f}, thr={thr_climb:.2f}/{thr_cruise:.2f}/{thr_hover:.2f})")

