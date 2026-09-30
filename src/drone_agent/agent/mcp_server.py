"""Serveur MCP (stdio) qui expose les outils de l'agent à Hermes.

  python -m drone_agent.agent.mcp_server --product lift_challenge --role engineer
  python -m drone_agent.agent.mcp_server --product lift_challenge --role desk
"""

from __future__ import annotations

import argparse
from pathlib import Path

from mcp.server.mcpserver import MCPServer

from . import toolbox

INSTRUCTIONS = {
    "engineer": "Outils de l'ingénieur produit autonome : comprendre le brief, évaluer des designs, explorer, "
                "régler finement, analyser la sensibilité du modèle, tenir le cahier de labo, répondre à "
                "l'utilisateur et proposer des changements de modèle sourcés.",
    "desk": "Outils de l'interlocuteur de l'utilisateur : état du projet, meilleurs designs, cahier de labo, "
            "transmission de consignes à l'ingénieur, validation ou refus des propositions de modèle.",
    "scout": "Outils de l'éclaireur : veille terrain (YouTube, web), base de problèmes réels, demandes d'essais à "
             "l'ingénieur et revues de réalisme de ses conceptions face au monde réel.",
    "auditor": "Outils du vérificateur indépendant : preuves de chaque cycle (appels d'outils, résultats, épreuves, "
               "télémétrie) pour confronter les affirmations de l'ingénieur, et enregistrement de l'audit.",
}


def build(product: str, role: str, root: Path | None = None) -> MCPServer:
    toolbox.init(product, root)
    server = MCPServer(name=f"engineer-{product}-{role}", instructions=INSTRUCTIONS[role])
    for fn in toolbox.tools_for(role, product):
        server.add_tool(fn)
    return server


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--product", default="lift_challenge")
    parser.add_argument("--role", choices=["engineer", "desk", "auditor", "scout"], default="engineer")
    parser.add_argument("--root", type=Path, help="dossier du projet (défaut : runs/<produit>)")
    args = parser.parse_args()
    build(args.product, args.role, args.root).run("stdio")


if __name__ == "__main__":
    main()
