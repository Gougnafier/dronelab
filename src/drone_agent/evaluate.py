"""Évaluation complète sans LLM : génération -> fabricabilité -> 4 cas statiques -> modal -> score.

Score : masse_ref / masse si toutes les contraintes sont respectées (> 0, plus haut = plus léger),
sinon moins la somme des violations normalisées (< 0). Un design faisable bat toujours un infaisable.
"""

from __future__ import annotations

import time

from .fem.calculix import STATIC_CASES
from .spec import load_spec
from .store import append_jsonl, now_iso, runs_dir
from .tools.check_manufacturability import check_manufacturability
from .tools.generate_part import generate_part
from .tools.run_fem import run_fem, run_modal


def reference_mass_g() -> float | None:
    ref = load_spec()["reference"]
    result = generate_part(ref["part"], ref["params"])
    return result.get("mass_g") if result.get("valid") else None


def score_design(mass_g: float, manufacturing: dict, fem: dict, modal: dict, spec: dict, mass_ref: float) -> dict:
    limits = spec["constraints"]
    violations, penalty = [], 0.0
    if not manufacturing.get("manufacturable"):
        violations += manufacturing.get("violations", ["fabricabilité non vérifiée"])
        penalty += max(1, len(manufacturing.get("violations", [])))
    for case, res in fem.items():
        sf = res.get("sf")
        if sf is not None and sf < limits["safety_factor_min"]:
            violations.append(f"{case} : facteur de sécurité {sf} < {limits['safety_factor_min']}")
            penalty += (limits["safety_factor_min"] - sf) / limits["safety_factor_min"]
    deflection = fem.get("max_thrust", {}).get("deflection_mm")
    if deflection is not None and deflection > limits["tip_deflection_max_mm"]:
        violations.append(f"flèche {deflection} mm > {limits['tip_deflection_max_mm']} mm")
        penalty += (deflection - limits["tip_deflection_max_mm"]) / limits["tip_deflection_max_mm"]
    f1 = (modal.get("modal_hz") or [None])[0]
    if f1 is not None and f1 < limits["first_frequency_min_hz"]:
        violations.append(f"1re fréquence {f1} Hz < {limits['first_frequency_min_hz']} Hz")
        penalty += (limits["first_frequency_min_hz"] - f1) / limits["first_frequency_min_hz"]
    feasible = not violations
    score = round(mass_ref / mass_g, 4) if feasible else round(-penalty, 4)
    return {"feasible": feasible, "violations": violations, "score": score}


def evaluate(part: str, params: dict, cycle: int | None = None, record: bool = True) -> dict:
    """Évalue un design ; ne lève jamais d'exception ; ajoute une ligne à runs/results.jsonl."""
    start = time.monotonic()
    spec = load_spec()
    line = {"cycle": cycle, "design_id": None, "timestamp": now_iso(), "part": part, "params": params,
            "valid": False, "feasible": False, "score": None}
    try:
        _run_pipeline(part, params, spec, line)
    except Exception as exc:  # garde-fou : l'agent reçoit toujours une ligne lisible
        line.update(valid=False, feasible=False, score=None, reason=f"{type(exc).__name__}: {exc}")
    line["seconds"] = round(time.monotonic() - start, 1)
    if record:
        append_jsonl(runs_dir() / "results.jsonl", line)
    return line


def _run_pipeline(part: str, params: dict, spec: dict, line: dict) -> None:
    generated = generate_part(part, params)
    if generated.get("valid"):
        line.update(design_id=generated["design_id"], params=generated["params"], mass_g=generated["mass_g"],
                    bbox_mm=generated["bbox_mm"])
        design_id = generated["design_id"]
        manufacturing = check_manufacturability(design_id)
        fem = {case: run_fem(design_id, case) for case in STATIC_CASES}
        modal = run_modal(design_id)
        failures = [r for r in (manufacturing, *fem.values(), modal) if not r.get("valid")]
        line["manufacturable"] = manufacturing.get("manufacturable")
        line["load_cases"] = {
            case: {k: r.get(k) for k in ("sf", "von_mises_max_mpa", "deflection_mm") if r.get(k) is not None}
            | ({} if r.get("valid") else {"reason": r.get("reason")})
            for case, r in fem.items()
        }
        line["modal_hz"] = modal.get("modal_hz")
        mass_ref = reference_mass_g()
        if failures or not mass_ref:
            line["reason"] = "; ".join(f"{r.get('tool')}: {r.get('reason')}" for r in failures) or "masse de référence indisponible"
        else:
            line["valid"] = True
            line["reference_mass_g"] = mass_ref
            line.update(score_design(generated["mass_g"], manufacturing, fem, modal, spec, mass_ref))
    else:
        line["reason"] = generated.get("reason")
