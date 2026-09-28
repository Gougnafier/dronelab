"""Exécution de calculs sur la machine RTX 5090 (WSL) par SSH, avec repli local.

Le code est synchronisé par scripts/sync_5090.sh dans ~/drone-agent/repo ; l'environnement de
calcul est ~/drone-agent/env. L'alias SSH est dans data/local/ssh_config (hors Git).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

from .spec import REPO_ROOT

SSH_CONFIG = REPO_ROOT / "data" / "local" / "ssh_config"
HOST = os.environ.get("DRONE_AGENT_REMOTE_HOST", "rtx5090")
REMOTE = ('wsl.exe -d Ubuntu -- bash -lc "cd ~/drone-agent/repo && PATH=~/drone-agent/env/bin:\\$PATH '
          'PYTHONPATH=src python -m {module}"')


def _parse(stdout: str) -> dict | None:
    for line in reversed(stdout.splitlines()):
        if line.startswith("RESULT_JSON "):
            return json.loads(line[len("RESULT_JSON "):])
    return None


def run_module(module: str, job: dict, timeout_s: float = 400) -> dict:
    """Lance `python -m module` (job JSON sur stdin) sur la 5090, sinon localement."""
    payload = json.dumps(job)
    if SSH_CONFIG.exists() and os.environ.get("DRONE_AGENT_REMOTE", "1") != "0":
        try:
            proc = subprocess.run(["ssh", "-F", str(SSH_CONFIG), HOST, REMOTE.format(module=module)],
                                  input=payload, capture_output=True, text=True, timeout=timeout_s)
            result = _parse(proc.stdout)
            if result is not None:
                return {**result, "ran_on": "rtx5090"}
            remote_error = (proc.stderr or proc.stdout)[-300:]
        except subprocess.TimeoutExpired:
            remote_error = f"timeout SSH après {timeout_s:.0f} s"
    else:
        remote_error = "SSH non configuré"
    proc = subprocess.run([sys.executable, "-m", module], input=payload, capture_output=True, text=True,
                          timeout=timeout_s, cwd=REPO_ROOT, env={**os.environ, "PYTHONPATH": str(REPO_ROOT / "src")})
    result = _parse(proc.stdout) or {"ok": False, "reason": (proc.stderr or proc.stdout)[-300:]}
    return {**result, "ran_on": "local", "remote_error": remote_error}
