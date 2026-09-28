"""Messages vers l'utilisateur : toujours journalisés dans outbox.jsonl, envoyés par `hermes send` si configuré.

Variables d'environnement :
  DRONE_AGENT_NOTIFY_TARGET  cible Hermes (ex. « discord » ou « discord:#drone-lab ») ; vide = journal seul
  DRONE_AGENT_HERMES_CMD     commande Hermes (défaut « hermes »), ex. l'alias d'un profil dédié
"""

from __future__ import annotations

import os
import shlex
import subprocess
from pathlib import Path

from ..store import append_jsonl, now_iso


def send(root: Path, kind: str, text: str, media: list[str] | None = None) -> dict:
    target = os.environ.get("DRONE_AGENT_NOTIFY_TARGET", "").strip()
    record = {"timestamp": now_iso(), "kind": kind, "text": text, "media": media or [], "target": target or None}
    if target:
        body = text + "".join(f"\nMEDIA:{Path(m).resolve()}" for m in (media or []))
        cmd = shlex.split(os.environ.get("DRONE_AGENT_HERMES_CMD", "hermes")) + ["send", "--to", target, "--quiet"]
        try:
            proc = subprocess.run(cmd, input=body, capture_output=True, text=True, timeout=60)
            record["delivered"] = proc.returncode == 0
            if proc.returncode != 0:
                record["error"] = (proc.stderr or proc.stdout)[-500:]
        except (OSError, subprocess.TimeoutExpired) as exc:
            record["delivered"], record["error"] = False, f"{type(exc).__name__}: {exc}"
    else:
        record["delivered"] = False
    append_jsonl(root / "outbox.jsonl", record)
    return record
