#!/usr/bin/env bash
# Passe l'ingénieur (dronelab) et l'interlocuteur Discord (dronedesk) sur OpenAI (compte ChatGPT, fournisseur
# openai-codex) ; le vérificateur (dronecheck) reste sur un modèle NVIDIA d'une autre famille.
# Prérequis, une fois par profil (connexion dans le navigateur) :
#   dronelab auth add openai-codex --type oauth
#   dronedesk auth add openai-codex --type oauth
set -euo pipefail
cd "$(dirname "$0")/.."
MODEL="${1:-gpt-5.6-sol}"

for profile in dronelab dronedesk; do
  if ! "$profile" auth list 2>/dev/null | grep -q "openai-codex"; then
    echo "Profil $profile : pas de connexion OpenAI. Lancer : $profile auth add openai-codex --type oauth" >&2
    exit 1
  fi
done

for profile in dronelab dronedesk; do
  "$profile" config set model.provider openai-codex
  "$profile" config set model.default "$MODEL"
  "$profile" config set model.base_url https://chatgpt.com/backend-api/codex
done

systemctl --user restart dronelab-agent 2>/dev/null || echo "service dronelab-agent non lancé : utiliser scripts/run_agent.py"
dronedesk gateway restart
echo "OpenAI ($MODEL) actif pour dronelab et dronedesk ; dronecheck reste sur NVIDIA."
