#!/usr/bin/env python
"""Évalue N bras tirés au hasard dans les bornes de la spec (bloc du dimanche, sans LLM).

Reprise : un design déjà calculé est relu depuis runs/designs/<id>/ au lieu d'être recalculé.

  python scripts/random_designs.py --n 20 --seed 0 --workers 6
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from drone_agent.evaluate import evaluate  # noqa: E402
from drone_agent.sampling import sample_params  # noqa: E402
from drone_agent.spec import load_spec  # noqa: E402
from drone_agent.store import runs_dir  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--n", type=int, default=20)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--summary", type=Path, help="fichier JSON de synthèse (défaut : runs/random_<seed>.json)")
    args = parser.parse_args()

    spec = load_spec()
    rng = random.Random(args.seed)
    designs = [sample_params(spec["parameters"], rng) for _ in range(args.n)]
    reference = evaluate("arm", spec["reference"]["params"], cycle=0)
    print(f"référence : {reference.get('design_id')} masse {reference.get('mass_g')} g "
          f"score {reference.get('score')} faisable {reference.get('feasible')}", flush=True)

    results = []
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(evaluate, "arm", p, i + 1): i for i, p in enumerate(designs)}
        for future in as_completed(futures):
            line = future.result()
            results.append(line)
            print(f"[{len(results):2d}/{args.n}] cycle {line['cycle']:2d} {line.get('design_id')} "
                  f"masse {line.get('mass_g')} g valide {line['valid']} faisable {line.get('feasible')} "
                  f"score {line.get('score')} ({line['seconds']} s) {line.get('reason') or ''}", flush=True)

    results.sort(key=lambda r: r["cycle"])
    summary = {
        "seed": args.seed,
        "n": args.n,
        "reference": reference,
        "valid": sum(r["valid"] for r in results),
        "feasible": sum(bool(r.get("feasible")) for r in results),
        "best": max((r for r in results if r.get("feasible")), key=lambda r: r["score"], default=None),
        "results": results,
    }
    path = args.summary or runs_dir() / f"random_{args.seed}.json"
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"valides {summary['valid']}/{args.n}, faisables {summary['feasible']}/{args.n}, synthèse : {path}")
    return 0 if summary["valid"] == args.n else 1


if __name__ == "__main__":
    raise SystemExit(main())
