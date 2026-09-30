#!/usr/bin/env python3
"""
Génère le modèle MuJoCo (drone.xml) et design.json pour l'hexacoptère 34".
Architecture : 6 rotors en configuration plate (6 bras radiaux).
"""

import json
import math
import os

# Configuration
NAME = "v2_hexa34"
N_ROTORS = 6
PROP_DIAM_M = 0.864  # 34 inches
PROP_RADIUS_M = PROP_DIAM_M / 2
ARM_LENGTH = 0.95  # distance center to rotor (m) - slightly longer for larger props
MOTOR_KW = 10.0  # puissance max continue par moteur (T-Motor U15 class)
MOTOR_MAX_POWER_W = MOTOR_KW * 1000
SPINS = [1, -1, 1, -1, 1, -1]  # alternance

# Masses (kg) - based on real components
MOTOR_MASS = 2.3   # T-Motor U15 KV80, 10kW max, ~2.3kg
PROP_MASS = 0.45   # hélice carbone 34" (T-Motor P34)
ARM_MASS_PER = 0.25  # tube carbone 30mm OD, 1.1m ~250g
PLATE_MASS = 1.0   # plateau supérieur + inférieur (plus grand pour hexa)
AVIONICS_MASS = 0.5  # FC, 6x ESC, GPS, radio, PDB, wiring
PAYLOAD_ATTACH_MASS = 0.15  # quick-release plus robuste
BATTERY_MASS = 9.0  # 2500 Wh / 280 Wh/kg = ~8.9 kg
BATTERY_ENERGY_WH = 2500
BATTERY_MAX_POWER_W = 60000  # ~25C * 2500 Wh = 62.5 kW max

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
print(f"Ratio poussée/poids: {T_max_total/T_req:.2f}")

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
      
      <!-- Plateau central supérieur (plus large pour hexa) -->
      <geom name="plate_top" class="body_geom" type="cylinder" size="0.20 0.015" pos="0 0 0.05" mass="{PLATE_MASS*0.6:.3f}" material="mat_carbon"/>
      
      <!-- Plateau central inférieur (support batterie) -->
      <geom name="plate_bottom" class="body_geom" type="cylinder" size="0.22 0.01" pos="0 0 -0.1" mass="{PLATE_MASS*0.4:.3f}" material="mat_carbon"/>
      
      <!-- Boîte avionique centrée -->
      <geom name="avionics_box" class="body_geom" type="box" size="0.08 0.06 0.03" pos="0 0 0.02" mass="{AVIONICS_MASS:.3f}" material="mat_carbon"/>
      
      <!-- Attache charge utile sous le drone -->
      <site name="payload_attach" pos="0 0 -0.20" size="0.02" rgba="1 0 0 1"/>
      <geom name="payload_attach_geom" class="body_geom" type="cylinder" size="0.025 0.02" pos="0 0 -0.20" mass="{PAYLOAD_ATTACH_MASS:.3f}" material="mat_payload"/>
'''

# Bras et rotors
for i in range(N_ROTORS):
    x, y, z = rotor_positions[i]
    spin = SPINS[i]
    angle = 2 * math.pi * i / N_ROTORS
    
    # Bras (tube carbone)
    arm_length_geom = ARM_LENGTH - 0.10  # laisser place pour moteur
    
    mjcf += f'''
      <!-- Bras {i} -->
      <geom name="arm_{i}" class="body_geom" type="cylinder" size="0.015 {arm_length_geom/2:.3f}" 
            pos="{x/2:.3f} {y/2:.3f} {z:.3f}" 
            euler="0 0 {angle:.3f}" 
            mass="{ARM_MASS_PER:.3f}" material="mat_carbon"/>
      
      <!-- Moteur au bout du bras -->
      <geom name="motor_{i}" class="body_geom" type="cylinder" size="0.06 0.04" 
            pos="{x:.3f} {y:.3f} {z:.3f}" 
            mass="{MOTOR_MASS:.3f}" material="mat_motor"/>
      
      <!-- Hélice (exclue de la traînée) -->
      <geom name="prop_{i}" class="rotor_geom" type="cylinder" size="{PROP_RADIUS_M:.3f} 0.005" 
            pos="{x:.3f} {y:.3f} {z+0.04:.3f}" 
            mass="{PROP_MASS:.3f}" material="mat_prop"/>
      
      <!-- Site rotor pour l'épreuve -->
      <site name="rotor_{i}" pos="{x:.3f} {y:.3f} {z+0.04:.3f}" 
            size="0.01" rgba="0 1 0 1" type="cylinder"/>
'''

# Batterie (sous le plateau inférieur, plus grande)
mjcf += f'''
      <!-- Batterie -->
      <geom name="battery_main" class="body_geom" type="box" size="0.20 0.12 0.06" 
            pos="0 0 -0.17" 
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
        {"name": "motor", "mass_kg": MOTOR_MASS, "count": N_ROTORS, "source_url": "https://store.tmotor.com/goods.php?id=618", "note": "T-Motor U15 KV80, 10kW max, ~2.3kg"},
        {"name": "propeller", "mass_kg": PROP_MASS, "count": N_ROTORS, "source_url": "https://store.tmotor.com/goods.php?id=618", "note": "T-Motor P34x10.5 carbon fiber"},
        {"name": "arm_tube", "mass_kg": ARM_MASS_PER, "count": N_ROTORS, "source_url": "https://www.rockwestcomposites.com/carbon-fiber-tubes", "note": "Carbon tube 30mm OD, 27mm ID, 1.1m"},
        {"name": "center_plates", "mass_kg": PLATE_MASS, "count": 1, "source_url": "", "note": "CFRP plates top/bottom, larger for hexa"},
        {"name": "avionics", "mass_kg": AVIONICS_MASS, "count": 1, "source_url": "", "note": "FC, 6x ESC, GPS, radio, PDB, wiring"},
        {"name": "payload_attach", "mass_kg": PAYLOAD_ATTACH_MASS, "count": 1, "source_url": "", "note": "Quick-release hook, reinforced"},
        {"name": "battery_pack", "mass_kg": BATTERY_MASS, "count": 1, "source_url": "https://www.tattu.com/", "note": "Tattu 12S 30000mAh 25C, ~2500 Wh, 9kg pack level"}
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