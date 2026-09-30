"""Outils de l'agent, indépendants du LLM : chaque fonction reçoit et renvoie du JSON, sans exception.

Deux rôles :
- engineer : l'ingénieur autonome (évaluer, explorer, écrire le cahier, proposer, répondre) ;
- desk : l'interlocuteur de l'utilisateur sur Discord (état, consignes, validations).
L'ingénieur ne peut pas valider ses propres propositions.
"""

from __future__ import annotations

import json
import os
import random
from pathlib import Path

from ..products import Product, get_product
from ..sampling import is_interval, sample_params
from ..tools.base import tool
from . import notify
from .workspace import Workspace

_CTX: dict = {}
ASK_USER_PER_DAY = 3
DISCORD_MAX_CHARS = 1900


def init(product: str, root=None) -> tuple[Product, Workspace]:
    ws = Workspace.open(product, root)
    os.environ["DRONE_AGENT_RUNS"] = str(ws.root)
    _CTX.update(product=get_product(product), ws=ws)
    return _CTX["product"], ws


def _p() -> Product:
    return _CTX["product"]


def _ws() -> Workspace:
    return _CTX["ws"]


def compact(line: dict) -> dict:
    """Vue courte d'une évaluation pour le contexte du modèle."""
    keys = ("cycle", "design_id", "score", "feasible", "violations", "params", "aircraft_mass_kg", "max_payload_kg",
            "payload_ratio", "limiting_factors", "checks_at_max", "arm_frequency", "mass_breakdown_kg",
            "geometry", "mass_g", "load_cases", "modal_hz", "manufacturable", "reason", "hypothesis", "source")
    out = {k: line[k] for k in keys if k in line}
    mission = line.get("mission")
    if isinstance(mission, dict):
        out["mission"] = {k: mission.get(k) for k in ("needed_wh", "usable_wh", "thrust_to_weight",
                                                      "peak_demand_kw", "battery_max_kw", "hover_tip_speed_m_s", "arm")}
        out["mission"]["time_s"] = (mission.get("mission") or {}).get("time_s")
    return out


def _evaluate(params: dict, tags: dict, edition: str | None = None, record: bool = True, overrides=None) -> dict:
    overrides = _ws().overrides() if overrides is None else overrides
    if record:
        return _p().evaluate(params, cycle=_ws().current_cycle(), overrides=overrides, tags=tags, edition=edition)
    from ..heavylift.evaluate import evaluate_vehicle  # analyse de sensibilité : produit rapide seulement
    return evaluate_vehicle.__wrapped__(params, edition, overrides)  # sans journal d'appel


def _best_row(design_id: str) -> dict | None:
    """Meilleure évaluation d'un design (plusieurs éditions ou hypothèses peuvent coexister)."""
    rows = [r for r in _ws().results() if r.get("design_id") == design_id and r.get("params")]
    return max(rows, key=lambda r: r.get("score") if r.get("score") is not None else -1e9) if rows else None


# --- ingénieur : comprendre ----------------------------------------------------------------------
@tool
def brief() -> dict:
    """Objectif, règles, contraintes, bornes des paramètres et hypothèses du modèle."""
    product = _p()
    return {"ok": True, "title": product.title, "score": product.score, **product.brief(_ws().overrides()),
            "model_paths": product.model_paths(), "skills": product.skills,
            "cycle": _ws().current_cycle()}


@tool
def best_designs(n: int = 5) -> dict:
    """Les n meilleurs designs évalués (un par design_id), score décroissant."""
    return {"ok": True, "designs": [compact(r) for r in _ws().best(min(int(n), 20))]}


@tool
def history(last: int = 20) -> dict:
    """Dernières évaluations : cycle, score, source, hypothèse et facteur limitant."""
    rows = _ws().results()[-min(int(last), 100):]
    return {"ok": True, "count": len(_ws().results()), "rows": [
        {k: r.get(k) for k in ("cycle", "design_id", "score", "feasible", "source", "hypothesis")} |
        {"limit": (r.get("limiting_factors") or r.get("violations") or [None])[0]} for r in rows]}


# --- ingénieur : essayer --------------------------------------------------------------------------
@tool
def evaluate_design(params: dict, hypothesis: str, edition: str | None = None) -> dict:
    """Évalue un design ; l'hypothèse testée est enregistrée avec le résultat."""
    line = _evaluate(params, {"source": "agent", "hypothesis": hypothesis}, edition)
    return {"ok": bool(line.get("valid", line.get("ok", True))), **compact(line)}


@tool
def random_designs(n: int = 20, seed: int | None = None, fixed: dict | None = None) -> dict:
    """Explore au hasard dans les bornes (paramètres de `fixed` imposés) ; renvoie les 5 meilleurs."""
    product = _p()
    budget = max(1, min(int(n), int(600 / product.seconds_per_evaluation), 500))
    rng = random.Random(seed)
    lines = []
    for _ in range(budget):
        params = {**sample_params(product.bounds(), rng), **(fixed or {})}
        lines.append(_evaluate(params, {"source": "random_designs"}))
    top = sorted((l for l in lines if l.get("score") is not None), key=lambda l: l["score"], reverse=True)[:5]
    return {"ok": True, "evaluated": len(lines), "feasible": sum(bool(l.get("feasible")) for l in lines),
            "top": [compact(l) for l in top]}


@tool
def optimize_local(start: dict, vary: list[str], budget: int = 150, hypothesis: str = "") -> dict:
    """Réglage fin (Nelder-Mead borné) des paramètres continus listés dans `vary`, depuis `start`."""
    from scipy.optimize import minimize

    product = _p()
    bounds = product.bounds()
    bad = [k for k in vary if k not in bounds or not is_interval(bounds[k])]
    if bad:
        return {"ok": False, "reason": f"paramètres non continus ou inconnus : {bad}"}
    budget = max(5, min(int(budget), int(900 / product.seconds_per_evaluation), 600))
    lo = [float(bounds[k][0]) for k in vary]
    hi = [float(bounds[k][1]) for k in vary]
    x0 = [min(max((float(start[k]) - a) / (b - a), 0.0), 1.0) for k, a, b in zip(vary, lo, hi)]
    trace = []

    def to_params(x):
        values = {k: a + min(max(v, 0.0), 1.0) * (b - a) for k, v, a, b in zip(vary, x, lo, hi)}
        return {**start, **{k: (round(v) if all(isinstance(e, int) for e in bounds[k]) else round(v, 3))
                            for k, v in values.items()}}

    def objective(x):
        line = _evaluate(to_params(x), {"source": "optimize_local", "hypothesis": hypothesis})
        score = line.get("score")
        trace.append(score)
        return -score if score is not None else 1e6

    simplex = [x0] + [[v + (0.1 if v <= 0.9 else -0.1) if j == i else v for j, v in enumerate(x0)]
                      for i in range(len(x0))]
    res = minimize(objective, x0, method="Nelder-Mead",
                   options={"maxfev": budget, "xatol": 1e-3, "fatol": 1e-4, "initial_simplex": simplex})
    best_params = to_params(res.x)
    final = _evaluate(best_params, {"source": "optimize_local", "hypothesis": hypothesis})
    finite = [t for t in trace if t is not None]
    return {"ok": True, "evaluations": len(trace) + 1, "start_score": finite[0] if finite else None,
            "best": compact(final), "score_trace_every_10": finite[::10]}


@tool
def sensitivity(params: dict, paths: list[str] | None = None, relative_change: float = 0.1) -> dict:
    """Effet sur le score d'une variation de ±x % de chaque hypothèse du modèle (sans enregistrer)."""
    product = _p()
    if product.seconds_per_evaluation > 1:
        return {"ok": False, "reason": "analyse de sensibilité réservée aux produits à évaluation rapide"}
    from ..heavylift.evaluate import lift_spec

    base_overrides = _ws().overrides()
    base = _evaluate(params, {}, record=False, overrides=base_overrides)
    if not base.get("ok", True) or base.get("score") is None:
        return {"ok": False, "reason": base.get("reason", "design non évaluable")}
    spec = lift_spec(base_overrides)
    effects = []
    for path in (paths or product.model_paths()):
        node = spec
        try:
            for key in path.split("."):
                node = node[key]
        except (KeyError, TypeError):
            effects.append({"path": path, "error": "chemin inconnu"})
            continue
        if not isinstance(node, (int, float)) or isinstance(node, bool):
            continue
        scores = []
        for sign in (-1, 1):
            trial = {**base_overrides, path: node * (1 + sign * relative_change)}
            scores.append(_evaluate(params, {}, record=False, overrides=trial).get("score"))
        effects.append({"path": path, "value": node, "score_minus": scores[0], "score_plus": scores[1],
                        "spread": round(abs((scores[1] or 0) - (scores[0] or 0)), 4)})
    effects.sort(key=lambda e: e.get("spread", 0), reverse=True)
    return {"ok": True, "base_score": base["score"], "relative_change": relative_change, "effects": effects[:15]}


@tool
def verify_arm_fem(design_id: str) -> dict:
    """Vérifie le bras d'un design par éléments finis (coques, Gmsh + CalculiX) sur la RTX 5090 et compare
    au modèle analytique : contrainte sous l'effort de dimensionnement, flèche, 1re fréquence. ~1 à 3 min."""
    from ..heavylift.evaluate import lift_spec
    from ..heavylift.model import Vehicle
    from ..remote import run_module
    from ..store import append_jsonl, now_iso

    if _p().name != "heavylift":
        return {"ok": False, "reason": "vérification disponible pour le produit heavylift"}
    row = _best_row(design_id)
    if row is None:
        return {"ok": False, "reason": f"design inconnu : {design_id}"}
    spec = lift_spec(_ws().overrides())
    vehicle = Vehicle(row["params"], spec)
    payload = row.get("max_payload_kg") or 0.0
    loaded = (vehicle.mass_kg + payload) * vehicle.g
    force = spec["margins"]["thrust_to_weight_min"] * loaded / vehicle.n_arms
    mat = spec["arm_material"]
    job = {"length_m": vehicle.arm_free_m, "od_mm": row["params"]["arm_od_mm"], "wall_mm": row["params"]["arm_wall_mm"],
           "young_gpa": mat["young_gpa"], "poisson": 0.3, "density_kg_m3": mat["density_kg_m3"],
           "strength_mpa": mat["strength_mpa"], "tip_force_n": [0.0, 0.0, force],
           "tip_mass_kg": vehicle.tip_mass_per_arm_kg}
    fem = run_module("drone_agent.fem.tube", job)
    e_pa, length, inertia = mat["young_gpa"] * 1e9, vehicle.arm_free_m, vehicle.arm_inertia_m4
    analytic = {"stress_root_mpa": round(force * length * (row["params"]["arm_od_mm"] / 2000) / inertia / 1e6, 2),
                "tip_deflection_mm": round(force * length**3 / (3 * e_pa * inertia) * 1000, 3),
                "f1_hz": vehicle.arm_frequency(payload)["f1_hz"]}
    result = {"ok": bool(fem.get("ok")), "design_id": design_id, "payload_kg": payload,
              "design_force_n": round(force, 1), "arm_length_m": round(length, 3), "fem": fem, "analytic": analytic,
              "note": "contrainte FEM hors d'une bande d'un diamètre aux extrémités ; effort et masse moteur répartis"}
    if fem.get("ok"):
        result["relative_gap"] = {
            "tip_deflection": round(fem["tip_deflection_mm"] / analytic["tip_deflection_mm"] - 1, 3),
            "f1": round(fem["f1_hz"] / analytic["f1_hz"] - 1, 3)}
        result["agreement"] = all(abs(v) < 0.1 for v in result["relative_gap"].values())
    append_jsonl(_ws().root / "verifications.jsonl", {"timestamp": now_iso(), "cycle": _ws().current_cycle(), **result})
    return result


# --- ingénieur : consigner ------------------------------------------------------------------------
def pending_audit() -> dict | None:
    """Dernier audit avec des points (réserves ou problème) auquel l'ingénieur n'a pas encore répondu."""
    ws = _ws()
    current = ws.current_cycle()
    audits = [a for a in ws.audits() if a.get("cycle", 0) < current and (a.get("issues") or a.get("verdict") != "ok")]
    if not audits:
        return None
    last = audits[-1]
    answered = {e.get("audit_cycle") for e in ws.notebook() if e.get("audit_response")}
    return None if last["cycle"] in answered else last


@tool
def notebook_write(hypothesis: str, tests: str, result: str, conclusion: str, next_step: str,
                   kind: str = "cycle", sources: list[str] | None = None, audit_response: str = "") -> dict:
    """Entrée du cahier de labo (obligatoire à chaque cycle). kind : cycle ou retrospective. audit_response :
    réponse point par point au dernier audit du vérificateur s'il a relevé des points (corrigé / contesté + preuve)."""
    audit = pending_audit()
    if audit and len(audit_response.strip()) < 40:
        return {"ok": False, "reason": f"réponds d'abord point par point à l'audit du cycle {audit['cycle']} "
                                       f"({audit['verdict']}) dans audit_response",
                "audit": {"summary": audit["summary"], "issues": audit.get("issues", [])}}
    entry = {"kind": kind, "hypothesis": hypothesis, "tests": tests, "result": result, "conclusion": conclusion,
             "next_step": next_step, "sources": sources or []}
    if audit:
        entry.update(audit_cycle=audit["cycle"], audit_response=audit_response)
    record = _ws().write_notebook(entry)
    return {"ok": True, "cycle": record["cycle"], "summary_due": _ws().summary_due()}


@tool
def notebook_read(last: int = 5) -> dict:
    """Résumé courant et dernières entrées du cahier de labo."""
    return {"ok": True, "summary": _ws().summary(), "entries": _ws().notebook(min(int(last), 30))}


@tool
def notebook_summary_write(text: str) -> dict:
    """Réécrit le résumé (15 lignes max) : pistes gagnantes, impasses, record, hypothèses à vérifier."""
    return _ws().set_summary(text)


# --- ingénieur : dialoguer ---------------------------------------------------------------------------
@tool
def user_inbox() -> dict:
    """Consignes de l'utilisateur non traitées et propositions de modèle en attente."""
    return {"ok": True, "pending": _ws().inbox(), "pending_proposals": _ws().proposals()}


@tool
def reply_to_user(message_id: str, response: str) -> dict:
    """Répond à une consigne de l'utilisateur et la marque traitée."""
    result = _ws().acknowledge(message_id, response)
    if result.get("ok"):
        notify.send(_ws().root, "reply", f"[{_p().name} · cycle {_ws().current_cycle()}] {response}")
    return result


@tool
def ask_user(question: str) -> dict:
    """Question non bloquante à l'utilisateur (3 par jour max) ; la réponse arrivera dans user_inbox."""
    from ..store import now_iso, read_jsonl

    today = now_iso()[:10]
    asked = [r for r in read_jsonl(_ws().root / "outbox.jsonl") if r["kind"] == "question" and r["timestamp"][:10] == today]
    if len(asked) >= ASK_USER_PER_DAY:
        return {"ok": False, "reason": "quota de questions du jour atteint ; continuer sans attendre"}
    notify.send(_ws().root, "question", f"❓ [{_p().name} · cycle {_ws().current_cycle()}] {question}")
    return {"ok": True, "note": "ne pas attendre la réponse : continuer le travail"}


@tool
def propose_model_update(path: str, value: float, source_url: str, excerpt: str, justification: str) -> dict:
    """Propose de remplacer une hypothèse du modèle par une valeur sourcée ; appliqué après validation."""
    if path not in _p().model_paths():
        return {"ok": False, "reason": "chemin inconnu ; voir brief().model_paths"}
    if not source_url.startswith(("http://", "https://")) or len(excerpt.strip()) < 20:
        return {"ok": False, "reason": "source URL et extrait (20 caractères min) obligatoires"}
    proposal = _ws().propose(path, value, source_url, excerpt, justification)
    notify.send(_ws().root, "proposal",
                f"📐 Proposition {proposal['id']} : {path} → {value}\nSource : {source_url}\n« {excerpt[:300]} »\n"
                f"Pourquoi : {justification[:400]}\nRépondre « valider {proposal['id']} » ou « refuser {proposal['id']} ».")
    return {"ok": True, "id": proposal["id"], "status": "pending"}


# --- rapports (génériques, tous produits) ----------------------------------------------------------------
def _field(row: dict, path: str):
    node = row
    for key in path.split("."):
        if not isinstance(node, dict) or key not in node:
            return None
        node = node[key]
    return node if isinstance(node, (int, float)) and not isinstance(node, bool) else None


def _numeric_paths(row: dict, prefix: str = "") -> list[str]:
    paths = []
    for key, value in row.items():
        path = f"{prefix}{key}"
        if isinstance(value, dict):
            paths += _numeric_paths(value, path + ".")
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            paths.append(path)
    return paths


@tool
def result_fields() -> dict:
    """Champs numériques disponibles dans les résultats (chemins pointés), utilisables par plot_results."""
    rows = [r for r in _ws().results() if r.get("valid", True)]
    if not rows:
        return {"ok": True, "fields": [], "note": "aucun résultat pour l'instant"}
    fields = sorted(set(_numeric_paths(rows[-1])) | set(_numeric_paths(rows[0])))
    return {"ok": True, "count": len(rows), "fields": fields}


@tool
def plot_results(x: str, y: str, title: str = "", only_feasible: bool = False,
                 reference_lines: list[dict] | None = None, highlight_best: bool = True) -> dict:
    """Nuage y en fonction de x sur toutes les évaluations (qualifiantes en couleur). reference_lines :
    [{"kind": "slope"|"x"|"y", "value": nombre, "label": texte}]. Renvoie le chemin du PNG."""
    from .report import _plt, _stamp

    rows = [r for r in _ws().results() if _field(r, x) is not None and _field(r, y) is not None]
    if only_feasible:
        rows = [r for r in rows if r.get("feasible")]
    if not rows:
        return {"ok": False, "reason": f"aucune évaluation avec {x} et {y} ; voir result_fields"}
    plt = _plt()
    fig, ax = plt.subplots(figsize=(7, 5), dpi=120)
    for feasible, color, label, size in ((False, "#8a8f98", "non qualifiant", 6), (True, "#0b6bcb", "qualifiant", 14)):
        pts = [r for r in rows if bool(r.get("feasible")) == feasible]
        if pts:
            ax.scatter([_field(r, x) for r in pts], [_field(r, y) for r in pts], s=size,
                       alpha=0.3 if not feasible else 0.9, color=color, label=label)
    if highlight_best:
        top = _ws().best(1)
        if top and _field(top[0], x) is not None and _field(top[0], y) is not None:
            ax.scatter([_field(top[0], x)], [_field(top[0], y)], s=120, marker="*", color="#d97706", label="record")
    xmax = max(_field(r, x) for r in rows)
    for line in reference_lines or []:
        kind, value, label = line.get("kind"), float(line.get("value", 0)), line.get("label", "")
        if kind == "slope":
            ax.plot([0, xmax], [0, value * xmax], ls=":", lw=0.8, color="#444", label=label or None)
        elif kind == "x":
            ax.axvline(value, color="#b91c1c", lw=0.8, label=label or None)
        elif kind == "y":
            ax.axhline(value, color="#b91c1c", lw=0.8, label=label or None)
    ax.set_xlabel(x)
    ax.set_ylabel(y)
    ax.set_title(title or f"{y} en fonction de {x}")
    ax.grid(alpha=0.2)
    ax.legend(fontsize=8)
    fig.tight_layout()
    folder = _ws().root / "reports"
    folder.mkdir(exist_ok=True)
    path = folder / f"{_stamp()}-{y}-vs-{x}.png".replace("/", "_")
    fig.savefig(path)
    plt.close(fig)
    return {"ok": True, "image": str(path), "points": len(rows)}


@tool
def plot_progress() -> dict:
    """Courbe du meilleur score par cycle, nuage des évaluations et rétrospectives. Renvoie le PNG."""
    from .report import _stamp, progress_chart

    folder = _ws().root / "reports"
    folder.mkdir(exist_ok=True)
    return {"ok": True, "image": str(progress_chart(_ws(), folder / f"{_stamp()}-progress.png"))}


@tool
def render_design(design_id: str = "", view: str = "iso") -> dict:
    """Maquette 3D d'un design (défaut : le record) : fichier OpenUSD + image rendue (Blender).
    view : iso, top ou side. ~30 s à 1 min. L'image peut être jointe à send_report ou à une réponse."""
    import json as _json
    import shutil
    import subprocess

    from ..heavylift.evaluate import lift_spec
    from ..heavylift.geometry import assembly, write_usda
    from ..heavylift.model import Vehicle
    from ..spec import REPO_ROOT
    from .report import _plt, _stamp

    if _p().name != "heavylift":
        return {"ok": False, "reason": "rendu 3D disponible pour le produit heavylift"}
    if view not in ("iso", "top", "side"):
        return {"ok": False, "reason": "view : iso, top ou side"}
    if not design_id:
        top = _ws().best(1)
        if not top:
            return {"ok": False, "reason": "aucun design évalué"}
        design_id = top[0]["design_id"]
    row = _best_row(design_id)
    if row is None:
        return {"ok": False, "reason": f"design inconnu : {design_id}"}
    vehicle = Vehicle(row["params"], lift_spec(_ws().overrides()))
    payload = row.get("max_payload_kg") or 0.0
    parts = assembly(vehicle, payload)
    folder = _ws().root / "designs" / design_id
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "parts.json").write_text(_json.dumps(parts), encoding="utf-8")
    meta = {"design_id": design_id, "aircraft_mass_kg": round(vehicle.mass_kg, 3), "payload_kg": payload,
            "score": row.get("score") or 0.0}
    usda = write_usda(parts, folder / f"{design_id}.usda", meta)
    raw = folder / f"render-{view}.png"
    blender = os.environ.get("BLENDER") or shutil.which("blender")
    if not blender:
        return {"ok": False, "reason": "Blender introuvable", "usda": str(usda)}
    proc = subprocess.run([blender, "-b", "--factory-startup", "--python", str(REPO_ROOT / "scripts" / "blender_render.py"),
                           "--", str(folder / "parts.json"), str(raw), view],
                          capture_output=True, text=True, timeout=600)
    if not raw.exists():
        return {"ok": False, "reason": "rendu échoué : " + (proc.stderr or proc.stdout)[-300:], "usda": str(usda)}
    plt = _plt()
    image = plt.imread(str(raw))
    fig = plt.figure(figsize=(image.shape[1] / 100, image.shape[0] / 100 + 0.6), dpi=100)
    ax = fig.add_axes([0, 0, 1, image.shape[0] / (image.shape[0] + 60)])
    ax.imshow(image)
    ax.axis("off")
    p = row["params"]
    fig.text(0.01, 0.985, f"{design_id} · {vehicle.n_arms} bras{' coaxiaux' if p['coaxial'] else ''} · hélices "
             f"{p['prop_diameter_in']:.0f} po · batterie {p['battery']} {p['battery_kg']:.1f} kg · envergure "
             f"{2 * vehicle.arm_center_m + vehicle.diameter_m:.2f} m", fontsize=12, va="top")
    fig.text(0.01, 0.955, f"aéronef {vehicle.mass_kg:.1f} kg · charge {payload:.1f} kg ({payload / 0.45359237:.0f} lb) "
             f"· ratio {payload / vehicle.mass_kg:.2f} · score {row.get('score')}", fontsize=12, va="top")
    reports = _ws().root / "reports"
    reports.mkdir(exist_ok=True)
    out = reports / f"{_stamp()}-render-{design_id}-{view}.png"
    fig.savefig(out)
    plt.close(fig)
    return {"ok": True, "image": str(out), "usda": str(usda), "parts": len(parts),
            "note": "maquette : volumes déduits des masses du modèle, pas des fichiers de fabricants"}


@tool
def send_report(text: str, images: list[str] | None = None) -> dict:
    """Envoie un rapport à l'utilisateur : texte + 4 fichiers max (images plot_*/render, vidéo video.mp4 d'une épreuve)."""
    allowed = [(_ws().root / "reports").resolve(), (_ws().root / "exams").resolve()]
    paths = []
    for image in (images or [])[:4]:
        path = Path(image).resolve()
        if not any(folder in path.parents for folder in allowed) or not path.exists():
            return {"ok": False, "reason": f"fichier hors des dossiers rapports/épreuves ou absent : {image}"}
        paths.append(str(path))
    if len(text.strip()) < 40:
        return {"ok": False, "reason": "rapport trop court"}
    if len(text) > DISCORD_MAX_CHARS:
        return {"ok": False, "reason": f"rapport trop long ({len(text)} caractères, {DISCORD_MAX_CHARS} max) : raccourcir"}
    record = notify.send(_ws().root, "report", text, paths)
    return {"ok": True, "delivered": record.get("delivered"), "images": len(paths)}


# --- desk : côté utilisateur -----------------------------------------------------------------------------
@tool
def status() -> dict:
    """État du projet : cycle, meilleurs designs, résumé, dernières entrées, attentes."""
    state = _ws().state()
    top = _ws().best(3)
    return {"ok": True, "product": _p().title, "cycle": state.get("cycle"), "evaluations": len(_ws().results()),
            "best": [compact(r) for r in top], "summary": _ws().summary(),
            "last_entries": _ws().notebook(3), "retrospectives": state.get("retrospectives", []),
            "pending_instructions": _ws().inbox(), "pending_proposals": _ws().proposals(),
            "audits": _ws().audits(3)}


@tool
def post_instruction(text: str) -> dict:
    """Transmet une consigne de l'utilisateur à l'ingénieur (lue au prochain cycle)."""
    return {"ok": True, **_ws().post_instruction(text)}


@tool
def decide_proposal(proposal_id: str, approve: bool, note: str = "") -> dict:
    """Validation par l'utilisateur d'un changement de modèle proposé par l'ingénieur."""
    return _ws().decide(proposal_id, bool(approve), note)


# --- épreuve simulée (produit lift_challenge) -------------------------------------------------------------
@tool
def check_design(design_dir: str) -> dict:
    """Contrôle rapide d'un dossier de conception (drone.xml + design.json) sans simulation : format, masses,
    poussée max par rotor, garde-fous de plausibilité. design_dir est relatif à l'espace de travail."""
    from ..lift import tools as lift

    return lift.check_design(_ws().root, design_dir)


@tool
def run_exam(design_dir: str, payload_kg: float, hypothesis: str, cruise_speed_m_s: float | None = None,
             scenario: str = "nominal") -> dict:
    """Fait passer l'épreuve simulée DARPA Lift (MuJoCo, sur la RTX 5090) avec la charge demandée. scenario :
    nominal (seul compté pour le score), vent (traversier 8 m/s), rafales, chaleur (38 °C, air moins dense),
    altitude (1 500 m). Renvoie verdict, statistiques par phase, température max des moteurs et exam_id ; la vidéo
    est produite pour l'utilisateur. 1 à 3 min."""
    from ..lift import tools as lift

    return lift.run_exam(_ws().root, design_dir, float(payload_kg), cruise_speed_m_s, _ws().current_cycle(),
                         hypothesis, scenario)


@tool
def exam_telemetry(exam_id: str, columns: list[str] | None = None, t_from: float = 0.0, t_to: float | None = None,
                   every_s: float = 5.0) -> dict:
    """Séries temporelles d'une épreuve (10 Hz à l'origine) : t, phase, x, y, z, vitesses, inclinaison, écart de
    trajectoire, poussée totale, poussée max relative, puissance, énergie, batterie, charge accrochée."""
    from ..lift import tools as lift

    return lift.exam_telemetry(_ws().root, exam_id, columns, float(t_from), t_to, float(every_s))


@tool
def exam_list(last: int = 10) -> dict:
    """Dernières épreuves passées : verdict, cause d'échec, ratio, hypothèse testée."""
    from ..lift import tools as lift

    return lift.exam_list(_ws().root, min(int(last), 50))


# --- atelier : catalogue, pièces sur mesure, assemblage (produit lift_challenge, épreuve v3) --------------------
@tool
def catalog_add(category: str, name: str, manufacturer: str, specs: dict, source_url: str, source_excerpt: str) -> dict:
    """Ajoute une pièce achetée au catalogue. La page source est ouverte et vérifiée (404 ou page d'accueil refusées).
    Catégories et spécifications requises : motor (mass_kg, max_continuous_power_w, diameter_m, height_m,
    mount_pattern_mm, option max_prop_diameter_m), propeller (mass_kg, diameter_m), battery (mass_kg, energy_wh,
    max_continuous_power_w, dims_m), esc (mass_kg, max_continuous_power_w, dims_m), tube (mass_per_m_kg,
    outer_diameter_m, wall_m, material), avionics (mass_kg, dims_m), wiring (mass_per_m_kg), landing_gear
    (mass_kg, dims_m), other (mass_kg, dims_m). dims_m = [longueur, largeur, hauteur]."""
    from ..lift import catalog

    return catalog.add(_ws().root, category, name, manufacturer, specs, source_url, source_excerpt)


@tool
def catalog_search(category: str | None = None, text: str | None = None) -> dict:
    """Pièces du catalogue (filtre par catégorie ou texte) avec spécifications et sources."""
    from ..lift import catalog

    rows = catalog.search(_ws().root, category, text)
    return {"ok": True, "count": len(rows), "entries": rows[:60]}


@tool
def materials_info() -> dict:
    """Matériaux (densité, module, résistance, conductivité, température max) et procédés (FDM, CNC : volume,
    paroi minimale, abattement de résistance) de l'atelier, et règles de dimensionnement."""
    from ..lift import parts

    return {"ok": True, **parts.materials()}


@tool
def part_build(name: str) -> dict:
    """Construit la pièce sur mesure workspace/parts/<name>/ (part.py : build(occ) en mm ; part.json : material,
    process, role, interfaces, load_cases, heat) : masse, fabrication, thermique, STEP/STL, image (image)."""
    from ..lift import parts

    return parts.build(_ws().root, name)


@tool
def part_fem(name: str, load_case: str) -> dict:
    """Calcul par éléments finis d'un cas de charge déclaré dans part.json (sur la RTX 5090) : contrainte de von Mises,
    déplacement, facteur de sécurité sur la résistance utile du matériau et du procédé. Requis avant l'assemblage."""
    from ..lift import parts

    return parts.fem(_ws().root, name, load_case)


@tool
def assembly_compile(name: str) -> dict:
    """Compile workspace/assemblies/<name>/assembly.json en dossier d'épreuve designs/<name>/ : masses calculées
    (catalogue + CAO), contrôles d'interfaces et de l'épreuve, OpenUSD et image. Seul chemin vers run_exam."""
    from ..lift import assembly

    return assembly.compile_assembly(_ws().root, name)


# --- vérificateur ------------------------------------------------------------------------------------------
@tool
def cycle_evidence(cycle: int) -> dict:
    """Tout ce que l'ingénieur a réellement fait pendant un cycle : entrées du cahier, appels d'outils avec leurs
    résultats (tronqués), épreuves passées. Sert à confronter ses affirmations aux preuves."""
    from ..store import read_jsonl

    cycle = int(cycle)
    calls = [c for c in read_jsonl(_ws().root / "calls.jsonl") if c.get("cycle") == cycle
             and c.get("tool") not in ("cycle_evidence", "record_audit")]
    slim = []
    for c in calls[-80:]:
        text = json.dumps({k: v for k, v in c.items() if k not in ("timestamp",)}, ensure_ascii=False)
        slim.append(text[:1500])
    return {"ok": True, "cycle": cycle, "notebook": [e for e in _ws().notebook() if e.get("cycle") == cycle],
            "tool_calls": slim, "tool_calls_total": len(calls),
            "results": [compact(r) for r in _ws().results() if r.get("cycle") == cycle][-20:],
            "note": "les recherches web et fichiers écrits par l'ingénieur ne sont pas dans ce journal : vérifier "
                    "les URL citées et les fichiers de l'espace de travail directement si besoin"}


@tool
def record_audit(cycle: int, verdict: str, summary: str, issues: list[dict] | None = None) -> dict:
    """Enregistre l'audit d'un cycle. verdict : « ok », « réserves » ou « problème ». issues : liste de
    {"claim": affirmation, "evidence": ce que disent les preuves, "severity": "faible"|"moyenne"|"forte"}."""
    if verdict not in ("ok", "réserves", "problème"):
        return {"ok": False, "reason": "verdict : ok, réserves ou problème"}
    record = _ws().record_audit(int(cycle), verdict, summary, issues or [])
    if verdict == "problème" or any(i.get("severity") == "forte" for i in issues or []):
        notify.send(_ws().root, "audit", f"🔎 Vérificateur · cycle {cycle} · {verdict}\n{summary[:1200]}")
    return {"ok": True, **record}


# --- éclaireur : veille terrain, essais demandés, revues de réalisme ------------------------------------------
@tool
def youtube_search(query: str, max_results: int = 8) -> dict:
    """Recherche de vidéos YouTube (sans clé d'API) : titre, chaîne, durée, vues, URL. Requêtes en anglais conseillées
    (« heavy lift drone motor failure », « octocopter vibration arm », « drone flight test wind »…)."""
    from ..research import youtube

    return {"ok": True, "results": youtube.search(query, max_results)}


@tool
def youtube_transcript(video: str, start_s: float = 0.0, max_chars: int = 12000) -> dict:
    """Transcription horodatée d'une vidéo (sous-titres, sinon transcription locale Whisper). Pagination par
    start_s / next_start_s. Citer les extraits avec l'URL et l'horodatage."""
    from ..research import youtube

    return youtube.transcript(video, _ws().root, float(start_s), min(int(max_chars), 20000))


@tool
def field_note_add(topic: str, problem: str, evidence_url: str, evidence_quote: str, design_impact: str,
                   recommended_test: str, severity: str, timestamp_s: float | None = None) -> dict:
    """Consigne un problème réel observé sur le terrain (vidéo, article, forum) : sujet (moteurs, thermique,
    vibrations, structure, batterie, aérodynamique, vent, commande, intégration…), preuve citée, conséquence pour la
    conception, essai recommandé, gravité (faible, moyenne, forte)."""
    if severity not in ("faible", "moyenne", "forte"):
        return {"ok": False, "reason": "gravité : faible, moyenne ou forte"}
    if not evidence_url.startswith(("http://", "https://")) or len(evidence_quote.strip()) < 20:
        return {"ok": False, "reason": "URL de la source et citation (20 caractères min) obligatoires"}
    note = _ws().add_field_note({"topic": topic, "problem": problem, "evidence_url": evidence_url,
                                 "evidence_quote": evidence_quote, "timestamp_s": timestamp_s,
                                 "design_impact": design_impact, "recommended_test": recommended_test,
                                 "severity": severity})
    return {"ok": True, "id": note["id"]}


@tool
def field_notes(topic: str | None = None, last: int = 40) -> dict:
    """Connaissances de terrain consignées par l'éclaireur (problèmes réels, preuves, essais recommandés)."""
    return {"ok": True, "notes": _ws().field_notes(topic, min(int(last), 100))}


@tool
def request_test(title: str, rationale: str, protocol: str, note_ids: list[str] | None = None) -> dict:
    """Demande à l'ingénieur un essai tiré du terrain (banc de vent, journée chaude, échauffement moteur,
    résonance, cas de charge de pièce…). Arrive dans sa boîte de consignes : il doit y répondre."""
    text = (f"🔭 Demande d'essai de l'éclaireur : {title}\nPourquoi : {rationale}\nProtocole : {protocol}"
            + (f"\nNotes de terrain : {', '.join(note_ids)}" if note_ids else ""))
    msg = _ws().post_instruction(text, author="éclaireur")
    from ..store import append_jsonl, now_iso

    append_jsonl(_ws().root / "test_requests.jsonl", {"id": msg["id"], "timestamp": now_iso(), "title": title,
                                                      "cycle": _ws().current_cycle(), "note_ids": note_ids or []})
    return {"ok": True, "message_id": msg["id"]}


@tool
def record_reality_review(verdict: str, summary: str, gaps: list[dict]) -> dict:
    """Revue de réalisme de la meilleure conception et de l'épreuve. verdict : réaliste, à renforcer, irréaliste.
    gaps : [{"aspect", "simulation" (ce que le modèle suppose), "reality" (ce que montre le terrain), "evidence"
    (URL, note), "severity" (faible, moyenne, forte), "action" : "essai" | "conception" | "épreuve"}]. Les écarts
    « épreuve » (limite de l'examen) sont soumis à l'équipe, seule habilitée à modifier l'épreuve."""
    if verdict not in ("réaliste", "à renforcer", "irréaliste"):
        return {"ok": False, "reason": "verdict : réaliste, à renforcer ou irréaliste"}
    review = _ws().record_reality_review({"verdict": verdict, "summary": summary, "gaps": gaps})
    exam_gaps = [g for g in gaps if g.get("action") == "épreuve"]
    if exam_gaps or verdict == "irréaliste":
        lines = [f"🔭 Revue de réalisme · cycle {review['cycle']} · {verdict}", summary[:600]]
        lines += [f"- limite de l'épreuve : {g.get('aspect')} — {g.get('reality', '')[:200]}" for g in exam_gaps[:5]]
        notify.send(_ws().root, "reality", "\n".join(lines)[:1900])
    return {"ok": True, "cycle": review["cycle"], "exam_gaps_sent_to_team": len(exam_gaps)}


@tool
def report_exam_limitation(aspect: str, exam_assumption: str, evidence: str, source_url: str, suggestion: str) -> dict:
    """Signale à l'équipe une hypothèse de l'épreuve qui semble irréaliste (ex. facteur de mérite des hélices,
    batterie à tension constante), avec une preuve sourcée. L'épreuve ne change que si l'équipe le décide ;
    continue ton travail avec l'épreuve actuelle."""
    if not source_url.startswith(("http://", "https://")) or len(evidence.strip()) < 20:
        return {"ok": False, "reason": "preuve (20 caractères min) et URL de la source obligatoires"}
    from ..store import append_jsonl, now_iso, read_jsonl

    path = _ws().root / "exam_limitations.jsonl"
    record = {"id": f"lim-{len(read_jsonl(path)) + 1:03d}", "timestamp": now_iso(), "cycle": _ws().current_cycle(),
              "aspect": aspect, "exam_assumption": exam_assumption, "evidence": evidence, "source_url": source_url,
              "suggestion": suggestion, "status": "à examiner par l'équipe"}
    append_jsonl(path, record)
    notify.send(_ws().root, "exam_limitation",
                f"🧪 Limite de l'épreuve signalée par l'ingénieur ({record['id']}, cycle {record['cycle']}) : {aspect}\n"
                f"Hypothèse de l'épreuve : {exam_assumption[:300]}\nPreuve : {evidence[:500]}\nSource : {source_url}\n"
                f"Suggestion : {suggestion[:300]}")
    return {"ok": True, "id": record["id"], "note": "transmis à l'équipe ; continuer avec l'épreuve actuelle"}


GENERIC_ENGINEER = [brief, best_designs, history, notebook_write, notebook_read, notebook_summary_write, user_inbox,
                    reply_to_user, ask_user, result_fields, plot_results, plot_progress, send_report]
GENERIC_DESK = [status, best_designs, history, notebook_read, post_instruction, decide_proposal, user_inbox,
                result_fields, plot_results, plot_progress]
GENERIC_AUDITOR = [brief, notebook_read, history, cycle_evidence, record_audit]
GENERIC_SCOUT = [brief, best_designs, history, notebook_read, youtube_search, youtube_transcript, field_note_add,
                 field_notes, request_test, record_reality_review]
PRODUCT_TOOLS = {
    "heavylift": {"engineer": [evaluate_design, random_designs, optimize_local, sensitivity, verify_arm_fem,
                               render_design, propose_model_update],
                  "desk": [render_design], "auditor": []},
    "lift_challenge": {"engineer": [materials_info, catalog_add, catalog_search, part_build, part_fem, assembly_compile,
                                    check_design, run_exam, exam_telemetry, exam_list, report_exam_limitation],
                       "desk": [exam_list, catalog_search, field_notes],
                       "auditor": [exam_telemetry, exam_list, check_design, catalog_search, materials_info],
                       "scout": [exam_list, exam_telemetry, check_design, catalog_search, materials_info]},
    "printed_arm": {"engineer": [evaluate_design, random_designs, optimize_local], "desk": [], "auditor": []},
}


def tools_for(role: str, product: str) -> list:
    generic = {"engineer": GENERIC_ENGINEER + [field_notes], "desk": GENERIC_DESK, "auditor": GENERIC_AUDITOR,
               "scout": GENERIC_SCOUT}[role]
    return generic + PRODUCT_TOOLS.get(product, {}).get(role, [])


ENGINEER_TOOLS = tools_for("engineer", "heavylift")  # compatibilité (tests du produit heavylift)
DESK_TOOLS = tools_for("desk", "heavylift")
