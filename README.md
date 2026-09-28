# Ingénieur produit autonome — NVIDIA Claw Agent Challenge 2026

Un agent qui mène seul, pendant des jours, un travail d’ingénieur : il formule des hypothèses, choisit ses essais, lance les calculs, tient un cahier de labo, remet en cause son propre modèle avec des sources, et rend compte sur Discord. Démonstration : dimensionner un multirotor lourd pour l’épreuve du [DARPA Lift Challenge](https://www.darpa.mil/research/challenges/lift) (aéronef < 55 lb, charge ≥ 110 lb sur 5 nmi, score = charge / masse).

**État (28 septembre 2026) :** premier cycle réel réussi (Hermes + Nemotron 3 Ultra + outils MCP du dépôt). Lancement continu à venir. Voir le [Kanban](docs/kanban.md).

## Architecture

- `src/drone_agent/agent/supervisor.py` : boucle codée en dur (contexte neuf par cycle, plateau → rétrospective, budget, reprise, alertes, rapports).
- `src/drone_agent/agent/mcp_server.py` et `toolbox.py` : outils exposés au LLM, rôles *engineer* et *desk*.
- `src/drone_agent/products.py` : produits disponibles (`heavylift`, `printed_arm`).
- `src/drone_agent/heavylift/` : modèle de mission et de dimensionnement ; `spec/darpa_lift.yaml` : règles et hypothèses.
- `src/drone_agent/cad`, `fem`, `tools` : bras imprimé paramétrique, Gmsh + CalculiX (plan B).
- `skills/` : compétences de méthode lues par l’agent.

## Installation

```bash
conda env create -f environment.yml
conda activate drone-agent
python -m pytest -q
```

Hermes : profil `dronelab` (modèle NVIDIA, serveur MCP `engineer`), voir [décisions](docs/decisions.md).

## Utilisation

```bash
python scripts/run_agent.py --product heavylift --hermes-cmd dronelab --max-cycles 1   # un cycle
python scripts/run_agent.py --product heavylift --hermes-cmd dronelab --notify discord --report   # en continu
python scripts/report.py --product heavylift                                            # rapport à la demande
touch runs/heavylift/STOP                                                               # arrêt propre
```

Fichiers du projet dans `runs/heavylift/` (hors Git) : `results.jsonl`, `notebook.md`, `notebook_summary.md`, `state.json`, `inbox.jsonl`, `proposals.jsonl`, `outbox.jsonl`, `reports/`, `llm/`.

Documents : [architecture](docs/architecture.md), [brainstorming](docs/brainstorming.md), [décisions](docs/decisions.md), [cahier des charges initial](docs/cahier-des-charges.md), [cadre du challenge](docs/challenge.md), [consignes](AGENTS.md).
