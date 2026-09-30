#!/usr/bin/env bash
# Rend les schémas Mermaid de docs/diagrams/*.mmd en SVG, noir sur fond blanc, dans docs/media/.
# Les images restent lisibles quel que soit le thème du lecteur, clair ou sombre.
# Prérequis : Node.js et @mermaid-js/mermaid-cli (licence MIT), par exemple :
#   npm install --prefix /tmp/mmdc @mermaid-js/mermaid-cli@11 && MMDC=/tmp/mmdc/node_modules/.bin/mmdc ./scripts/render_diagrams.sh
set -euo pipefail
cd "$(dirname "$0")/.."
MMDC="${MMDC:-mmdc}"
PUPPETEER_CONFIG=$(mktemp --suffix=.json)
trap 'rm -f "$PUPPETEER_CONFIG"' EXIT
CHROME="${CHROME:-$(ls -d "$HOME"/.cache/puppeteer/chrome/*/chrome-linux64/chrome 2>/dev/null | tail -1)}"
if [ -n "$CHROME" ]; then
  printf '{"executablePath": "%s", "args": ["--no-sandbox"]}\n' "$CHROME" > "$PUPPETEER_CONFIG"
else
  printf '{"args": ["--no-sandbox"]}\n' > "$PUPPETEER_CONFIG"
fi
for src in docs/diagrams/*.mmd; do
  name=$(basename "$src" .mmd)
  "$MMDC" -q -i "$src" -o "docs/media/diagram-$name.svg" -c docs/diagrams/mermaid-config.json -b white -p "$PUPPETEER_CONFIG"
  echo "docs/media/diagram-$name.svg"
done
