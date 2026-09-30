"""
Cycle 93 — exploration batterie v2.
Le modele dominant est la croisiere chargee (~85% de l'energie) dont la puissance
induite en vol d'avancement varie en ~T^2/v (T = poids total), pas T^1.5 (hover).
On compare les fits E(total) en total^2 (croisiere) et en total^1.5 (hover) sur les
4 points d'examens connus, puis on explore masse batterie vs ratio.

Points de calibration (a2g, 17 m/s, aircraft 23,935 kg) :
  120   lb = 54,431 kg -> 954,4 Wh
  122,5 lb = 55,565 kg -> 976,5 Wh
  125   lb = 56,699 kg -> 999,0 Wh
  127,5 lb = 57,833 kg -> 1021,7 Wh
  130   lb = 58,967 kg -> >1026 (echec)
"""
import numpy as np

payload = np.array([54.431, 55.565, 56.699, 57.833])
energy  = np.array([954.4,  976.5,  999.0, 1021.7])
aircraft0 = 23.935
total = aircraft0 + payload

def fit_report(name, cols):
    A = np.vstack(cols).T
    coef, *_ = np.linalg.lstsq(A, energy, rcond=None)
    pred = A @ coef
    print(f"--- {name} : residus max {np.max(np.abs(energy-pred)):.2f} Wh ---")
    return coef

# modele quadratique : E = a*total^2 + b*total + c
q = fit_report("quadratique total^2", [total**2, total, np.ones_like(total)])
# modele hover : E = a*total^1.5 + b*total + c
h = fit_report("hover total^1.5", [total**1.5, total, np.ones_like(total)])
print()

def Emodel(t, coef, kind):
    if kind == 'quad': return coef[0]*t**2 + coef[1]*t + coef[2]
    else: return coef[0]*t**1.5 + coef[1]*t + coef[2]

LB = 1.133980925
def quantize_kg(m): return np.floor(m / LB) * LB

def explore(kind, coef, label):
    print(f"=== {label} ===")
    print(f"{'dens':>4} {'m_bat':>6} {'aircraft':>8} {'E_use':>6} {'tot_max':>7} {'payload':>7} {'ratio':>6}")
    for density in (155.0, 180.0, 200.0):
        for m_bat in (7.35, 8.0, 8.35, 9.0):
            E_usable = 0.9 * density * m_bat
            M = aircraft0 - 7.35 + m_bat
            if M > 24.94: continue
            lo, hi = 70.0, 150.0
            if Emodel(hi, coef, kind) < E_usable:
                tot_max = float('inf')
            else:
                for _ in range(80):
                    mid = (lo+hi)/2
                    if Emodel(mid, coef, kind) < E_usable: lo = mid
                    else: hi = mid
                tot_max = (lo+hi)/2
            if tot_max == float('inf'):
                print(f"{density:>4.0f} {m_bat:>6.2f} {M:>8.3f} {E_usable:>6.0f} {'>150':>7} {'n/a':>7} {'n/a':>6}")
                continue
            pay = quantize_kg(tot_max - M)
            if pay < 49.9: continue
            ratio = pay / M
            print(f"{density:>4.0f} {m_bat:>6.2f} {M:>8.3f} {E_usable:>6.0f} {tot_max:>7.2f} {pay:>7.2f} {ratio:>6.3f}")
    print()

explore('quad', q, "MODELE QUADRATIQUE (croisiere T^2) — extrapolation prudente")
explore('hover', h, "MODELE HOVER (T^1.5) — extrapolation optimiste")
print("Reference : ratio 2,416 (57,833 kg / 23,935 kg)")
