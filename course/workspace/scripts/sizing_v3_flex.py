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
payload_qualify_kg = 49.9

# structure (brief) : densité tube 1550, résistance 400 MPa, sécurité 1.5
dens_tube = 1550.0
strength_tube = 400e6
safety = 1.5
sigma_allow = strength_tube / safety  # 266.7 MPa

# mass_floors
esc_kg_per_kw = 0.06
wiring_kg_per_kw = 0.02
avionics_kg = 0.4
gear_frac = 0.04
frame_frac = 0.04

# ===== Composants réels (catalogue) =====
# moteur MN1118 KV90 continu 5679 W (cycle 75)
motor = dict(m=1.17, P=5679.0, D=1.018, prop=0.5)
# ESC T-Motor V200A 14S : 470 g (avec câbles), 100A continu, 18-60V
esc_mass_kg = 0.47
# batterie LiPo Tattu Pro 14S 22000mAh 25C : 7.35 kg, 1140 Wh, 28.5 kW
batt = dict(m=7.35, E=1140.0, Pmax=28500.0, whkg=1140.0/7.35)

hub_r = 0.12

def disk_area(D):
    return math.pi * (D/2)**2

def thrust_per_rotor(P, D):
    return (P * math.sqrt(2*rho*disk_area(D)) * FM * eta) ** (2/3)

def tube_choices():
    # (OD_m, wall_m)
    return [(0.020,0.0015),(0.022,0.0015),(0.025,0.0015),(0.025,0.002),
            (0.028,0.0015),(0.028,0.002),(0.030,0.0015),(0.030,0.002),
            (0.032,0.0015),(0.032,0.002),(0.035,0.002),(0.036,0.002),(0.040,0.002)]

def tube_mass_per_m(OD, wall):
    return dens_tube * math.pi*(OD**2 - (OD-2*wall)**2)/4

def tube_I(OD, wall):
    return math.pi*(OD**4 - (OD-2*wall)**4)/64

def arm_flex_stress(F, L, OD, wall):
    I = tube_I(OD, wall)
    return F * L * (OD/2) / I

def select_tube(F, L):
    for OD, wall in tube_choices():
        if arm_flex_stress(F, L, OD, wall) <= sigma_allow:
            return OD, wall, arm_flex_stress(F, L, OD, wall), tube_mass_per_m(OD, wall)
    return None  # aucun tube ne suffit

def mission_energy(n, D, m_aircraft, m_payload, V):
    A_total = n * disk_area(D)
    W_load = (m_aircraft + m_payload) * g
    W_empty = m_aircraft * g
    def P_ind(W, V):
        return W**2 / (2*rho*A_total*V) * k_ind / eta
    def P_par(V):
        cda = 0.12 + (0.06 if m_payload > 0 else 0.0)
        return 0.5 * rho * V**3 * cda / eta
    E = 0.0
    T_load = W_load / n
    P_hover_load = n * (T_load**1.5 / math.sqrt(2*rho*disk_area(D)) * k_ind / eta)
    E += P_hover_load * 1.25 * (45.72/2.5 + 1.0) / 3600.0
    E += (P_ind(W_load, V) + P_par(V)) * (7408.0/V) / 3600.0
    E += P_hover_load * 5.0 / 3600.0
    T_empty = W_empty / n
    P_hover_empty = n * (T_empty**1.5 / math.sqrt(2*rho*disk_area(D)) * k_ind / eta)
    E += (P_ind(W_empty, V) + P_par(V)) * (1852.0/V) / 3600.0
    E += P_hover_empty * 0.5 * (45.72/1.5) / 3600.0
    E += P_hover_empty * 5.0 / 3600.0
    return E

def eval_arch(n, V):
    D = motor["D"]
    # entraxe minimum (garde-fou hélices +2%)
    entraxe = D * 1.02
    # rayon du cercle : hexa côté=rayon ; octo côté=2 R sin(pi/8)
    if n == 6:
        R = entraxe
    elif n == 8:
        R = entraxe / (2*math.sin(math.pi/8))
    else:
        R = entraxe
    arm_len = R - hub_r
    # puissance moteur totale vs batterie
    P_motor_tot = n * motor["P"]
    P_batt = batt["Pmax"]
    P_per_rotor = min(motor["P"], P_batt/n)
    F = thrust_per_rotor(P_per_rotor, D)
    T_total = n * F
    # tube optimal pour la flexion (poussée max limitée batterie)
    sel = select_tube(F, arm_len)
    if sel is None:
        return dict(n=n, V=V, tube=None, m_aircraft=None, pl_thrust=None, pl_energy=None,
                    ratio=None, note="aucun tube ne tient la flexion")
    OD, wall, sigma, mpm = sel
    # masses
    m_mot = n * motor["m"]
    m_prop = n * motor["prop"]
    m_esc = n * esc_mass_kg
    m_wiring = max(wiring_kg_per_kw * P_motor_tot/1000.0, 0.68)
    m_av = avionics_kg
    m_arms = n * mpm * arm_len
    m_gear = gear_frac * m_aircraft_max
    m_frame = frame_frac * m_aircraft_max
    m_nonbatt = m_mot + m_prop + m_esc + m_wiring + m_av + m_arms + m_gear + m_frame
    m_aircraft = m_nonbatt + batt["m"]
    pl_thrust = (T_total / thrust_margin - m_aircraft * g) / g
    E_usable = batt["E"] * bat_usable
    pl_energy = None
    for pl in range(20, 260, 5):
        if mission_energy(n, D, m_aircraft, pl, V) > E_usable:
            pl_energy = pl - 5
            break
    if pl_energy is None:
        pl_energy = 260
    power_ok = P_motor_tot <= P_batt
    pl = min(pl_thrust, pl_energy)
    ratio = pl / m_aircraft if pl > 0 else 0
    return dict(n=n, V=V, R=R, arm_len=arm_len, tube=(OD,wall), sigma_MPa=sigma/1e6,
                mpm=mpm, F=F, T_total=T_total, P_motor_tot=P_motor_tot, P_batt=P_batt,
                power_ok=power_ok, m_arms=m_arms, m_esc=m_esc, m_aircraft=m_aircraft,
                m_nonbatt=m_nonbatt, pl_thrust=pl_thrust, pl_energy=pl_energy,
                pl=pl, ratio=ratio, qualify=pl>=payload_qualify_kg)

if __name__ == "__main__":
    print("="*100)
    print("DIMENSIONNEMENT v3 CORRIGÉ : flexion bras + ESC réel (V200A 470g) + puissance batterie")
    print("="*100)
    print(f"Poussée max théorique moteur (5679 W) = {thrust_per_rotor(motor['P'], motor['D']):.1f} N/rotor")
    print(f"Batterie LiPo {batt['m']}kg {batt['E']}Wh {batt['whkg']:.0f}Wh/kg, {batt['Pmax']/1000:.1f} kW max")
    print(f"Puissance 6 moteurs = {6*motor['P']/1000:.1f} kW ; 8 moteurs = {8*motor['P']/1000:.1f} kW")
    print("-"*100)
    for n in [6, 8]:
        for V in [13, 15, 17]:
            r = eval_arch(n, V)
            if r["m_aircraft"] is None:
                print(f"n={n} V={V} : {r['note']}")
                continue
            tag = "QUALIFIE" if r["qualify"] else "non-qual"
            od, wl = r["tube"]
            print(f"n={n} V={V} | R={r['R']:.3f}m arm={r['arm_len']:.3f}m tube={od*1000:.0f}mm/{wl*1000:.1f}mm "
                  f"sigma={r['sigma_MPa']:.0f}MPa | F={r['F']:.0f}N T={r['T_total']:.0f}N "
                  f"Pmot={r['P_motor_tot']/1000:.1f}kW Pbatt={r['P_batt']/1000:.1f}kW pow_ok={r['power_ok']}")
            print(f"        m_air={r['m_aircraft']:.2f}kg (bras {r['m_arms']:.2f}, esc {r['m_esc']:.2f}) "
                  f"pl_thrust={r['pl_thrust']:.0f}kg pl_energy={r['pl_energy']:.0f}kg pl={r['pl']:.0f}kg "
                  f"ratio={r['ratio']:.2f} {tag}")
    # Batterie alternative : que faut-il pour alimenter 34 kW ?
    print("-"*100)
    for whkg, C in [(155, 25), (200, 25), (230, 6), (260, 6)]:
        # 1140 Wh -> masse ; puissance = C * (E/V) * V = C*E
        m = 1140.0/whkg
        P = C * 1140.0  # watts (C-rate * Wh = W)
        print(f"  batterie {whkg} Wh/kg @ {C}C : 1140 Wh = {m:.2f} kg, puissance max = {P/1000:.1f} kW")
