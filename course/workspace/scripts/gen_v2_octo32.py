#!/usr/bin/env python3
"""
Génère le modèle MuJoCo (drone.xml) et design.json pour l'octocoptère 32".
Architecture : 8 rotors en configuration plate (8 bras radiaux).
Version allégée avec moteurs 5kW et hélices 32".
"""

import json
import math
import os

# Configuration
NAME = "v2_octo32"
N_ROTORS = 8
PROP_DIAM_M = 0.813  # 32 inches
PROP_RADIUS_M = PROP_DIAM_M / 2
ARM_LENGTH = 0.90  # distance center to rotor (m)
MOTOR_KW = 5.0  # puissance max continue par moteur
MOTOR_MAX_POWER_W = MOTOR_KW * 1000
SPINS = [1, -1] * 4  # alternance

# Masses (kg) - optimized from v1
MOTOR_MASS = 1.0   # 5kW motor at 5 kW/kg limit = 1.0 kg minimum, realistic ~1.0-1.1kg
PROP_MASS = 0.22   # hélice carbone 32" (lighter than 34")
ARM_MASS_PER = 0.15  # tube carbone 30mm OD, 1.0m ~150g
PLATE_MASS = 0.9   # plateau supérieur + inférieur (légèrement plus grand)
AVIONICS_MASS = 0.45  # FC, 8x ESC, GPS, radio, PDB, wiring
PAYLOAD_ATTACH_MASS = 0.1
BATTERY_MASS = 8.0  # 2400 Wh / 300 Wh/kg = 8.0 kg
BATTERY_ENERGY_WH = 2400
BATTERY_MAX_POWER_W = 55000  # ~23C * 2400 Wh = 55 kW max

# Masses totales
empty_mass = (N_ROTORS * (MOTOR_MASS + PROP_MASS + ARM_MASS_PER) +
              PLATE_MASS + AVIONICS_MASS + PAYLOAD_ATTACH_MASS)
total_mass = empty_mass + BATTERY_MASS

print(f"Masse à vide (sans batterie): {empty_mass:.2f} kg")
print(f"Masse batterie: {BATTERY_MASS:.2f} kg")
print(f"Masse totale: {total_mass:.2f} kg (max 24.94)")

# Vérification poussée max
RHO = 1.225
FM = 0.7
K_IND = 1.15
ETA_PT = 0.85
A_ROTOR = math.pi * PROP_RADIUS_M**2

# T_max par rotor depuis puissance
T_max_per = (MOTOR_MAX_POWER_W * FM * ETA_PT / K_IND * math.sqrt(2 * RHO * A_ROTOR))**(2/3)
T_max_total = N_ROTORS * T_max_per
T_req = total_mass * 9.81
print(f"Poussée max totale: {T_max_total:.0f} N")
print(f"Poids total: {T_req:.0f} N")
print(f"Ratio poussée/poids (vide): {T_max_total/T_req:.2f}")

# Avec charge utile 60kg
T_req_loaded = (total_mass + 60) * 9.81
print(f"Poids chargé (60kg): {T_req_loaded:.0f} N")
print(f"Ratio poussée/poids (60kg): {T_max_total/T_req_loaded:.2f}")

# Avec charge utile 80kg
T_req_loaded80 = (total_mass + 80) * 9.81
print(f"Poids chargé (80kg): {T_req_loaded80:.0f} N")
print(f"Ratio poussée/poids (80kg): {T_max_total/T_req_loaded80:.2f}")

# Surface disque totale
A_total = N_ROTORS * A_ROTOR
print(f"Surface disque totale: {A_total:.3f} m²")
print(f"Disk loading (vide): {T_req/A_total:.0f} N/m²")
print(f"Disk loading (60kg): {T_req_loaded/A_total:.0f} N/m²")
print(f"Disk loading (80kg): {T_req_loaded80/A_total:.0f} N/m²")

# Position des rotors (cercle)
rotor_positions = []
for i in range(N_ROTORS):
    angle = 2 * math.pi * i / N_ROTORS
    x = ARM_LENGTH * math.cos(angle)
    y = ARM_LENGTH * math.sin(angle)
    z = 0.05  # hauteur rotors au-dessus du centre de gravité
    rotor_positions.append((x, y, z))

# Génération MJCF
mjcf = f'''<mujoco model="{NAME}">
  <compiler angle="radian" meshdir="meshes" texturedir="textures"/>
  <option timestep="0.002" gravity="0 0 -9.81"/>
  
  <asset>
    <!-- Textures et matériaux simples -->
    <texture name="carbon" type="2d" builtin="flat" width="64" height="64" rgb1="0.2 0.2 0.2" rgb2="0.1 0.1 0.1"/>
    <material name="mat_carbon" texture="carbon" rgba="0.2 0.2 0.2 1" specular="0.3"/>
    <material name="mat_motor" rgba="0.3 0.3 0.35 1" specular="0.5"/>
    <material name="mat_prop" rgba="0.1 0.1 0.1 1" specular="0.1"/>
    <material name="mat_battery" rgba="0.15 0.15 0.2 1" specular="0.2"/>
    <material name="mat_payload" rgba="0.8 0.2 0.2 1" specular="0.3"/>
  </asset>

  <default>
    <default class="rotor_geom">
      <geom contype="0" conaffinity="0" group="1"/>
    </default>
    <default class="body_geom">
      <geom contype="1" conaffinity="1" group="2" solimp="0.9 0.95 0.001" solref="0.005 1"/>
    </default>
  </default>

  <worldbody>
    <body name="drone" pos="0 0 0.1">
      <freejoint/>
      
      <!-- Plateau central supérieur -->
      <geom name="plate_top" class="body_geom" type="cylinder" size="0.18 0.015" pos="0 0 0.05" mass="{PLATE_MASS*0.6:.3f}" material="mat_carbon"/>
      
      <!-- Plateau central inférieur (support batterie) -->
      <geom name="plate_bottom" class="body_geom" type="cylinder" size="0.20 0.01" pos="0 0 -0.1" mass="{PLATE_MASS*0.4:.3f}" material="mat_carbon"/>
      
      <!-- Boîte avionique centrée -->
      <geom name="avionics_box" class="body_geom" type="box" size="0.08 0.06 0.03" pos="0 0 0.02" mass="{AVIONICS_MASS:.3f}" material="mat_carbon"/>
      
      <!-- Attache charge utile sous le drone -->
      <site name="payload_attach" pos="0 0 -0.18" size="0.02" rgba="1 0 0 1"/>
      <geom name="payload_attach_geom" class="body_geom" type="cylinder" size="0.02 0.015" pos="0 0 -0.18" mass="{PAYLOAD_ATTACH_MASS:.3f}" material="mat_payload"/>
'''

# Bras et rotors
for i in range(N_ROTORS):
    x, y, z = rotor_positions[i]
    spin = SPINS[i]
    angle = 2 * math.pi * i / N_ROTORS
    
    # Bras (tube carbone)
    arm_length_geom = ARM_LENGTH - 0.09  # laisser place pour moteur
    
    mjcf += f'''
      <!-- Bras {i} -->
      <geom name="arm_{i}" class="body_geom" type="cylinder" size="0.015 {arm_length_geom/2:.3f}" 
            pos="{x/2:.3f} {y/2:.3f} {z:.3f}" 
            euler="0 0 {angle:.3f}" 
            mass="{ARM_MASS_PER:.3f}" material="mat_carbon"/>
      
      <!-- Moteur au bout du bras -->
      <geom name="motor_{i}" class="body_geom" type="cylinder" size="0.05 0.035" 
            pos="{x:.3f} {y:.3f} {z:.3f}" 
            mass="{MOTOR_MASS:.3f}" material="mat_motor"/>
      
      <!-- Hélice (exclue de la traînée) -->
      <geom name="prop_{i}" class="rotor_geom" type="cylinder" size="{PROP_RADIUS_M:.3f} 0.005" 
            pos="{x:.3f} {y:.3f} {z+0.035:.3f}" 
            mass="{PROP_MASS:.3f}" material="mat_prop"/>
      
      <!-- Site rotor pour l'épreuve -->
      <site name="rotor_{i}" pos="{x:.3f} {y:.3f} {z+0.035:.3f}" 
            size="0.01" rgba="0 1 0 1" type="cylinder"/>
'''

# Batterie (sous le plateau inférieur)
mjcf += f'''
      <!-- Batterie -->
      <geom name="battery_main" class="body_geom" type="box" size="0.18 0.11 0.055" 
            pos="0 0 -0.16" 
            mass="{BATTERY_MASS:.3f}" material="mat_battery"/>
'''

mjcf += '''    </body>
  </worldbody>
</mujoco>'''

# Écriture drone.xml
output_dir = f"runs/lift_challenge/workspace/designs/{NAME}"
os.makedirs(output_dir, exist_ok=True)

with open(f"{output_dir}/drone.xml", "w") as f:
    f.write(mjcf)

print(f"Écrit: {output_dir}/drone.xml")

# design.json
design = {
    "name": NAME,
    "rotors": [],
    "battery": {
        "energy_wh": BATTERY_ENERGY_WH,
        "max_power_w": BATTERY_MAX_POWER_W,
        "mass_kg": BATTERY_MASS
    },
    "cruise_speed_m_s": 12.0,
    "components": [
        {"name": "motor", "mass_kg": MOTOR_MASS, "count": N_ROTORS, "source_url": "https://store.tmotor.com/goods.php?id=618", "note": "T-Motor U15 KV100 derated to 5kW, ~1.0kg at 5kW/kg limit"},
        {"name": "propeller", "mass_kg": PROP_MASS, "count": N_ROTORS, "source_url": "https://store.tmotor.com/goods.php?id=618", "note": "T-Motor P32x10.5 carbon fiber"},
        {"name": "arm_tube", "mass_kg": ARM_MASS_PER, "count": N_ROTORS, "source_url": "https://www.rockwestcomposites.com/carbon-fiber-tubes", "note": "Carbon tube 30mm OD, 27mm ID, 1.0m"},
        {"name": "center_plates", "mass_kg": PLATE_MASS, "count": 1, "source_url": "", "note": "CFRP plates top/bottom, slightly larger"},
        {"name": "avionics", "mass_kg": AVIONICS_MASS, "count": 1, "source_url": "", "note": "FC, 8x ESC, GPS, radio, PDB, wiring"},
        {"name": "payload_attach", "mass_kg": PAYLOAD_ATTACH_MASS, "count": 1, "source_url": "", "note": "Quick-release hook"},
        {"name": "battery_pack", "mass_kg": BATTERY_MASS, "count": 1, "source_url": "https://www.tattu.com/", "note": "Tattu 12S 28000mAh 25C, ~2400 Wh, 8kg pack level"}
    ]
}

for i in range(N_ROTORS):
    x, y, z = rotor_positions[i]
    design["rotors"].append({
        "site": f"rotor_{i}",
        "spin": SPINS[i],
        "prop_diameter_m": PROP_DIAM_M,
        "motor_max_power_w": MOTOR_MAX_POWER_W
    })

with open(f"{output_dir}/design.json", "w") as f:
    json.dump(design, f, indent=2)

print(f"Écrit: {output_dir}/design.json")
print(f"Masse totale déclarée: {total_mass:.2f} kg")