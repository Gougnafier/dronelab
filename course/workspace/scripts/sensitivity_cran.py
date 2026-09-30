"""Cran de charge max qui reste sous 1026 Wh pour FM abaisse (0.65 / 0.60).

Determine, par re-simulation locale, le cran (multiple de 2.5 lb) qui passe sous
chaque valeur de FM, toutes autres hypotheses egales. Repond au protocole eclaireur.
"""
import copy
import os
import sys
import time

REPO = "."
sys.path.insert(0, os.path.join(REPO, "src"))

from drone_agent.lift.exam import run_exam, exam_spec, load_package, load_assets

DESIGN_DIR = os.path.join(REPO, "runs/lift_challenge/workspace/designs/a2e_hexa_mn1118_stagger")
drone_xml, design = load_package(DESIGN_DIR)
assets = load_assets(DESIGN_DIR)

cases = [
    ("FM=0.65 @ 127.5lb", 57.84, {"figure_of_merit": 0.65}),
    ("FM=0.65 @ 122.5lb", 55.566, {"figure_of_merit": 0.65}),
    ("FM=0.60 @ 122.5lb", 55.566, {"figure_of_merit": 0.60}),
]

for label, payload, overrides in cases:
    spec = exam_spec()
    for k, v in overrides.items():
        spec["physics"][k] = v
    t0 = time.time()
    res = run_exam(drone_xml, design, payload, spec=spec, scenario="nominal", assets=assets)
    dt = time.time() - t0
    usable = res.get("battery_usable_wh", 1026.0)
    marge = 100 * (1 - res["energy_used_wh"] / usable) if usable else 0.0
    fail = (res.get("failure") or {}).get("reason", "-")
    print(f"{label}: payload={res['payload_kg']:.3f}kg({res['payload_lb']:.1f}lb) "
          f"passed={res['passed']} energy={res['energy_used_wh']:.1f}Wh marge={marge:.2f}% "
          f"t={dt:.0f}s fail={fail}")
    sys.stdout.flush()
print("DONE")
