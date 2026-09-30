#!/usr/bin/env bash
# Course propre : archive la course en cours, étiquette le laboratoire, écrit un manifeste et relance
# l'agent sur un espace de travail vide, en attente de la mission envoyée sur Discord.
#   ./scripts/start_clean_run.sh            (arrêt propre : attend la fin du cycle en cours)
#   ./scripts/start_clean_run.sh --now      (arrêt immédiat)
set -euo pipefail
cd "$(dirname "$0")/.."
PY="$HOME/miniconda3/envs/drone-agent/bin/python"
RUN=runs/lift_challenge
STAMP=$(date +%Y%m%d-%H%M)

if [ -n "$(git status --porcelain)" ]; then
  echo "Dépôt non propre : commiter d'abord, pour que la course soit rattachée à un état exact du laboratoire." >&2
  exit 1
fi

if systemctl --user is-active --quiet dronelab-agent; then
  if [ "${1:-}" = "--now" ]; then
    systemctl --user stop dronelab-agent
  else
    touch "$RUN/STOP"
    echo "Arrêt propre demandé : attente de la fin du cycle en cours…"
    while systemctl --user is-active --quiet dronelab-agent; do sleep 10; done
  fi
fi
rm -f "$RUN/STOP"

if [ -d "$RUN" ]; then
  mv "$RUN" "runs/lift_challenge-dev-$STAMP"
  echo "Course précédente archivée : runs/lift_challenge-dev-$STAMP"
fi
mkdir -p "$RUN"

N=$(git tag -l 'course-propre-*' | wc -l)
TAG="course-propre-$((N + 1))"
git tag -a "$TAG" -m "Laboratoire figé pour la course propre du $STAMP"
echo "Laboratoire étiqueté : $TAG"

"$PY" - "$TAG" <<'EOF'
import hashlib, json, subprocess, sys
from pathlib import Path
import yaml
tag = sys.argv[1]
repo = Path.cwd()
profiles = {}
for name in ("dronelab", "dronecheck", "dronescout", "dronedesk"):
    cfg = yaml.safe_load((Path.home() / ".hermes/profiles" / name / "config.yaml").read_text())
    profiles[name] = {"provider": cfg["model"].get("provider"), "model": cfg["model"].get("default")}
skills = {p.parent.name: hashlib.sha1(p.read_bytes()).hexdigest()[:10] for p in sorted((repo / "skills").glob("*/SKILL.md"))}
exam = yaml.safe_load((repo / "spec/lift_exam.yaml").read_text())
manifest = {"tag": tag, "commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
            "started_at": subprocess.check_output(["date", "-Iseconds"], text=True).strip(),
            "profiles": profiles, "exam_version": exam.get("version"), "skills": skills,
            "rules": "espace de travail vide ; seule entrée : la mission envoyée sur Discord ; interventions humaines journalisées"}
(repo / "runs/lift_challenge/manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
print("Manifeste écrit :", json.dumps(profiles, ensure_ascii=False))
EOF

./scripts/sync_5090.sh
"$PY" scripts/check_lab.py --before-launch || { echo "Contrôle du laboratoire en échec : course non lancée." >&2; exit 1; }
dronedesk gateway restart

CH=$(cat data/local/notify_target)
systemd-run --user --unit=dronelab-agent --property=Restart=on-failure --property=RestartSec=30 \
  --working-directory="$PWD" \
  --setenv=PATH="$HOME/.local/bin:$HOME/miniconda3/envs/drone-agent/bin:/usr/local/bin:/usr/bin:/bin" \
  --setenv=PYTHONUNBUFFERED=1 -- "$PY" scripts/run_agent.py --product lift_challenge --hermes-cmd dronelab \
  --auditor-cmd dronecheck --scout-cmd dronescout --scout-every 3 --notify "$CH" --report --max-turns 120 \
  --cycle-timeout 3600 --pause 5 --await-mission
echo "Course propre lancée ($TAG) : l'agent attend la mission dans #drone-lab."
