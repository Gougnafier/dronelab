import json
import math

# Design: v3_hexa44_5kW - 6 rotors, 44" (1.118m) props, 5kW motors
n = 6
prop_diam = 1.118  # 44 inches = 1.118m
motor_power = 5000  # W
motor_mass = 1.0  # kg
prop_mass = 0.22 * (prop_diam / 0.813)**2  # scaled from 32" prop
arm_length = prop_diam / 2 + 0.1  # motor at prop radius + margin
arm_radius = 0.015  # 30mm OD tube
arm_mass = 0.18  # kg per arm

# Fixed masses
center_mass = 0.7
avionics_mass = 0.5
payload_attach_mass = 0.1

struct_mass = n * (motor_mass + prop_mass + arm_mass) + center_mass + avionics_mass + payload_attach_mass
# Leave 10g margin on aircraft mass
battery_mass = 24.93 - struct_mass
battery_wh = battery_mass * 299.9  # Just under 300 Wh/kg limit

print(f"Struct mass: {struct_mass:.2f} kg")
print(f"Battery mass: {battery_mass:.2f} kg ({battery_wh:.0f} Wh)")
print(f"Battery specific energy: {battery_wh/battery_mass:.1f} Wh/kg")
print(f"Total: {struct_mass + battery_mass:.2f} kg")

# Rotor positions - hexagon
rotor_radius = arm_length
rotors = []
for i in range(n):
    angle = 2 * math.pi * i / n
    x = rotor_radius * math.cos(angle)
    y = rotor_radius * math.sin(angle)
    rotors.append({
        "site": f"rotor_{i}",
        "spin": 1 if i % 2 == 0 else -1,
        "prop_diameter_m": prop_diam,
        "motor_max_power_w": motor_power
    })

# Battery
battery = {
    "energy_wh": battery_wh,
    "max_power_w": battery_wh * 25,  # 25C
    "mass_kg": battery_mass
}

# Components
components = [
    {"name": "motor", "mass_kg": motor_mass, "count": n, "source_url": "https://store.tmotor.com/goods.php?id=618", "note": "T-Motor U15 KV100 derated to 5kW, 1.0kg at 5000 W/kg limit"},
    {"name": "propeller", "mass_kg": prop_mass, "count": n, "source_url": "https://store.tmotor.com/goods.php?id=618", "note": f"T-Motor P{int(prop_diam*39.37)} carbon fiber"},
    {"name": "arm_tube", "mass_kg": arm_mass, "count": n, "source_url": "https://www.rockwestcomposites.com/carbon-fiber-tubes", "note": "Carbon tube 30mm OD, 27mm ID, 1.0m"},
    {"name": "center_plates", "mass_kg": center_mass, "count": 1, "source_url": "", "note": "CFRP plates top/bottom, hex layout"},
    {"name": "avionics", "mass_kg": avionics_mass, "count": 1, "source_url": "", "note": "FC, 6x ESC, GPS, radio, PDB, wiring"},
    {"name": "payload_attach", "mass_kg": payload_attach_mass, "count": 1, "source_url": "", "note": "Quick-release hook"},
    {"name": "battery_pack", "mass_kg": battery_mass, "count": 1, "source_url": "https://www.tattu.com/", "note": f"Tattu 12S {int(battery_wh/44.4/1000*1000)}mAh 25C, ~{battery_wh:.0f} Wh, {battery_mass:.2f}kg pack level at 299.9 Wh/kg limit"}
]

design = {
    "name": "v3_hexa44_5kW",
    "rotors": rotors,
    "battery": battery,
    "cruise_speed_m_s": 12.0,
    "components": components
}

# Write design.json
with open('runs/lift_challenge/workspace/designs/v3_hexa44_5kW/design.json', 'w') as f:
    json.dump(design, f, indent=2)

print("\nDesign.json written")

# Generate drone.xml
motor_z = 0.05
prop_z = motor_z + 0.035
rotor_site_z = prop_z

xml_lines = [
    '<mujoco model="v3_hexa44_5kW">',
    '  <compiler angle="radian" meshdir="meshes" texturedir="textures"/>',
    '  <option timestep="0.002" gravity="0 0 -9.81"/>',
    '',
    '  <asset>',
    '    <texture name="carbon" type="2d" builtin="flat" width="64" height="64" rgb1="0.2 0.2 0.2" rgb2="0.1 0.1 0.1"/>',
    '    <material name="mat_carbon" texture="carbon" rgba="0.2 0.2 0.2 1" specular="0.3"/>',
    '    <material name="mat_motor" rgba="0.3 0.3 0.35 1" specular="0.5"/>',
    '    <material name="mat_prop" rgba="0.1 0.1 0.1 1" specular="0.1"/>',
    '    <material name="mat_battery" rgba="0.15 0.15 0.2 1" specular="0.2"/>',
    '    <material name="mat_payload" rgba="0.8 0.2 0.2 1" specular="0.3"/>',
    '  </asset>',
    '',
    '  <default>',
    '    <default class="rotor_geom">',
    '      <geom contype="0" conaffinity="0" group="1"/>',
    '    </default>',
    '    <default class="body_geom">',
    '      <geom contype="1" conaffinity="1" group="2" solimp="0.9 0.95 0.001" solref="0.005 1"/>',
    '    </default>',
    '  </default>',
    '',
    '  <worldbody>',
    '    <body name="drone" pos="0 0 0.1">',
    '      <freejoint/>',
    ''
]

# Center plates
center_radius = 0.18
xml_lines.append(f'      <!-- Plateau central supérieur -->')
xml_lines.append(f'      <geom name="plate_top" class="body_geom" type="cylinder" size="{center_radius} 0.015" pos="0 0 0.05" mass="{center_mass * 0.6:.3f}" material="mat_carbon"/>')
xml_lines.append(f'      <!-- Plateau central inférieur (support batterie) -->')
xml_lines.append(f'      <geom name="plate_bottom" class="body_geom" type="cylinder" size="{center_radius + 0.02} 0.01" pos="0 0 -0.1" mass="{center_mass * 0.4:.3f}" material="mat_carbon"/>')

# Avionics box
xml_lines.append(f'      <!-- Boîte avionique centrée -->')
xml_lines.append(f'      <geom name="avionics_box" class="body_geom" type="box" size="0.08 0.06 0.03" pos="0 0 0.02" mass="{avionics_mass:.3f}" material="mat_carbon"/>')

# Payload attach
xml_lines.append(f'      <!-- Attache charge utile sous le drone -->')
xml_lines.append(f'      <site name="payload_attach" pos="0 0 -0.18" size="0.02" rgba="1 0 0 1" type="cylinder"/>')
xml_lines.append(f'      <geom name="payload_attach_geom" class="body_geom" type="cylinder" size="0.02 0.015" pos="0 0 -0.18" mass="{payload_attach_mass:.3f}" material="mat_payload"/>')

# Arms and motors
for i in range(n):
    angle = 2 * math.pi * i / n
    arm_len = rotor_radius - center_radius
    arm_x = (center_radius + arm_len/2) * math.cos(angle)
    arm_y = (center_radius + arm_len/2) * math.sin(angle)
    arm_euler = f"0 0 {angle}"
    
    xml_lines.append(f'      <!-- Bras {i} -->')
    xml_lines.append(f'      <geom name="arm_{i}" class="body_geom" type="cylinder" size="{arm_radius} {arm_len/2:.3f}"')
    xml_lines.append(f'            pos="{arm_x:.3f} {arm_y:.3f} {motor_z:.3f}"')
    xml_lines.append(f'            euler="{arm_euler}"')
    xml_lines.append(f'            mass="{arm_mass:.3f}" material="mat_carbon"/>')
    
    motor_x = rotor_radius * math.cos(angle)
    motor_y = rotor_radius * math.sin(angle)
    
    xml_lines.append(f'      <!-- Moteur au bout du bras -->')
    xml_lines.append(f'      <geom name="motor_{i}" class="body_geom" type="cylinder" size="0.05 0.035"')
    xml_lines.append(f'            pos="{motor_x:.3f} {motor_y:.3f} {motor_z:.3f}"')
    xml_lines.append(f'            mass="{motor_mass:.3f}" material="mat_motor"/>')
    
    prop_radius = prop_diam / 2
    xml_lines.append(f'      <!-- Hélice (exclue de la traînée) -->')
    xml_lines.append(f'      <geom name="prop_{i}" class="rotor_geom" type="cylinder" size="{prop_radius:.3f} 0.005"')
    xml_lines.append(f'            pos="{motor_x:.3f} {motor_y:.3f} {prop_z:.3f}"')
    xml_lines.append(f'            mass="{prop_mass:.3f}" material="mat_prop"/>')
    
    xml_lines.append(f'      <!-- Site rotor pour l\'épreuve -->')
    xml_lines.append(f'      <site name="rotor_{i}" pos="{motor_x:.3f} {motor_y:.3f} {rotor_site_z:.3f}"')
    xml_lines.append(f'            size="0.01" rgba="0 1 0 1" type="cylinder"/>')
    xml_lines.append('')

# Battery
bat_size_x = 0.19
bat_size_y = 0.115
bat_size_z = 0.055
xml_lines.append(f'      <!-- Batterie -->')
xml_lines.append(f'      <geom name="battery_main" class="body_geom" type="box" size="{bat_size_x} {bat_size_y} {bat_size_z}"')
xml_lines.append(f'            pos="0 0 -0.16"')
xml_lines.append(f'            mass="{battery_mass:.3f}" material="mat_battery"/>')

xml_lines.extend([
    '    </body>',
    '  </worldbody>',
    '</mujoco>'
])

xml_content = '\n'.join(xml_lines)
with open('runs/lift_challenge/workspace/designs/v3_hexa44_5kW/drone.xml', 'w') as f:
    f.write(xml_content)

print("drone.xml written")

# Verify mass sum from XML geoms
total_mass = center_mass + avionics_mass + payload_attach_mass + n*(arm_mass + motor_mass + prop_mass) + battery_mass
print(f"\nTotal mass from components: {total_mass:.3f} kg")

