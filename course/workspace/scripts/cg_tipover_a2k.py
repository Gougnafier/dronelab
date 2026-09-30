#!/usr/bin/env python3
"""Cycle 99 — CG et angle de basculement de a2k (design candidat, compile 24,606 kg).

Recalcule le centre de gravité vertical de a2k a partir des masses SOURCEES du
catalogue + CAO (masses reelles compilees) et des positions z de assembly.json,
puis l'angle de basculement du train elargi (pieds aux coins +/-0,128 m).

Repond a l'audit cycle 98 point 2 : le script precedent n'avait pas laisse de
trace d'outil. Celui-ci est execute et sa sortie reproduite dans le cahier.
"""
import math

items = []  # (masse kg, z m)

def add(m, z):
    items.append((m, z))

# --- masses SOURCEES (catalogue + CAO) ---
# tube carbone Ø30 paroi 1,5 mm : 0,214 kg/m (Easy Composites)
TUBE_M = 0.214
# bras : 6, fromto r=0,035 -> 0,80 m, longueur 0,765 m, z=0
for _ in range(6):
    add(0.765 * TUBE_M, 0.0)
# jambes : 4, fromto z=-0,04 -> -0,35 m, longueur 0,31 m, centre z=-0,195
for _ in range(4):
    add(0.31 * TUBE_M, (-0.04 - 0.35) / 2)

# supports moteur motor_mount_alu30_v3 : 0,0562 kg x6, z=0 (CAO part_build)
for _ in range(6):
    add(0.0562, 0.0)
# moteurs MN1118 : 1,17 kg x6 (catalogue), 3 hauts z=+0,075, 3 bas z=-0,08
for _ in range(3):
    add(1.17, 0.075)
for _ in range(3):
    add(1.17, -0.08)
# helices VZ40x16.1 : 0,41 kg x6, 3 hautes z=+0,105, 3 basses z=-0,05
for _ in range(3):
    add(0.41, 0.105)
for _ in range(3):
    add(0.41, -0.05)
# ESC V200A : 0,47 kg x6, z=-0,03
for _ in range(6):
    add(0.47, -0.03)
# batterie Tattu Pro 22Ah 14S : 7,35 kg, z=-0,20
add(7.35, -0.20)
# avionique : pixhawk 0,104 kg (z=+0,04), gps 0,032 (z=+0,07), pdb 0,27 (z=-0,09)
add(0.104, 0.04)
add(0.032, 0.07)
add(0.27, -0.09)
# cablage 8 AWG : 7 m x 0,105 kg/m = 0,735 kg, z=-0,05
add(7.0 * 0.105, -0.05)
# hub_hexa_alu30_v3 : 0,649 kg, z=0 (CAO part_build)
add(0.649, 0.0)
# landing_gear_v3 : 1,0274 kg, z=-0,02 (CAO part_build)
add(1.0274, -0.02)
# release_hook_v2 : 0,2135 kg, z=0 (CAO part_build)
add(0.2135, 0.0)
# elingue 0,19 m : 0,03 kg, z=-0,154
add(0.03, -0.154)
# actionneur + accessoires (acc) : 0,31 kg, z=0 (catalogue other)
add(0.31, 0.0)

M = sum(m for m, _ in items)
Mz = sum(m * z for m, z in items)
zcg = Mz / M

plan_pieds = -0.35  # bas des jambes (fromto z=-0,35)
h_cg = zcg - plan_pieds

print("== CG a2k (masses sourcees catalogue + CAO) ==")
print(f"M totale (compile) = {M:.3f} kg")
print(f"z_cg = {zcg:.4f} m sous le moyeu (z=0)")
print(f"plan de pose = {plan_pieds:.2f} m ; hauteur CG au-dessus du plan de contact = {h_cg:.4f} m")
print()

# base d'appui : pieds aux coins (+/-0,128, +/-0,128) ; rayon tube 0,015 m.
# basculement critique autour d'une ARETE du carre -> demi-cote 0,128 m.
half_base = 0.128 + 0.015
ang = math.degrees(math.atan(half_base / h_cg))
print("== Angle de basculement ==")
print(f"demi-base (arete du carre + rayon tube) = {half_base:.4f} m")
print(f"angle de basculement = atan({half_base:.3f}/{h_cg:.3f}) = {ang:.1f} deg")
print()

# marge de pesage (plafond 24,94 kg ; cible 24,79 kg)
plafond = 24.94
cible = 24.79
print("== Pesage ==")
print(f"masse a2k compilee = {M:.3f} kg")
print(f"marge sous plafond 24,94 kg = {plafond - M:+.3f} kg")
print(f"marge sous cible 24,79 kg   = {cible - M:+.3f} kg")
# si la PDB pesait 0,50 kg au lieu de 0,27 kg
print(f"si PDB = 0,50 kg (+0,23) -> masse d'emploi {M + 0.23:.3f} kg (delta plafond {M + 0.23 - plafond:+.3f})")
