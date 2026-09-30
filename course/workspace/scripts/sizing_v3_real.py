import math

# ===== Physique de l'épreuve v3 (constantes du brief) =====
rho = 1.225
g = 9.81
FM = 0.7
eta = 0.85
k_ind = 1.15
bat_usable = 0.9
m_aircraft_max = 24.94
thrust_margin = 1.6
payload_qualify_kg = 49.9   # 110 lb

# ===== Masses minimales (mass_floors) =====
esc_kg_per_kw = 0.06
wiring_kg_per_kw = 0.02
avionics_kg = 0.4
gear_frac = 0.04
frame_frac = 0.04

# ===== Composants réels du catalogue =====
# moteurs (name, mass_kg, P_cont_W, D_prop_m, prop_mass_kg)
# Puissance CONTINUE sourcée = point 80% throttle du tableau d'essai T-Motor :
#   note fabricant : « Motor temperature is the surface temperature after running on 80% for 10 min »
#   MN1118 KV90 : 80% = 105.19 A × 53.99 V = 5679 W (surface 110 °C < limites 150/180 °C) -> 4854 W/kg (< 5000)
#   MN1315 KV100 : 80% = 173.45 A × 54.14 V = 9391 W -> 5276 W/kg > borne 5000 W/kg -> plafonné 8900 W
motors = {
    "MN1118_KV90": dict(m=1.17, P=5679, D=1.018, prop=0.5),
    "MN1315_KV100": dict(m=1.78, P=8900, D=1.018, prop=0.5),
}
# batteries (name, mass_kg, energy_wh, max_power_w)
batteries = {
    "Tattu_Pro_14S_22000_LiPo": dict(m=7.35, E=1140, Pmax=28500, whkg=1140/7.35),
    "LiIon_6C_230Whkg_cible": dict(m=None, E=None, Pmax=None, whkg=230.0),
}

def disk_area(D):
    return math.pi * (D/2)**2

def thrust_per_rotor(P, D):
    return (P * math.sqrt(2*rho*disk_area(D)) * FM * eta) ** (2/3)

def mission_energy(n, D, P_motor, m_aircraft, m_payload, V):
    A_total = n * disk_area(D)
    W_load = (m_aircraft + m_payload) * g
    W_empty = m_aircraft * g
    def P_ind(W, V):
        return W**2 / (2*rho*A_total*V) * k_ind / eta
    def P_par(V):
        cda = 0.12 + (0.06 if m_payload > 0 else 0.0)
        return 0.5 * rho * V**3 * cda / eta
    E = 0.0
    # montée chargée
    T_load = W_load / n
    P_hover_load = n * (T_load**1.5 / math.sqrt(2*rho*disk_area(D)) * k_ind / eta)
    E += P_hover_load * 1.25 * (45.72/2.5 + 1.0) / 3600.0
    # croisière chargée
    E += (P_ind(W_load, V) + P_par(V)) * (7408.0/V) / 3600.0
    # hover avant largage
    E += P_hover_load * 5.0 / 3600.0
    # croisière à vide
    T_empty = W_empty / n
    P_hover_empty = n * (T_empty**1.5 / math.sqrt(2*rho*disk_area(D)) * k_ind / eta)
    E += (P_ind(W_empty, V) + P_par(V)) * (1852.0/V) / 3600.0
    # descente + hover après
    E += P_hover_empty * 0.5 * (45.72/1.5) / 3600.0
    E += P_hover_empty * 5.0 / 3600.0
    return E

def eval_arch(n, motor, battery_m_kg, battery_wh, battery_pmax, V):
    m_mot = n * motor["m"]
    P_tot = n * motor["P"]
    D = motor["D"]
    m_prop = n * motor["prop"]
    m_esc = esc_kg_per_kw * P_tot/1000.0
    m_wiring = wiring_kg_per_kw * P_tot/1000.0
    m_av = avionics_kg
    # bras : tubes carbone 20mm OD 1.5mm, longueur = entraxe rotors - hub
    hub_r = 0.12
    od, wall = 0.020, 0.0015
    tube_area = math.pi*(od**2-(od-2*wall)**2)/4
    arm_len = D*0.51 - hub_r   # entraxe hexa/octo ~ D/2 + marge
    arm_len = max(0.3, arm_len)
    m_arms = n * 1550.0 * tube_area * arm_len
    # train + frame (planchers fractionnaires sur m_total max)
    m_gear = gear_frac * m_aircraft_max
    m_frame = frame_frac * m_aircraft_max
    m_nonbatt = m_mot + m_prop + m_esc + m_wiring + m_av + m_arms + m_frame + m_gear
    m_aircraft = m_nonbatt + battery_m_kg
    T_per = thrust_per_rotor(motor["P"], D)
    T_total = n * T_per
    # payload poussée (marge 1.6)
    pl_thrust = (T_total / thrust_margin - m_aircraft * g) / g
    # énergie mission
    E_usable = battery_wh * bat_usable
    pl_energy = None
    for pl in range(20, 260, 5):
        if mission_energy(n, D, motor["P"], m_aircraft, pl, V) > E_usable:
            pl_energy = pl - 5
            break
    if pl_energy is None: pl_energy = 260
    # puissance batterie
    power_ok = P_tot <= battery_pmax
    pl = min(pl_thrust, pl_energy)
    ratio = pl / m_aircraft if pl > 0 else 0
    return dict(n=n, m_aircraft=m_aircraft, m_nonbatt=m_nonbatt, m_batt=battery_m_kg,
                T_total=T_total, pl_thrust=pl_thrust, pl_energy=pl_energy, power_ok=power_ok,
                pl=pl, ratio=ratio, qualify=pl >= payload_qualify_kg)

if __name__ == "__main__":
    print("="*96)
    print("DIMENSIONNEMENT v3 — composants RÉELS du catalogue (FM=0.7 fixe, marge 1.6)")
    print("="*96)
    for mn, mo in motors.items():
        for V in [13, 15, 17]:
            for n in [6, 8]:
                # batterie LiPo Tattu réelle
                b = batteries["Tattu_Pro_14S_22000_LiPo"]
                r = eval_arch(n, mo, b["m"], b["E"], b["Pmax"], V)
                tag = "QUALIFIE" if r["qualify"] else "non-qual"
                print(f"{mn} n={n} V={V} | T={r['T_total']:.0f}N pl_thrust={r['pl_thrust']:.0f}kg "
                      f"pl_energy={r['pl_energy']:.0f}kg | m_air={r['m_aircraft']:.2f}kg "
                      f"batt={r['m_batt']:.2f}kg | pl={r['pl']:.0f}kg ratio={r['ratio']:.2f} {tag}")
    # batterie Li-ion cible 230 Wh/kg : quelle masse pour E=1140 Wh ?
    print("-"*96)
    for whkg in [155, 200, 230, 260]:
        m_for_1140 = 1140/whkg
        print(f"  batterie {whkg} Wh/kg -> masse pour 1140 Wh = {m_for_1140:.2f} kg "
              f"(vs Tattu LiPo 7.35 kg)")
