#!/usr/bin/env python
"""Exporte dans le dépôt les traces lisibles d'une course (runs/ reste hors Git) : cahier de labo, audits,
notes de terrain, catalogue, pièces (script CAO, STEP, calculs), assemblages, scripts de l'agent, résumés des vols.

  python scripts/export_run.py --run runs/lift_challenge --out course
Les chemins absolus de la machine sont remplacés par des chemins relatifs au dépôt. Exclus : journaux bruts
des modèles (llm/), maillages, vidéos et télémétrie complète (trop volumineux).
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
FILES = ["notebook.md", "notebook_summary.md", "notebook.jsonl", "audits.jsonl", "field_notes.jsonl", "catalog.jsonl",
         "results.jsonl", "results-exam-v1.jsonl", "exam_limitations.jsonl", "reality_reviews.jsonl", "test_requests.jsonl",
         "inbox.jsonl", "outbox.jsonl", "calls.jsonl", "state.json"]
PATTERNS = ["workspace/parts/*/part.py", "workspace/parts/*/part.json", "workspace/parts/*/build.json",
            "workspace/parts/*/fem-*.json", "workspace/parts/*/view.png", "workspace/parts/*/part.step",
            "workspace/assemblies/*/assembly.json", "workspace/designs/*/compile.json", "workspace/designs/*/design.json",
            "workspace/designs/*/view.png", "workspace/scripts/*.py", "exams/*/summary.json"]
TEXT = {".md", ".json", ".jsonl", ".py"}


def clean(text: str) -> str:
    text = text.replace(str(REPO) + "/", "").replace(str(REPO), ".")
    text = text.replace(str(Path.home()), "~")
    # Chemins tronqués ou abrégés dans les journaux : on retire le préfixe propre à la machine.
    return re.sub(r"/" + re.escape(REPO.parts[1]) + r"[^\s\"'\\]*", "…", text)


def light_call(line: str) -> str:
    """calls.jsonl allégé : outil, cycle, horodatage, durée, succès et début des arguments."""
    try:
        row = json.loads(line)
    except json.JSONDecodeError:
        return ""
    args = json.dumps({"args": row.get("args"), "kwargs": row.get("kwargs")}, ensure_ascii=False)
    keep = {k: row.get(k) for k in ("timestamp", "cycle", "tool", "ok", "seconds")}
    keep["arguments"] = args[:300]
    return json.dumps(keep, ensure_ascii=False)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run", type=Path, default=Path("runs/lift_challenge"))
    parser.add_argument("--out", type=Path, default=Path("course"))
    args = parser.parse_args()
    run, out = args.run.resolve(), args.out
    sources = [run / name for name in FILES if (run / name).exists()]
    for pattern in PATTERNS:
        sources += sorted(run.glob(pattern))
    count, size = 0, 0
    for src in sources:
        target = out / src.relative_to(run)
        target.parent.mkdir(parents=True, exist_ok=True)
        if src.name == "calls.jsonl":
            lines = (light_call(line) for line in src.read_text(encoding="utf-8").splitlines())
            target.write_text(clean("\n".join(line for line in lines if line)) + "\n", encoding="utf-8")
        elif src.suffix in TEXT:
            target.write_text(clean(src.read_text(encoding="utf-8", errors="replace")), encoding="utf-8")
        else:
            shutil.copy(src, target)
        count += 1
        size += target.stat().st_size
    print(f"{count} fichiers, {size / 1e6:.1f} Mo dans {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
