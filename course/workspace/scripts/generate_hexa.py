import json
import math
import os

def generate_hexa(d_inch, motor_w, design_name):
    """Generate drone.xml and design.json for hexacopter with given prop diameter and motor power"""
    n = 6
    R_prop = d_inch * 0.0254 / 2
    
    # Arm geometry
    center_plate_radius = 0.18
    motor_radius = 0.05
    motor_radius_from_center = center_plate_radius + 0.02 + R_prop + motor_radius
    arm_length = motor_radius_from_center - center_plate_radius
    
    # Component masses
    motor_mass = motor_w / 5000.0
    prop_mass = 0.416 * (d_inch / 44)**2.5
    arm_mass = 0.18 * (arm_length / 0.479)
    
    m_motors = n * motor_mass
    m_props = n * prop_mass
    m_arms = n * arm_mass
    m_struct_fixed = 0.7 + 0.5 + 0.1
    m_struct = m_motors + m_props + m_arms + m_struct_fixed
    m_battery = 24.94 - m_struct
    E_battery = m_battery * 299.9
    E_usable = E_battery * 0.9
    max_power_w = E_battery * 25
    
    rotors = []
    for i in range(n):
        angle = i * 2 * math.pi / n
        rotors.append({
            "site": f"rotor_{i}",
            "spin": 1 if i % 2 == 0 else -1,
            "prop_diameter_m": d_inch * 0.0254,
            "motor_max_power_w": motor_w
        })
    
    design = {
        "name": design_name,
        "rotors": rotors,
        "battery": {
            "energy_wh": E_battery,
            "max_power_w": max_power_w,
            "mass_kg": m_battery
        },
        "cruise_speed_m_s": 12.0,
        "components": [
            {"name": "motor", "mass_kg": motor_mass, "count": n, 
             "source_url": "https://store.tmotor.com/goods.php?id=618",
             "note": f"T-Motor U15 KV100 derated to {motor_w/1000:.0f}kW, {motor_mass:.2f}kg at 5000 W/kg limit"},
            {"name": "propeller", "mass_kg": prop_mass, "count": n,
             "source_url": "https://store.tmotor.com/goods.php?id=618",
             "note": f"T-Motor P{d_inch} carbon fiber, estimated"},
            {"name": "arm_tube", "mass_kg": arm_mass, "count": n,
             "source_url": "https://www.rockwestcomposites.com/carbon-fiber-tubes",
             "note": f"Carbon tube 30mm OD, 27mm ID, {arm_length:.2f}m"},
            {"name": "center_plates", "mass_kg": 0.7, "count": 1, "source_url": "", "note": "CFRP plates top/bottom, hex layout"},
            {"name": "avionics", "mass_kg": 0.5, "count": 1, "source_url": "", "note": "FC, 6x ESC, GPS, radio, PDB, wiring"},
            {"name": "payload_attach", "mass_kg": 0.1, "count": 1, "source_url": "", "note": "Quick-release hook"},
            {"name": "battery_pack", "mass_kg": m_battery, "count": 1, "source_url": "https://www.tattu.com/",
             "note": f"Tattu 12S high-capacity, ~{E_battery:.0f} Wh, {m_battery:.2f}kg pack level at 299.9 Wh/kg limit"}
        ]
    }
    
    xml_lines = [
        f'<mujoco model="{design_name}">',
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
        '',
        '      <!-- Plateau central supérieur -->',
        '      <geom name="plate_top" class="body_geom" type="cylinder" size="0.18 0.015" pos="0 0 0.05" mass="0.420" material="mat_carbon"/>',
        '      <!-- Plateau central inférieur (support batterie) -->',
        '      <geom name="plate_bottom" class="body_geom" type="cylinder" size="0.2 0.01" pos="0 0 -0.1" mass="0.280" material="mat_carbon"/>',
        '      <!-- Boîte avionique centrée -->',
        '      <geom name="avionics_box" class="body_geom" type="box" size="0.08 0.06 0.03" pos="0 0 0.02" mass="0.500" material="mat_carbon"/>',
        '      <!-- Attache charge utile sous le drone -->',
        '      <site name="payload_attach" pos="0 0 -0.18" size="0.02" rgba="1 0 0 1" type="cylinder"/>',
        '      <geom name="payload_attach_geom" class="body_geom" type="cylinder" size="0.02 0.015" pos="0 0 -0.18" mass="0.100" material="mat_payload"/>',
    ]
    
    for i in range(n):
        angle = i * 2 * math.pi / n
        x_arm = motor_radius_from_center * math.cos(angle)
        y_arm = motor_radius_from_center * math.sin(angle)
        arm_x = (center_plate_radius + arm_length/2) * math.cos(angle)
        arm_y = (center_plate_radius + arm_length/2) * math.sin(angle)
        
        xml_lines.append(f'      <!-- Bras {i} -->')
        xml_lines.append(f'      <geom name="arm_{i}" class="body_geom" type="cylinder" size="0.015 {arm_length/2:.3f}"')
        xml_lines.append(f'            pos="{arm_x:.3f} {arm_y:.3f} 0.050"')
        xml_lines.append(f'            euler="0 0 {angle:.6f}"')
        xml_lines.append(f'            mass="{arm_mass:.3f}" material="mat_carbon"/>')
        xml_lines.append(f'      <!-- Moteur au bout du bras -->')
        xml_lines.append(f'      <geom name="motor_{i}" class="body_geom" type="cylinder" size="0.05 0.035"')
        xml_lines.append(f'            pos="{x_arm:.3f} {y_arm:.3f} 0.050"')
        xml_lines.append(f'            mass="{motor_mass:.3f}" material="mat_motor"/>')
        xml_lines.append(f'      <!-- Hélice (exclue de la traînée) -->')
        xml_lines.append(f'      <geom name="prop_{i}" class="rotor_geom" type="cylinder" size="{R_prop:.3f} 0.005"')
        xml_lines.append(f'            pos="{x_arm:.3f} {y_arm:.3f} 0.085"')
        xml_lines.append(f'            mass="{prop_mass:.3f}" material="mat_prop"/>')
        xml_lines.append(f'      <!-- Site rotor pour l\'épreuve -->')
        xml_lines.append(f'      <site name="rotor_{i}" pos="{x_arm:.3f} {y_arm:.3f} 0.085"')
        xml_lines.append(f'            size="0.01" rgba="0 1 0 1" type="cylinder"/>')
        xml_lines.append('')
    
    xml_lines.append('      <!-- Batterie -->')
    xml_lines.append(f'      <geom name="battery_main" class="body_geom" type="box" size="0.19 0.115 0.055"')
    xml_lines.append(f'            pos="0 0 -0.16"')
    xml_lines.append(f'            mass="{m_battery:.3f}" material="mat_battery"/>')
    xml_lines.append('    </body>')
    xml_lines.append('  </worldbody>')
    xml_lines.append('</mujoco>')
    
    return '\n'.join(xml_lines), design, motor_mass, prop_mass, arm_mass, arm_length, m_struct, m_battery, E_battery

# Generate designs
for d_inch, motor_w, name in [
    (48, 5000, "v3_hexa48_5kW"),
    (50, 5000, "v3_hexa50_5kW"),
    (46, 7500, "v3_hexa46_7.5kW"),
    (48, 7500, "v3_hexa48_7.5kW"),
]:
    xml_content, design, m_motor, m_prop, m_arm, arm_len, m_struct, m_batt, E_batt = generate_hexa(d_inch, motor_w, name)
    
    os.makedirs(f"runs/lift_challenge/workspace/designs/{name}", exist_ok=True)
    
    with open(f"runs/lift_challenge/workspace/designs/{name}/drone.xml", "w") as f:
        f.write(xml_content)
    
    with open(f"runs/lift_challenge/workspace/designs/{name}/design.json", "w") as f:
        json.dump(design, f, indent=2)
    
    print(f"Generated {name}")
    print(f"  motor_mass={m_motor:.2f} kg each, prop_mass={m_prop:.3f} kg each")
    print(f"  arm_length={arm_len:.3f} m, arm_mass={m_arm:.3f} kg each")
    print(f"  struct={m_struct:.2f} kg, battery={m_batt:.2f} kg ({E_batt:.0f} Wh)")
    print()

