"""Registre des produits : ce que le noyau de l'agent a besoin de savoir sur chaque problème.

Un produit fournit un brief (objectif, règles, contraintes, hypothèses de modèle), des bornes de
paramètres, une fonction d'évaluation sans LLM et la liste de ses compétences de test.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from pathlib import Path

from .spec import REPO_ROOT


@dataclass
class Product:
    name: str
    title: str
    goal: str
    score: str
    bounds: Callable[[], dict]
    brief: Callable[[dict], dict]
    evaluate: Callable[..., dict]
    model_paths: Callable[[], list[str]] = lambda: []
    skills: list[str] = field(default_factory=list)
    seconds_per_evaluation: float = 0.01


def _heavylift() -> Product:
    from .heavylift import evaluate as hl

    def brief(overrides: dict) -> dict:
        spec = hl.lift_spec(overrides)
        return {
            "product": "heavylift",
            "goal": "Maximiser charge max / masse de l'aéronef sur l'épreuve DARPA Lift.",
            "editions": spec["editions"],
            "default_edition": spec["default_edition"],
            "course": {"cruise_altitude_m": spec["cruise_altitude_m"], "payload_step_kg": spec["payload_step_kg"],
                       "mission": spec["mission"], "environment": spec["environment"]},
            "margins": spec["margins"],
            "parameters": spec["parameters"],
            "model_hypotheses": {k: spec[k] for k in ("propulsion", "mass_models", "batteries", "arm_material")},
            "approved_overrides": overrides,
            "sources": ["https://www.darpa.mil/research/challenges/lift",
                        "https://www.darpa.mil/research/challenges/lift/rules"],
            "notes": [
                "Les hypothèses de modèle sont provisoires ; les remplacer passe par propose_model_update "
                "avec une source, et la validation de l'utilisateur.",
                "Score > 0 : design qualifiant, égal au ratio charge/masse. Score < 0 : somme des écarts.",
            ],
        }

    def evaluate(params, cycle=None, overrides=None, tags=None, edition=None):
        return hl.evaluate(params, cycle=cycle, edition=edition, overrides=overrides, tags=tags)

    def model_paths() -> list[str]:
        spec = hl.lift_spec()
        paths = []
        for section in ("propulsion", "mass_models", "arm_material", "margins"):
            paths += [f"{section}.{k}" for k, v in spec[section].items() if isinstance(v, (int, float))]
        for chem, values in spec["batteries"].items():
            if isinstance(values, dict):
                paths += [f"batteries.{chem}.{k}" for k in values]
        return paths

    return Product(
        name="heavylift",
        title="Multirotor lourd — épreuve DARPA Lift",
        goal="Porter la plus grande charge possible par kilogramme d'aéronef sur le parcours DARPA Lift.",
        score="charge max / masse de l'aéronef si qualifiant, sinon pénalité négative",
        bounds=lambda: hl.lift_spec()["parameters"],
        brief=brief,
        evaluate=evaluate,
        model_paths=model_paths,
        skills=["engineering-cycle", "heavy-lift-testing", "component-research", "progress-report"],
        seconds_per_evaluation=0.003,
    )


def _printed_arm() -> Product:
    from .evaluate import evaluate as arm_evaluate
    from .spec import load_spec

    def brief(overrides: dict) -> dict:
        spec = load_spec()
        return {"product": "printed_arm", "goal": "Minimiser la masse du bras imprimé sous contraintes.",
                "constraints": spec["constraints"], "load_cases": spec["load_cases"],
                "parameters": spec["parameters"], "materials": spec["materials"],
                "interfaces": spec["interfaces"], "manufacturing": spec["manufacturing"]}

    def evaluate(params, cycle=None, overrides=None, tags=None, edition=None):
        line = arm_evaluate("arm", params, cycle=cycle)
        return {**(tags or {}), **line}

    return Product(
        name="printed_arm",
        title="Bras de quadricoptère 7 pouces imprimé",
        goal="Alléger le bras en respectant résistance, flèche, fréquence et fabricabilité.",
        score="masse de référence / masse si faisable, sinon pénalité négative",
        bounds=lambda: load_spec()["parameters"],
        brief=brief,
        evaluate=evaluate,
        skills=["engineering-cycle", "progress-report"],
        seconds_per_evaluation=60.0,
    )


DESIGN_FORMAT = """Épreuve v3 : un drone se construit en trois étapes, masses jamais déclarées à la main.
1. Catalogue des pièces achetées (catalog_add) : moteurs, hélices, batteries, variateurs, tubes, avionique, câblage,
   train ; chaque entrée avec une fiche produit précise, ouverte et vérifiée par l'outil.
2. Pièces sur mesure (workspace/parts/<nom>/ : part.py CAO en mm + part.json matériau, procédé, rôle, interfaces,
   cas de charge, chaleur) : part_build (masse, fabrication, thermique, image), part_fem (éléments finis sur la 5090).
3. Assemblage (workspace/assemblies/<nom>/assembly.json : instances catalog:/part:, tubes par fromto_m, rotors,
   connexions) : assembly_compile produit designs/<nom>/ (drone.xml, design.json signé, OpenUSD, image).
Seul un dossier compilé passe run_exam. Règles : hélices dégagées ou décalées en hauteur (pénalité selon le
recouvrement), masses minimales par famille, batterie par paliers, flexion des bras, poussée ≥ 1,6 × poids chargé.
L'épreuve impose sa physique et son pilote automatique : l'agent conçoit l'appareil, pas le pilote."""


def _lift_challenge() -> Product:
    from .lift.exam import exam_spec

    def brief(overrides: dict) -> dict:
        spec = exam_spec()
        workspace = REPO_ROOT / "runs" / "lift_challenge" / "workspace"
        return {
            "product": "lift_challenge",
            "goal": "Concevoir de zéro un multirotor qui réussit l'épreuve simulée DARPA Lift avec le meilleur ratio "
                    "charge / masse de l'aéronef.",
            "rules": spec["rules"], "mission": spec["mission"],
            "exam_version": spec.get("version", 1),
            "exam_physics": spec["physics"], "plausibility_gates": spec["plausibility"], "mass_floors": spec["mass_floors"],
            "structure_rules": spec["structure"], "failure_criteria": spec["failure"],
            "design_format": DESIGN_FORMAT,
            "workspace": str(workspace),
            "workshop": {
                "materials_and_processes": "materials_info()",
                "catalog_entries": len(__import__("drone_agent.lift.catalog", fromlist=["entries"]).entries(workspace.parent)),
                "parts": sorted(p.name for p in (workspace / "parts").glob("*") if p.is_dir()),
                "assemblies": sorted(p.name for p in (workspace / "assemblies").glob("*") if p.is_dir()),
            },
            "lab": {
                "python": str(Path.home() / "miniconda3/envs/drone-agent/bin/python"),
                "libraries": ["mujoco", "numpy", "scipy", "matplotlib", "gmsh", "calculix (ccx)"],
                "how": "écrire fichiers et scripts dans l'espace de travail avec tes outils de fichiers et de terminal ; "
                       "tu peux simuler toi-même avec mujoco pour des essais rapides, mais seul run_exam fait foi",
                "compute": "run_exam s'exécute sur la RTX 5090 par SSH ; la vidéo est produite pour l'utilisateur",
            },
            "sources": ["https://www.darpa.mil/research/challenges/lift/rules",
                        "https://mujoco.readthedocs.io/en/stable/XMLreference.html"],
            "score": "ratio charge/masse si le parcours est réussi avec une charge qualifiante (≥ 110 lb) et un aéronef "
                     "< 55 lb ; petit négatif si réussi sous 110 lb ; entre -1 et -0,1 selon l'avancement si échec ; "
                     "-1,5 si hors règlement ; -2 si dossier refusé",
        }

    return Product(
        name="lift_challenge",
        title="Défi DARPA Lift — conception de zéro, épreuve simulée",
        goal="Concevoir de zéro un multirotor qui réussit l'épreuve simulée DARPA Lift avec le meilleur ratio charge / masse.",
        score="ratio charge / masse d'un parcours réussi et qualifiant ; négatif sinon (voir brief)",
        bounds=lambda: {},
        brief=brief,
        evaluate=lambda *a, **k: {"ok": False, "reason": "utiliser run_exam"},
        skills=["engineering-cycle", "drone-from-scratch", "lift-exam", "assembly-design", "part-design",
                "component-research", "progress-report"],
        seconds_per_evaluation=120.0,
    )


FACTORIES = {"heavylift": _heavylift, "printed_arm": _printed_arm, "lift_challenge": _lift_challenge}


def get_product(name: str) -> Product:
    if name not in FACTORIES:
        raise KeyError(f"produit inconnu : {name} (disponibles : {sorted(FACTORIES)})")
    return FACTORIES[name]()


SKILLS_DIR = REPO_ROOT / "skills"
