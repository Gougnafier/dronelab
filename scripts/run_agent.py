#!/usr/bin/env python
"""Lance l'ingénieur autonome : superviseur + sessions Hermes (profil dédié) + serveur MCP du dépôt.

  python scripts/run_agent.py --product heavylift --hermes-cmd dronelab --max-cycles 1
  python scripts/run_agent.py --product heavylift --hermes-cmd dronelab --notify discord   # en continu

Arrêt propre : créer runs/<produit>/STOP. Reprise : relancer la même commande.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from drone_agent.agent.supervisor import Config, Supervisor  # noqa: E402
from drone_agent.products import get_product  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--product", default="heavylift")
    parser.add_argument("--hermes-cmd", default="dronelab", help="commande Hermes (alias du profil)")
    parser.add_argument("--max-cycles", type=int)
    parser.add_argument("--max-cycles-per-day", type=int, default=0, help="0 = aucune limite")
    parser.add_argument("--max-turns", type=int, default=60)
    parser.add_argument("--cycle-timeout", type=int, default=1800)
    parser.add_argument("--pause", type=int, default=5)
    parser.add_argument("--notify", default="", help="cible Hermes send, ex. discord ; vide = journal seul")
    parser.add_argument("--report", action="store_true", help="joindre les graphiques aux notifications de record")
    parser.add_argument("--report-now", action="store_true", help="rapport rédigé par l'agent dès le démarrage")
    parser.add_argument("--auditor-cmd", default="", help="profil Hermes du vérificateur (ex. dronecheck) ; vide = sans audit")
    parser.add_argument("--scout-cmd", default="", help="profil Hermes de l'éclaireur (ex. dronescout) ; vide = sans veille")
    parser.add_argument("--scout-every", type=int, default=3, help="une session d'éclaireur tous les N cycles réussis")
    args = parser.parse_args()

    os.environ["DRONE_AGENT_NOTIFY_TARGET"] = args.notify
    os.environ["DRONE_AGENT_HERMES_CMD"] = args.hermes_cmd
    product = get_product(args.product)
    reporter = None
    if args.report:
        from drone_agent.agent.report import record_media

        reporter = record_media
    config = Config(product=args.product, hermes_cmd=args.hermes_cmd, skills=tuple(product.skills),
                    max_turns=args.max_turns, cycle_timeout_s=args.cycle_timeout, pause_s=args.pause,
                    max_cycles=args.max_cycles, max_cycles_per_day=args.max_cycles_per_day or None,
                    report_now=args.report_now, auditor_cmd=args.auditor_cmd or None,
                    scout_cmd=args.scout_cmd or None, scout_every=args.scout_every)
    Supervisor(config, reporter=reporter).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
