#!/usr/bin/env python
"""Chronologie des messages envoyés sur Discord pendant une course (outbox.jsonl), pour retrouver un message à l'écran.

  python scripts/discord_timeline.py --run runs/lift_challenge --since 2026-09-28T18:00 > docs/demo/chronologie-discord.md
Chaque ligne : heure d'envoi, cycle concerné, type, début du texte, pièces jointes.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

KINDS = {"record": "🏆 record", "audit": "🔎 vérificateur", "reality": "🔭 revue de réalisme", "exam_limitation": "🧪 limite de l'épreuve",
         "reply": "💬 réponse de l'ingénieur", "report": "📊 rapport", "blocked": "⚠️ alerte", "announcement": "📣 équipe"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run", type=Path, default=Path("runs/lift_challenge"))
    parser.add_argument("--since", default="", help="horodatage ISO de début, par exemple 2026-09-28T18:00")
    parser.add_argument("--width", type=int, default=160, help="longueur maximale de l'extrait de texte")
    args = parser.parse_args()
    lines = [json.loads(line) for line in (args.run / "outbox.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    lines = [m for m in lines if m.get("timestamp", "") >= args.since]
    print(f"# Messages Discord de la course `{args.run.name}`\n")
    print(f"Source : `{args.run}/outbox.jsonl` ({len(lines)} messages{f' depuis {args.since}' if args.since else ''}). "
          "Heure locale d'envoi ; le cycle est celui cité dans le message.\n")
    day = None
    for m in lines:
        stamp = m.get("timestamp", "")
        if stamp[:10] != day:
            day = stamp[:10]
            print(f"\n## {day}\n\n| Heure | Cycle | Type | Extrait | Pièces jointes |\n| --- | --- | --- | --- | --- |")
        text = " ".join((m.get("text") or "").split()).replace(str(REPO) + "/", "")
        cycle = re.search(r"cycle (\d+)", text)
        excerpt = text[: args.width].replace("|", "/") + ("…" if len(text) > args.width else "")
        media = ", ".join(Path(p).parent.name + "/" + Path(p).name if Path(p).name == "video.mp4" else Path(p).name for p in m.get("media") or [])
        print(f"| {stamp[11:16]} | {cycle.group(1) if cycle else ''} | {KINDS.get(m.get('kind'), m.get('kind'))} | {excerpt} | {media} |")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
