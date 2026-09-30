"""Sensibilite de l'energie de mission du record a2e aux hypotheses de l'epreuve.

Re-simule localement (MuJoCo CPU) le parcours exam-0166 (127.5 lb) en faisant varier
une seule hypothese a la fois, toutes autres egales :
  - FM = 0.70 (reference) / 0.665 (-5 %) / 0.60 (hypothese basse eclaireur)
  - kappa = 1.2075 (+5 %) sur le facteur de puissance induite
  - eta = 0.8075 (-5 %) sur le rendement de chaine
Imprime energie, verdict, marge, et energie par phase. Analyse de sensibilite,
pas un resultat d'epreuve (run_exam fait foi).
"""
import copy
import os
import sys
import time

REPO = "."
sys.path.insert(0, os.path.join(REPO, "src"))

from drone_agent.lift.exam import run_exam, exam_spec, load_package, load_assets

DESIGN_DIR = os.path.join(REPO, "runs/lift_challenge/workspace/designs/a2e_hexa_mn1118_stagger")
PAYLOAD = 57.831  # 127.5 lb (au-dessus du seuil d'arrondi, applique 57.830 kg)

drone_xml, design = load_package(DESIGN_DIR)
assets = load_assets(DESIGN_DIR)

cases = [
    ("FM=0.70 ref", {"figure_of_merit": 0.70}),
    ("FM=0.665 -5%", {"figure_of_merit": 0.665}),
    ("FM=0.60 bas", {"figure_of_merit": 0.60}),
    ("kappa=1.2075 +5%", {"induced_power_factor": 1.2075}),
    ("eta=0.8075 -5%", {"powertrain_efficiency": 0.8075}),
]

for label, overrides in cases:
    spec = exam_spec()
    for k, v in overrides.items():
        spec["physics"][k] = v
    t0 = time.time()
    res = run_exam(drone_xml, design, PAYLOAD, spec=spec, scenario="nominal", assets=assets)
    dt = time.time() - t0
    usable = res.get("battery_usable_wh", 1026.0)
    marge = 100 * (1 - res["energy_used_wh"] / usable) if usable else 0.0
    fail = res.get("failure") or {}
    print(f"{label}: payload={res['payload_kg']:.3f}kg({res['payload_lb']:.1f}lb) "
          f"passed={res['passed']} energy={res['energy_used_wh']:.1f}Wh usable={usable:.1f} "
          f"marge={marge:.2f}% t={dt:.0f}s fail={fail.get('reason','-')}")
    for k, v in res.get("phases", {}).items():
        if v["energy_wh"] > 0:
            print(f"    {k}: {v['energy_wh']:.1f}Wh (max_throttle={v['max_throttle']:.3f})")
    sys.stdout.flush()
print("DONE")
