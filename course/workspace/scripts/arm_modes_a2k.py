#!/usr/bin/env python3
"""Cycle 99 — Modes propres du bras a2k vs bandes 1P/2P (reserve note-0018).

Le controle de compilation ne couvre que f1 (10,0 Hz). La note-0018 demande de
calculer le 2e mode de flexion (f2) et la premiere torsion du tube, et de les
comparer aux bandes d'excitation : 1P [17,5-36,2 Hz] (rotation helice) et
2P [34,9-72,3 Hz] (passage des pales).

Methode :
  - Flexion (verticale ET laterale, identiques pour un tube circulaire) :
    poutre encastree-libre avec masse ponctuelle M_bout en bout. Equation
    caracteristique exacte :
       1 + cos(L)cosh(L) + alpha*L*[cos(L)sinh(L) - sin(L)cosh(L)] = 0
    avec alpha = M_bout / m_bras. Racines L_n -> f_n = L_n^2 * sqrt(EI/(m L^3)) / 2pi.
    EI est CALE sur f1 = 10,0 Hz (valeur compilee), ce qui rend f2/f3
    independants de toute hypothese sur E.
  - Torsion (autour de l'axe longitudinal du bras, excitee par le couple rotor) :
    f_t = (1/2pi)*sqrt(k_t/I_bout), k_t = G*J/L. G non publie par le fabricant :
    plage G = 3..6 GPa (G12 d'un pli UD carbone/epoxy), J = pi(D^4-d^4)/32.
    I_bout = inertie massique de l'helice (2 pales) + moteur autour de l'axe du bras.
"""
import math
from scipy.optimize import brentq

# --- geometrie et masses bras ---
D, d = 0.030, 0.027          # tube Ø30 paroi 1,5 mm
L = 0.765                    # longueur de bras (0,035 -> 0,80 m)
m_bras = L * 0.214           # masse du tube (0,214 kg/m)
M_bout = 1.17 + 0.41 + 0.0562  # moteur + helice + support moteur (kg)
alpha = M_bout / m_bras

f1_compile = 10.0            # Hz, valeur du rapport de compilation

def char_eq(lam):
    return (1.0 + math.cos(lam) * math.cosh(lam)
            + alpha * lam * (math.cos(lam) * math.sinh(lam) - math.sin(lam) * math.cosh(lam)))

# racines de l'equation caracteristique (les premieres positives, hors lam=0)
roots = []
step = 0.15
x = step
while len(roots) < 3 and x < 20.0:
    a, b = x, x + step
    fa, fb = char_eq(a), char_eq(b)
    if fa * fb < 0:
        roots.append(brentq(char_eq, a, b))
    x = b

# EI cale sur f1
lam1 = roots[0]
# f1 = lam1^2 * sqrt(EI/(m L^3)) / 2pi  =>  sqrt(EI/(m L^3)) = 2pi f1 / lam1^2
c = (2 * math.pi * f1_compile) / (lam1 ** 2)
freqs = [(lam ** 2) * c / (2 * math.pi) for lam in roots]

print("== Flexion du bras (poutre encastree + masse en bout) ==")
print(f"m_bras = {m_bras:.4f} kg ; M_bout = {M_bout:.4f} kg ; alpha = M_bout/m_bras = {alpha:.2f}")
print(f"racines L_n = {[f'{r:.4f}' for r in roots]}")
print(f"EI cale sur f1={f1_compile} Hz")
for i, f in enumerate(freqs):
    print(f"  f{i+1} = {f:.1f} Hz")
print(f"  -> f2/f1 = {freqs[1]/freqs[0]:.2f} (et NON 6,3 : ce rapport vaut pour une poutre SANS masse en bout)")
print()

# --- torsion ---
J = math.pi * (D**4 - d**4) / 32.0
# inertie massique en bout autour de l'axe du bras :
# helice 2 pales ~ barre de longueur 2R : I = m R^2 / 3
I_prop = 0.41 * (1.018 / 2.0) ** 2 / 3.0
# moteur ~ disque Ø0,1205 : I = m R^2 / 2
I_mot = 1.17 * (0.1205 / 2.0) ** 2 / 2.0
I_bout = I_prop + I_mot

print("== Torsion du bras (axe longitudinal, couple rotor) ==")
print(f"J (constante de torsion tube) = {J:.4e} m^4")
print(f"I_bout (helice + moteur) = {I_bout:.4f} kg.m^2")
print(f"k_t = G*J/L ; G non publie -> plage 3..6 GPa (G12 carbone/epoxy UD)")
for G in (3e9, 4e9, 5e9, 6e9):
    kt = G * J / L
    ft = math.sqrt(kt / I_bout) / (2 * math.pi)
    print(f"  G={G/1e9:.0f} GPa -> f_torsion = {ft:.1f} Hz")
print()

print("== Bande d'excitation (compile) ==")
print("  1P [17,5-36,2 Hz] ; 2P [34,9-72,3 Hz]")
print("  f1 flexion ~10 Hz (SOUS 1P, hors bande) ; f2/f3 flexion >> 2P (hors bande) ;")
print("  f_torsion ~10-12 Hz (SOUS 1P, hors bande).")
