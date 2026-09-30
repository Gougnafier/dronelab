import math

# ===== Bras de l'hexa 6xMN1118 : flexion, flèche, fréquence propre =====
# Géométrie
D_prop = 1.018            # diamètre hélice VZ40 (m)
entraxe = D_prop * 1.02   # garde-fou +2%
R = entraxe                # hexa régulier : entraxe = rayon
hub_r = 0.12
L = R - hub_r             # longueur de bras (moyeu -> axe rotor)

# Charges (N)
F_batt = 252.0            # poussée par rotor limitée par pack 25C (28,5 kW)
F_motor = 283.4           # poussée par rotor à 5679 W continu moteur
F_shock = 2.0 * F_motor   # choc vertical 2g en bout

# Structure (brief) : densité tube 1550 kg/m3, résistance 400 MPa, sécurité 1.5
dens = 1550.0
strength = 400e6
safety = 1.5
sigma_allow = strength / safety   # 266.7 MPa

# Masse en bout de bras : moteur MN1118 + hélice VZ40 + support moteur (est. alu)
m_motor = 1.17
m_prop = 0.5
m_mount_est = 0.20
m_tip = m_motor + m_prop + m_mount_est

# Module du tube carbone : plage (tissé ~70 GPa -> pultrudé ~230 GPa)
E_lo = 70e9
E_hi = 230e9

def geom(OD, wall):
    ID = OD - 2*wall
    A = math.pi*(OD**2 - ID**2)/4.0
    I = math.pi*(OD**4 - ID**4)/64.0
    mpm = dens * A
    return A, I, mpm

def sigma(F, OD, I):
    return F * L * (OD/2.0) / I

def fleche(F, OD, I, E):
    return F * L**3 / (3.0 * E * I)

def f_nu(E, I, mpm):
    # poutre cantilever nue (sans masse en bout)
    return (1.875**2) / (2*math.pi*L**2) * math.sqrt(E*I/mpm)

def f_tip(E, I, mpm):
    # cantilever + masse concentrée en bout (moteur+hélice+support)
    m_tube = mpm * L
    m_eff = m_tip + 0.236*m_tube
    k = 3.0*E*I / L**3
    return (1.0/(2*math.pi)) * math.sqrt(k/m_eff)

tubes = [(0.028,0.002),(0.030,0.002),(0.032,0.002),(0.036,0.002)]

print("="*110)
print(f"BRAS HEXA 6xMN1118 : L = {L:.4f} m (R={R:.4f}, hub_r={hub_r}) ; m_tip = {m_tip:.2f} kg")
print(f"Limite règle : sigma <= 400/1.5 = {sigma_allow/1e6:.0f} MPa  (à poussée max, facteur déjà inclus)")
print(f"Excitations rotor VZ40 : 1P = 65 Hz (3900 rpm), 2P = 130 Hz")
print("="*110)
print(f"{'tube':>10} | {'mpm':>7} | {'m_6bras':>8} | {'sig252':>7} {'sig283':>7} {'sig566':>7} | {'marge283':>8} | {'fleche283':>12} | {'f_tip':>8} {'f_nu':>8}")
for OD, wall in tubes:
    A, I, mpm = geom(OD, wall)
    s252 = sigma(F_batt, OD, I)/1e6
    s283 = sigma(F_motor, OD, I)/1e6
    s566 = sigma(F_shock, OD, I)/1e6
    marge = sigma_allow/sigma(F_motor, OD, I)   # facteur vs limite à 283 N
    d_lo = fleche(F_motor, OD, I, E_lo)*1000.0
    d_hi = fleche(F_motor, OD, I, E_hi)*1000.0
    ft_lo = f_tip(E_lo, I, mpm)
    ft_hi = f_tip(E_hi, I, mpm)
    fn_lo = f_nu(E_lo, I, mpm)
    fn_hi = f_nu(E_hi, I, mpm)
    m6 = 6*mpm*L
    print(f"{OD*1000:.0f}/{wall*1000:.1f} mm | {mpm:.3f} | {m6:7.2f}kg | {s252:6.0f} {s283:6.0f} {s566:6.0f} | {marge:7.2f}x | {d_lo:5.1f}-{d_hi:5.1f} mm | {ft_lo:6.1f}-{ft_hi:6.1f} {fn_lo:5.0f}-{fn_hi:5.0f}")

print("-"*110)
print("Lecture : sig = contrainte (MPa) aux cas 252 N / 283 N / 566 N ; marge283 = facteur vs limite à poussée moteur")
print("fleche283 = déflexion en bout (mm) à 283 N, E=70..230 GPa ; f_tip = 1er mode avec masse en bout (Hz) ; f_nu = bras nu")
