#!/usr/bin/env bash
# Ingénieur (dronelab) et interlocuteur Discord (dronedesk) sur l'API DeepSeek directe ; le vérificateur
# (dronecheck) sur un modèle NVIDIA d'une autre famille (Nemotron), pour une vérification indépendante.
# La clé est saisie masquée et écrite seulement dans le .env des deux profils (hors dépôt, droits 600).
set -euo pipefail
cd "$(dirname "$0")/.."
ENGINEER_MODEL="${ENGINEER_MODEL:-deepseek-v4-pro}"
DESK_MODEL="${DESK_MODEL:-deepseek-v4-flash}"

read -r -s -p "Clé API DeepSeek (saisie masquée) : " KEY
echo
if [ -z "$KEY" ]; then echo "Clé vide, rien n'est modifié." >&2; exit 1; fi

for profile in dronelab dronedesk; do
  env_file="$HOME/.hermes/profiles/$profile/.env"
  touch "$env_file"
  chmod 600 "$env_file"
  grep -v '^DEEPSEEK_API_KEY=' "$env_file" > "$env_file.tmp" || true
  printf 'DEEPSEEK_API_KEY=%s\n' "$KEY" >> "$env_file.tmp"
  mv "$env_file.tmp" "$env_file"
  chmod 600 "$env_file"
done
unset KEY

set_model() {  # profil fournisseur modèle url
  "$1" config set model.provider "$2" >/dev/null
  "$1" config set model.default "$3" >/dev/null
  "$1" config set model.base_url "$4" >/dev/null
  echo "$1 -> $2 / $3"
}
set_model dronelab deepseek "$ENGINEER_MODEL" https://api.deepseek.com/v1
set_model dronedesk deepseek "$DESK_MODEL" https://api.deepseek.com/v1
set_model dronecheck nvidia nvidia/nemotron-3-ultra-550b-a55b https://integrate.api.nvidia.com/v1

echo "Test de connexion (ingénieur)…"
if ! timeout 180 dronelab chat -q "Réponds uniquement : OK" -Q --source tool --max-turns 1 2>&1 | tail -3 | grep -q "OK"; then
  echo "La connexion DeepSeek ne répond pas comme attendu : vérifier la clé et le solde du compte." >&2
  exit 1
fi

systemctl --user restart dronelab-agent 2>/dev/null || echo "service dronelab-agent non lancé : utiliser scripts/run_agent.py"
dronedesk gateway restart
echo "DeepSeek actif pour l'ingénieur ($ENGINEER_MODEL) et le bot Discord ($DESK_MODEL) ; vérificateur sur Nemotron (NVIDIA)."
