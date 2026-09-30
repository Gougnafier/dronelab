import math

# Constants from brief
rho = 1.225
g = 9.81
FM = 0.7
eta_powertrain = 0.85
battery_usable_frac = 0.9
battery_spec_energy = 299.9  # Wh/kg pack level
motor_spec_power = 5000  # W/kg
aircraft_mass_max = 24.94  # kg

# Fixed structure masses (from v3_hexa44_5kW design.json)
mass_center_plates = 0.7
mass_avionics = 0.5
mass_payload_attach = 0.1
mass_arm_per = 0.18  # at 0.479m length
n_arms = 6

# Prop mass estimates (scaling with diameter^2 roughly)
def prop_mass(diameter_inch):
    # 44" = 0.416 kg from design.json
    return 0.416 * (diameter_inch / 44)**2 * (44 / diameter_inch)  # rough: mass ~ D^2 * chord, chord ~ D

# Better: T-Motor prop data
# P44: 0.416 kg, P46: ?, P48: ?, P50: ?
# Assume mass scales ~ D^2.5
def prop_mass_kg(d_inch):
    return 0.416 * (d_inch / 44)**2.5

# Arm mass scales with length
# Current: motor at 0.659m from center, center plate radius 0.18m, arm length = 0.479m
# For prop diameter D (radius R), motor at R + 0.05 (motor radius)
# Arm length = (R + 0.05) - 0.18 = R - 0.13
# R = D_inch * 0.0254 / 2
def arm_mass_kg(d_inch):
    R = d_inch * 0.0254 / 2
    arm_len = max(0.479, R - 0.13)  # at least current length
    return 0.18 * (arm_len / 0.479)

def motor_mass_kg(power_w):
    return power_w / motor_spec_power

def disk_area_per_rotor(d_inch):
    R = d_inch * 0.0254 / 2
    return math.pi * R**2

def max_thrust_per_rotor(power_w, d_inch):
    A = disk_area_per_rotor(d_inch)
    # P = T^1.5 / sqrt(2*rho*A) / FM / eta
    # T = (P * sqrt(2*rho*A) * FM * eta)^(2/3)
    return (power_w * math.sqrt(2*rho*A) * FM * eta_powertrain)**(2/3)

def hover_power_per_rotor(thrust_n, d_inch):
    A = disk_area_per_rotor(d_inch)
    return thrust_n**1.5 / math.sqrt(2*rho*A) / FM / eta_powertrain

def estimate_mission_energy(payload_kg, d_inch, motor_power_w, battery_wh):
    """Rough mission energy estimate"""
    n = 6
    A_total = n * disk_area_per_rotor(d_inch)
    m_aircraft = aircraft_mass_max  # assume maxed
    m_total = m_aircraft + payload_kg
    T_total = m_total * g
    T_per = T_total / n
    
    # Climb: 45.72m at 2.5 m/s = 18.3s + settle + accel
    # Power = hover_power * climb_factor (induced + climb)
    P_hover_per = hover_power_per_rotor(T_per, d_inch)
    P_climb_per = P_hover_per * 1.3  # rough factor for climb
    t_climb = 45.72 / 2.5 + 1 + 2.5/1.0  # ~22s
    E_climb = n * P_climb_per * t_climb
    
    # Cruise loaded: 7408m at 12 m/s = 617s
    # Cruise power = induced + parasite
    V = 12.0
    # Induced power in forward flight: T^2 / (2*rho*A*V) (approx)
    P_induced_cruise_per = (T_per**2) / (2 * rho * disk_area_per_rotor(d_inch) * V)
    # Parasite: assume body drag CdA = 0.05 m^2 (from brief body_drag_coefficient 0.8, need frontal area)
    CdA_body = 0.05
    P_parasite_per = 0.5 * rho * V**3 * CdA_body / n
    P_cruise_per = (P_induced_cruise_per + P_parasite_per) / eta_powertrain
    t_cruise_loaded = 7408 / V
    E_cruise_loaded = n * P_cruise_per * t_cruise_loaded
    
    # Hover before drop: 5s at payload weight
    E_hover_load = n * P_hover_per * 5
    
    # Cruise empty: 1852m at 12 m/s = 154s
    T_empty = m_aircraft * g
    T_per_empty = T_empty / n
    P_hover_empty_per = hover_power_per_rotor(T_per_empty, d_inch)
    P_induced_empty_per = (T_per_empty**2) / (2 * rho * disk_area_per_rotor(d_inch) * V)
    P_cruise_empty_per = (P_induced_empty_per + P_parasite_per) / eta_powertrain
    t_cruise_empty = 1852 / V
    E_cruise_empty = n * P_cruise_empty_per * t_cruise_empty
    
    # Descent: 45.72m at 1.5 m/s = 30s, power ~ 0.5 * hover
    P_descent_per = P_hover_empty_per * 0.5
    t_descent = 45.72 / 1.5
    E_descent = n * P_descent_per * t_descent
    
    # Hover after drop: 5s
    E_hover_empty = n * P_hover_empty_per * 5
    
    total = E_climb + E_cruise_loaded + E_hover_load + E_cruise_empty + E_descent + E_hover_empty
    return total / 3600  # Wh

# Evaluate configurations
configs = [
    {"name": "v3_hexa44_5kW", "d_inch": 44, "motor_w": 5000},
    {"name": "v3_hexa46_5kW", "d_inch": 46, "motor_w": 5000},
    {"name": "v3_hexa48_5kW", "d_inch": 48, "motor_w": 5000},
    {"name": "v3_hexa50_5kW", "d_inch": 50, "motor_w": 5000},
    {"name": "v3_hexa46_7.5kW", "d_inch": 46, "motor_w": 7500},
    {"name": "v3_hexa48_7.5kW", "d_inch": 48, "motor_w": 7500},
]

for c in configs:
    d = c["d_inch"]
    P_motor = c["motor_w"]
    n = 6
    
    m_motors = n * motor_mass_kg(P_motor)
    m_props = n * prop_mass_kg(d)
    m_arms = n * arm_mass_kg(d)
    m_struct_fixed = mass_center_plates + mass_avionics + mass_payload_attach
    m_struct = m_motors + m_props + m_arms + m_struct_fixed
    m_battery = aircraft_mass_max - m_struct
    E_battery = m_battery * battery_spec_energy
    E_usable = E_battery * battery_usable_frac
    
    T_max_per = max_thrust_per_rotor(P_motor, d)
    T_max_total = n * T_max_per
    
    # Max payload at thrust limit
    payload_thrust_limit = (T_max_total - aircraft_mass_max * g) / g
    
    # Estimate energy at 128 kg payload
    E_mission_128 = estimate_mission_energy(128, d, P_motor, E_battery)
    
    # Max payload at energy limit (solve roughly)
    # Try payloads until energy matches
    for pl in [100, 120, 130, 140, 150, 160, 170, 180, 190, 200]:
        E = estimate_mission_energy(pl, d, P_motor, E_battery)
        if E > E_usable:
            payload_energy_limit = pl - 5
            break
    else:
        payload_energy_limit = 200
    
    payload_max = min(payload_thrust_limit, payload_energy_limit)
    ratio = payload_max / aircraft_mass_max
    
    print(f"\n{c['name']}:")
    print(f"  Diameter: {d}\", Motor: {P_motor/1000:.1f} kW")
    print(f"  Motor mass: {m_motors:.2f} kg, Props: {m_props:.2f} kg, Arms: {m_arms:.2f} kg")
    print(f"  Structure: {m_struct:.2f} kg, Battery: {m_battery:.2f} kg ({E_battery:.0f} Wh, {E_usable:.0f} Wh usable)")
    print(f"  Disk area/rotor: {disk_area_per_rotor(d):.3f} m², Total: {n*disk_area_per_rotor(d):.2f} m²")
    print(f"  Max thrust/rotor: {T_max_per:.0f} N, Total: {T_max_total:.0f} N")
    print(f"  Payload thrust limit: {payload_thrust_limit:.1f} kg")
    print(f"  Mission energy @128kg: {E_mission_128:.0f} Wh")
    print(f"  Payload energy limit: {payload_energy_limit:.1f} kg")
    print(f"  Max payload (min of both): {payload_max:.1f} kg")
    print(f"  Ratio: {ratio:.3f}")

