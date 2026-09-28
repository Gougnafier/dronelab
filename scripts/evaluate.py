#!/usr/bin/env python
"""Évalue un design sans LLM et affiche la ligne de résultat en JSON.

Exemples :
  python scripts/evaluate.py --reference
  python scripts/evaluate.py --params '{"thickness_mm": 4, "width_mm": 20, "rib": true, "rib_height_mm": 8, "rib_width_mm": 2, "material": "PLA-CF"}'
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from drone_agent.evaluate import evaluate  # noqa: E402
from drone_agent.spec import load_spec  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--params", help="paramètres JSON")
    source.add_argument("--params-file", type=Path, help="fichier JSON de paramètres")
    source.add_argument("--reference", action="store_true", help="bras de référence de la spec")
    parser.add_argument("--part", default="arm")
    parser.add_argument("--cycle", type=int)
    args = parser.parse_args()

    if args.reference:
        params = load_spec()["reference"]["params"]
    elif args.params_file:
        params = json.loads(args.params_file.read_text(encoding="utf-8"))
    else:
        params = json.loads(args.params)
    result = evaluate(args.part, params, cycle=args.cycle)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("valid") else 1


if __name__ == "__main__":
    raise SystemExit(main())
