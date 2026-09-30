#!/usr/bin/env python
"""Construit le rapport d'avancement (graphiques + résumé) ; --send l'envoie par Hermes.

  python scripts/report.py --product lift_challenge
  python scripts/report.py --product lift_challenge --send discord --hermes-cmd dronelab
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from drone_agent.agent import notify, report  # noqa: E402
from drone_agent.agent.workspace import Workspace  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--product", default="lift_challenge")
    parser.add_argument("--send", default="", help="cible Hermes send (ex. discord) ; vide = fichiers seulement")
    parser.add_argument("--hermes-cmd", default="dronelab")
    args = parser.parse_args()
    ws = Workspace.open(args.product)
    text, media = report.build(ws)
    print(text)
    print("\n".join(media))
    if args.send:
        os.environ["DRONE_AGENT_NOTIFY_TARGET"] = args.send
        os.environ["DRONE_AGENT_HERMES_CMD"] = args.hermes_cmd
        result = notify.send(ws.root, "report", text, media)
        print("envoyé" if result.get("delivered") else f"échec d'envoi : {result.get('error')}")
        return 0 if result.get("delivered") else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
