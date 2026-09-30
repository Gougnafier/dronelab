import math
rho = 1.225; g = 9.81; FM = 0.7; eta = 0.85; k_ind = 1.15
bat_usable = 0.9; m_max = 24.94; margin = 1.6
dens_tube = 1550.0

motor = dict(m=1.17, P=5679.0, D=1.018, prop=0.5)   # MN1118 continu
esc_mass = 0.47
hub_r = 0.12
n = 6
D = motor["D"]
entraxe = D*1.02
R = entraxe                      # hexa
arm_len = R - hub_r

def disk_area(D): return math.pi*(D/2)**2
def thrust_per_rotor(P, D): return (P*math.sqrt(2*rho*disk_area(D))*FM*eta)**(2/3)

# tube fixe 32 mm OD / 2 mm
OD, wall = 0.032, 0.002
mpm = dens_tube*math.pi*(OD**2-(OD-2*wall)**2)/4
m_arms = n*mpm*arm_len

def mission_energy(n, D, m_air, pl, V):
    A = n*disk_area(D); Wl=(m_air+pl)*g; We=m_air*g
    P_hover = lambda W: n*((W/n)**1.5/math.sqrt(2*rho*disk_area(D))*k_ind/eta)
    Ppar = 0.5*rho*V**3*(0.12+(0.06 if pl>0 else 0))/eta
    E = P_hover(Wl)*1.25*(45.72/2.5+1.0)/3600
    E += (Wl**2/(2*rho*A*V)*k_ind/eta + Ppar)*(7408/V)/3600
    E += P_hover(Wl)*5/3600
    E += (We**2/(2*rho*A*V)*k_ind/eta + Ppar)*(1852/V)/3600
    E += P_hover(We)*0.5*(45.72/1.5)/3600
    E += P_hover(We)*5/3600
    return E

m_mot = n*motor["m"]; m_prop = n*motor["prop"]; m_esc = n*esc_mass
m_wiring = max(0.02*n*motor["P"]/1000, 0.68); m_av = 0.4
m_gear = 0.04*m_max; m_frame = 0.04*m_max
m_nonbatt = m_mot+m_prop+m_esc+m_wiring+m_av+m_arms+m_gear+m_frame

print("="*100)
print(f"HEXA 6xMN1118, tube {OD*1000:.0f}/{wall*1000:.1f} mm, arm={arm_len:.3f} m, m_arms={m_arms:.2f} kg")
print(f"m_nonbatt = {m_nonbatt:.2f} kg (mot {m_mot:.2f} prop {m_prop:.2f} esc {m_esc:.2f} cab {m_wiring:.2f} av {m_av} bras {m_arms:.2f} gear {m_gear:.2f} frame {m_frame:.2f})")
print("="*100)

for name, whkg, C, E in [("LiPo 155 (actuel)",155,25,1140),("LiHV 180",180,25,1140),("LiHV 200",200,25,1140),("LiHV 200 @20C",200,20,1140),("Li-ion 260 (6C)",260,6,1140)]:
    mb = E/whkg
    Pb = C*E/1000.0    # kW
    P_rot = min(motor["P"], Pb*1000/n)
    F = thrust_per_rotor(P_rot, D)
    T = n*F
    m_air = m_nonbatt + mb
    pl_thrust = (T/margin - m_air*g)/g
    print(f"\n{name}: {E}Wh {whkg}Wh/kg @{C}C -> {mb:.2f} kg, {Pb:.1f} kW")
    print(f"  m_air = {m_air:.2f} kg (budget {m_max}, marge {m_max-m_air:.2f} kg)")
    print(f"  poussee = {T:.0f} N ({F:.0f} N/rotor), pl_thrust = {pl_thrust:.1f} kg")
    for V in [13,15,17]:
        Em = mission_energy(n,D,m_air,50.0,V)
        E_usable = E*bat_usable
        pl_energy = None
        for pl in range(20,260,5):
            if mission_energy(n,D,m_air,pl,V) > E_usable:
                pl_energy = pl-5; break
        pl = min(pl_thrust, pl_energy)
        ratio = pl/m_air
        print(f"    V={V}: E(50)={Em:.0f}Wh E_usable={E_usable:.0f}Wh pl_energy={pl_energy}kg pl={pl:.0f}kg ratio={ratio:.2f}")
