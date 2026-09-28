#!/usr/bin/env bash
# Copie le code du dépôt sur la RTX 5090 (WSL) : ~/drone-agent/repo. Le partage SMB n'étant pas monté
# en session SSH, le transfert passe par un flux tar.
set -euo pipefail
cd "$(dirname "$0")/.."
tar czf - --exclude=__pycache__ src scripts spec tests skills pyproject.toml environment.yml \
  | ssh -F data/local/ssh_config rtx5090 'wsl.exe -d Ubuntu -- bash -lc "mkdir -p ~/drone-agent/repo && cd ~/drone-agent/repo && tar xzf -"' 2>&1 \
  | grep -v "^wsl:" || true
echo "synchronisé"
