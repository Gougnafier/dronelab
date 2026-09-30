import math

# Physique de l'épreuve v3 (constantes du brief, pas des hypothèses)
rho = 1.225
g = 9.81
FM = 0.7
eta = 0.85          # powertrain_efficiency
k_ind = 1.15        # induced_power_factor
bat_usable = 0.9
motor_spec_power = 5000.0   # W/kg max continu
m_aircraft_max = 24.94

# Masses minimales par famille (mass_floors)
esc_kg_per_kw = 0.06
prop_kg_at_1m = 0.25
prop_exp = 2.5
wiring_kg_per_kw = 0.02
avionics_kg = 0.4
gear_frac = 0.04
frame_frac = 0.04

# Batterie par paliers
def battery_spec_energy(wh_kg_target=None):
    # Renvoie (wh_kg, c_max) pour le palier choisi
    # Palier 1: 200 Wh/kg, 25C ; palier 2: 260 Wh/kg, 6C
    return None

# Tube carbone (structure_rules)
tube_density = 1550.0
tube_strength = 400e6
tube_sf = 1.5

# Mission
climb_alt = 45.72
climb_rate = 2.5
descent_rate = 1.5
loaded_dist = 7408.0
unloaded_dist = 1852.0
hover_before = 5.0
hover_after = 5.0
settle = 1.0
payload_cda = 0.06
body_cd = 0.8

def disk_area(D):
    R = D / 2.0
    return math.pi * R * R

def thrust_per_rotor(P, D):
    A = disk_area(D)
    return (P * math.sqrt(2*rho*A) * FM * eta) ** (2.0/3.0)

def mass_prop(D):
    return prop_kg_at_1m * (D ** prop_exp)

def mission_energy(n, D, P_motor, m_aircraft, m_payload, V, body_cda):
    """Énergie de mission (Wh) — ordre de grandeur, croisière dominante."""
    A_total = n * disk_area(D)
    W_load = (m_aircraft + m_payload) * g
    W_empty = m_aircraft * g
    # Puissance de sustentation en stationnaire (par rotor, moyenne)
    # P_ind = T^1.5 / sqrt(2 rho A) * k_ind / eta   (stationnaire)
    # Croisière chargée : induite en vol d'avancement ~ W^2/(2 rho A V) * k_ind / eta
    def P_ind(W, V):
        return W**2 / (2*rho*A_total*V) * k_ind / eta
    def P_parasite(V):
        # traînée parasite du corps (CdA) + charge
        cda = body_cda + (payload_cda if m_payload > 0 else 0.0)
        return 0.5 * rho * V**3 * cda / eta
    def P_cruise(W, V):
        return P_ind(W, V) + P_parasite(V)

    E = 0.0
    # Montée chargée : ~18.3s à puissance hover * facteur montée
    T_load = W_load / n
    P_hover_load = n * (T_load**1.5 / math.sqrt(2*rho*disk_area(D)) * k_ind / eta)
    t_climb = climb_alt / climb_rate + settle
    E += P_hover_load * 1.25 * t_climb / 3600.0
    # Croisière chargée
    t_cruise_load = loaded_dist / V
    E += P_cruise(W_load, V) * t_cruise_load / 3600.0
    # Hover avant largage
    E += P_hover_load * hover_before / 3600.0
    # Croisière à vide
    T_empty = W_empty / n
    P_hover_empty = n * (T_empty**1.5 / math.sqrt(2*rho*disk_area(D)) * k_ind / eta)
    t_cruise_empty = unloaded_dist / V
    E += P_cruise(W_empty, V) * t_cruise_empty / 3600.0
    # Descente + hover après
    E += P_hover_empty * 0.5 * (climb_alt / descent_rate) / 3600.0
    E += P_hover_empty * hover_after / 3600.0
    return E

def masses_and_budget(n, D, P_motor, m_total):
    """Masses par famille hors batterie, et batterie restante."""
    m_motors = n * P_motor / motor_spec_power
    m_esc = esc_kg_per_kw * n * P_motor / 1000.0
    m_props = n * mass_prop(D)
    m_wiring = wiring_kg_per_kw * n * P_motor / 1000.0
    m_av = avionics_kg
    # bras tubes carbone : longueur ~ distance centre -> moteur
    # hexa : centre sur cercle rayon = D*0.98 (dégagé 2%), bras ~ D*0.98 - hub_radius
    hub_r = 0.12
    arm_len = max(0.0, D*0.49 - hub_r)  # demi-entraxe ~ D/2, approx
    # tube 20mm OD 1.5mm paroi
    od, wall = 0.020, 0.0015
    id_ = od - 2*wall
    area = math.pi*(od**2 - id_**2)/4.0
    m_arms = n * tube_density * area * arm_len
    # pièces sur mesure hub + supports (estimation, affinée par CAO)
    m_hub_supports = 1.5  # kg, estimation première
    # train et frame : planchers fractionnaires (sur m_total)
    m_gear = gear_frac * m_total
    m_frame_floor = frame_frac * m_total
    m_frame = max(m_frame_floor, m_hub_supports)
    m_nonbatt = m_motors + m_esc + m_props + m_wiring + m_av + m_arms + m_frame + m_gear
    m_batt = m_total - m_nonbatt
    return dict(m_motors=m_motors, m_esc=m_esc, m_props=m_props, m_wiring=m_wiring,
                m_av=m_av, m_arms=m_arms, m_frame=m_frame, m_gear=m_gear,
                m_nonbatt=m_nonbatt, m_batt=m_batt)

def evaluate(n, D, P_motor, V, m_payload, tier=2, body_cda=0.12, verbose=True):
    m_total = m_aircraft_max
    mb = masses_and_budget(n, D, P_motor, m_total)
    m_batt = mb["m_batt"]
    if tier == 2:
        wh_kg, c_max = 260.0, 6.0
    else:
        wh_kg, c_max = 200.0, 25.0
    E_batt = m_batt * wh_kg
    E_usable = E_batt * bat_usable
    P_cr_max = c_max * E_batt  # W max soutirés (C x Wh)
    # poussée
    T_per = thrust_per_rotor(P_motor, D)
    T_total = n * T_per
    # contrainte marge 1.6
    W_req = 1.6 * (m_total + m_payload) * g
    thrust_ok = T_total >= W_req
    # puissance batterie
    P_peak = n * P_motor
    power_ok = P_peak <= P_cr_max
    # énergie mission
    E_mission = mission_energy(n, D, P_motor, m_total, m_payload, V, body_cda)
    energy_ok = E_mission <= E_usable
    ratio = m_payload / m_total
    if verbose:
        print(f"n={n} D={D*100:.0f}cm P={P_motor/1000:.1f}kW V={V}m/s payload={m_payload}kg "
              f"batt={m_batt:.2f}kg E={E_batt:.0f}Wh(us{int(E_usable)}Wh)")
        print(f"   T_total={T_total:.0f}N (req {W_req:.0f}N, {T_total/W_req:.2f}x) "
              f"| thrust_ok={thrust_ok}")
        print(f"   P_peak={P_peak/1000:.1f}kW vs batt {P_cr_max/1000:.1f}kW power_ok={power_ok}")
        print(f"   E_mission={E_mission:.0f}Wh vs usable {E_usable:.0f} energy_ok={energy_ok}")
        print(f"   masses: motors={mb['m_motors']:.2f} esc={mb['m_esc']:.2f} props={mb['m_props']:.2f} "
              f"wiring={mb['m_wiring']:.2f} av={mb['m_av']:.2f} arms={mb['m_arms']:.2f} "
              f"frame={mb['m_frame']:.2f} gear={mb['m_gear']:.2f} batt={mb['m_batt']:.2f}")
        print(f"   ratio={ratio:.3f}")
    return dict(ratio=ratio, thrust_ok=thrust_ok, power_ok=power_ok, energy_ok=energy_ok,
                E_mission=E_mission, E_usable=E_usable, m_batt=m_batt, mb=mb, T_total=T_total)

if __name__ == "__main__":
    # Balayage architectures : hexa vs octo, diamètres, puissances
    print("="*100)
    print("DIMENSIONNEMENT v3 — masses minimales + batterie 260Wh/kg(6C) + marge 1.6")
    print("="*100)
    # hexa : 6 rotors
    for D_inch in [50, 52, 54]:
        D = D_inch * 0.0254
        for P in [5000, 5500, 6000]:
            for V in [13, 15]:
                # charge = celle qui sature poussée (marge 1.6) ou énergie, on balaye
                m_total = m_aircraft_max
                mb = masses_and_budget(6, D, P, m_total)
                m_batt = mb["m_batt"]
                E_usable = m_batt * 260.0 * bat_usable
                T_total = 6 * thrust_per_rotor(P, D)
                # payload max poussée
                pl_thrust = (T_total/1.6 - m_total*g)/g
                # payload max énergie (dichotomie grossière)
                pl_energy = None
                for pl in range(20, 300, 5):
                    E = mission_energy(6, D, P, m_total, pl, V, 0.12)
                    if E > E_usable:
                        pl_energy = pl - 5
                        break
                if pl_energy is None: pl_energy = 300
                pl = min(pl_thrust, pl_energy)
                if pl < 0: pl = 0
                print(f"hexa {D_inch}\" P={P/1000:.1f}kW V={V}: pl_thrust={pl_thrust:.0f} "
                      f"pl_energy={pl_energy:.0f} -> pl={pl:.0f}kg ratio={pl/m_total:.2f} "
                      f"batt={m_batt:.2f}kg E_usable={E_usable:.0f}Wh")
