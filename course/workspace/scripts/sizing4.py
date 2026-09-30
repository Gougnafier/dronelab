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

# Calibrate from exam-0046
T_loaded_base = (24.93 + 97.52) * g
T_empty_base = 24.93 * g
A_base = 8 * math.pi * (0.813/2)**2

k_hover = 21958 * math.sqrt(A_base) / (T_loaded_base**1.5)
r_cruise_loaded = 17664 / 21958
P_hover_empty_base = k_hover * T_empty_base**1.5 / math.sqrt(A_base)
r_cruise_empty = 1246 / P_hover_empty_base
r_climb = 21840 / 21958
r_descent = 0.5

t_climb = cruise_alt / climb_rate
t_cruise_loaded = loaded_dist / cruise_v
t_hover_drop = hover_before
t_cruise_empty = unloaded_dist / cruise_v
t_hover_after = hover_after
t_descent = cruise_alt / descent_rate

# Corrected configs - struct_other only includes center, avionics, payload_attach
configs = [
    # (name, n, d_m, motor_kW, motor_kg_per, notes)
    ("v3_hexa36_5kW", 6, 0.914, 5, 1.0, "6x36\", 5kW motors"),
    ("v3_hexa38_5kW", 6, 0.965, 5, 1.0, "6x38\", 5kW motors"),
    ("v3_hexa40_5kW", 6, 1.016, 5, 1.0, "6x40\", 5kW motors"),
    ("v3_hexa42_5kW", 6, 1.067, 5, 1.0, "6x42\", 5kW motors"),
    ("v3_hexa38_7.5kW", 6, 0.965, 7.5, 1.5, "6x38\", 7.5kW motors"),
    ("v3_hexa40_7.5kW", 6, 1.016, 7.5, 1.5, "6x40\", 7.5kW motors"),
    ("v3_octo36_5kW", 8, 0.914, 5, 1.0, "8x36\", 5kW motors"),
    ("v3_octo38_5kW", 8, 0.965, 5, 1.0, "8x38\", 5kW motors"),
    ("v3_octo40_5kW", 8, 1.016, 5, 1.0, "8x40\", 5kW motors"),
]

# Fixed structural masses
center_kg = 0.7
avionics_kg = 0.5
payload_attach_kg = 0.1
struct_fixed = center_kg + avionics_kg + payload_attach_kg  # 1.3 kg
arm_kg_per = 0.18  # per arm
prop_kg_ref = 0.22  # at 32" (0.813m)
prop_d_ref = 0.813

print("=== Corrected structural mass ===")
for name, n, d, motor_kW, motor_kg, note in configs:
    motor_total = n * motor_kg
    prop_kg = n * prop_kg_ref * (d/prop_d_ref)**2
    arm_kg = n * arm_kg_per
    struct = motor_total + prop_kg + arm_kg + struct_fixed
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
    best_thr = (0,0,0)
    
    for payload in range(80, 150, 2):
        aircraft_mass = 24.94
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
        
        if margin > 0 and thr_climb < 0.98 and thr_cruise < 0.98 and thr_hover < 0.98:
            ratio = payload / aircraft_mass
            if ratio > best_ratio:
                best_ratio = ratio
                best_payload = payload
                best_margin = margin
                best_thr = (thr_climb, thr_cruise, thr_hover)
    
    if best_payload > 0:
        DL = (24.94 + best_payload) * g / A
        print(f"{name}: A={A:.2f}m² struct={struct:.1f}kg bat={bat_kg:.1f}kg({bat_wh:.0f}Wh) -> payload={best_payload}kg ratio={best_ratio:.3f} margin={best_margin:.0f}Wh thr={best_thr[0]:.2f}/{best_thr[1]:.2f}/{best_thr[2]:.2f} DL={DL:.0f}")
    else:
        print(f"{name}: A={A:.2f}m² struct={struct:.1f}kg bat={bat_kg:.1f}kg -> NO VALID PAYLOAD (throttle or energy limit)")

