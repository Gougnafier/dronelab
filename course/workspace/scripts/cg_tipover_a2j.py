#!/usr/bin/env python3
"""Cycle 98 — CG et angle de basculement de a2j, et bilan masse d'emploi.

Calcule le centre de gravité vertical du design compilé a2j à partir des
instances d'assembly.json (positions) et des masses du catalogue + CAO,
puis l'angle de basculement du train (base carrée, pieds à ±0,0926 m).
Compare la variante élargie (pieds à ±0,13 m).
"""
import math

# masses (kg) et positions z (m) des instances a2j (z vers le haut, moyeu z=0)
# tubes (6 bras 0,765 m + 4 jambes 0,31 m) — masse linéique 0,214 kg/m
items = []

def add(m, z):
    items.append((m, z))

# bras (6 x 0.765 m, centre z=0)
for _ in range(6):
    add(0.765 * 0.214, 0.0)
# jambes (4 x 0.31 m, centre z = (-0.04 + -0.35)/2)
for _ in range(4):
    add(0.31 * 0.214, (-0.04 - 0.35) / 2)

# supports moteur (6 x 0.0562 kg, z=0)
for _ in range(6):
    add(0.0562, 0.0)
# moteurs (6 x 1.17 kg) : 3 à z=+0.075, 3 à z=-0.08
for _ in range(3):
    add(1.17, 0.075)
for _ in range(3):
    add(1.17, -0.08)
# hélices (6 x 0.41 kg) : 3 à +0.105, 3 à -0.05
for _ in range(3):
    add(0.41, 0.105)
for _ in range(3):
    add(0.41, -0.05)
# ESC (6 x 0.47 kg, z=-0.03)
for _ in range(6):
    add(0.47, -0.03)
# batterie 7.35 kg, z=-0.2
add(7.35, -0.2)
# avionique : pixhawk 0.104 (z=0.04), gps 0.032 (z=0.07), pdb 0.27 (z=-0.09)
add(0.104, 0.04)
add(0.032, 0.07)
add(0.27, -0.09)
# câblage 0.735 kg (7 m x 0.105), z=-0.05
add(0.735, -0.05)
# moyeu 0.8454 kg, z=0
add(0.8454, 0.0)
# train landing_gear_v2 1.1076 kg, z=-0.02
add(1.1076, -0.02)
# crochet release_hook_v2 0.2135 kg, z=0
add(0.2135, 0.0)
# élingue 0.03 kg, z=-0.154
add(0.03, -0.154)

M = sum(m for m, _ in items)
Mz = sum(m * z for m, z in items)
zcg = Mz / M

plan_pieds = -0.35
h_cg = zcg - plan_pieds

# base actuelle : pieds aux diagonales ±0.0926, rayon tube 0.015
for label, half_base in [("a2j (±0.0926 m)", 0.0926 + 0.015),
                         ("variante ±0.13 m", 0.13 + 0.015),
                         ("variante ±0.14 m", 0.14 + 0.015)]:
    ang = math.degrees(math.atan(half_base / h_cg))
    print(f"{label}: demi-base {half_base:.4f} m, angle basculement {ang:.1f} deg")

print()
print(f"M totale (compilé) = {M:.3f} kg")
print(f"z_cg = {zcg:.4f} m (sous le moyeu), hauteur CG au-dessus plan posé = {h_cg:.3f} m")

# Bilan masse d'emploi
plafond = 24.94
cible = 24.79  # marge 0,15 kg sous le plafond
marge_actuelle = plafond - M

# inventaire masses manquantes (kg)
manquantes = {
    "actionneur largage (servo ~60 g)": 0.06,
    "câble seconde voie": 0.03,
    "visserie (M4/M5 + écrous + rondelles)": 0.06,
    "connecteurs AS150U/XT90 + cosses": 0.06,
    "sangles + mousse pack": 0.10,
    "mât GPS": 0.03,
    "gaines": 0.03,
}
somme_manquantes = sum(manquantes.values())

# allègements prévus
train_v2 = 1.1076
train_v3 = 0.95      # estimation, à confirmer par part_build
hub_v2 = 0.8454
hub_v3 = 0.65        # estimation, à confirmer par part_build

allègement = (train_v2 - train_v3) + (hub_v2 - hub_v3)

masse_emploi = M + somme_manquantes - allègement

print()
print("== Inventaire masses manquantes ==")
for k, v in manquantes.items():
    print(f"  {k}: {v:.3f} kg")
print(f"  somme = {somme_manquantes:.3f} kg (plancher, PDB déjà comptée 0,27 kg)")
print()
print(f"Marge actuelle (compilé) = {marge_actuelle:.3f} kg")
print(f"Allègement train {train_v2:.3f}->{train_v3:.3f} (-{train_v2-train_v3:.3f}) + hub {hub_v2:.3f}->{hub_v3:.3f} (-{hub_v2-hub_v3:.3f}) = -{allègement:.3f} kg")
print(f"Masse d'emploi estimée = {masse_emploi:.3f} kg (cible <= {cible} kg)")
print(f"Delta vs cible = {masse_emploi - cible:+.3f} kg")
print(f"Delta vs plafond = {masse_emploi - plafond:+.3f} kg")
# variante PDB haute (+0,23)
print(f"Si PDB = 0,50 kg réel (+0,23) : masse d'emploi = {masse_emploi+0.23:.3f} kg (delta plafond {masse_emploi+0.23-plafond:+.3f})")
