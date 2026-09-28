"""Briques de rapport génériques (tous produits) et rapport de secours.

Le rapport normal est rédigé par l'agent lui-même (session de rapport, compétence progress-report,
outils plot_results / plot_progress / send_report). Ce module ne contient rien de propre à un produit."""

from __future__ import annotations

from pathlib import Path

from ..store import now_iso
from .workspace import Workspace


def _plt():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    return plt


def progress_chart(ws: Workspace, path: Path) -> Path:
    """Meilleur score par cycle, nuage des évaluations et rétrospectives."""
    plt = _plt()
    state = ws.state()
    fig, ax = plt.subplots(figsize=(9, 4.5), dpi=120)
    rows = [r for r in ws.results() if r.get("score") is not None and r.get("cycle") is not None]
    if rows:
        ax.scatter([r["cycle"] for r in rows], [max(r["score"], -1.0) for r in rows], s=6, alpha=0.25,
                   color="#8a8f98", label="évaluations (pénalités bornées à -1)")
    history = [(c, s) for c, s in state.get("best_history", []) if s is not None]
    if history:
        ax.step([c for c, _ in history], [s for _, s in history], where="post", color="#0b6bcb", lw=2,
                label="meilleur score")
    for i, retro in enumerate(state.get("retrospectives", [])):
        ax.axvline(retro["cycle"], color="#d97706", ls="--", lw=1, label="rétrospective" if i == 0 else None)
    ax.axhline(0, color="#444", lw=0.6)
    ax.set_xlabel("cycle")
    ax.set_ylabel("score (ratio charge / masse si qualifiant)")
    ax.set_title(f"{ws.product} · progression · {now_iso()[:16].replace('T', ' ')}")
    ax.legend(loc="lower right", fontsize=8)
    ax.grid(alpha=0.2)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return path


def summary_text(ws: Workspace) -> str:
    state = ws.state()
    best = ws.best(1)
    last = ws.notebook(1)
    lines = [f"📊 Rapport (secours) · {ws.product} · cycle {state.get('cycle', 0)} · {len(ws.results())} évaluations"]
    if best:
        b = best[0]
        limit = (b.get("limiting_factors") or b.get("violations") or ["—"])[0]
        lines.append(f"Meilleur : {b.get('design_id')} · score {b.get('score')} · qualifiant {b.get('feasible')} "
                     f"· limite {limit}")
    log = state.get("cycle_log", [])
    if log:
        ok = sum(c["success"] for c in log[-20:])
        lines.append(f"Derniers cycles réussis : {ok}/{min(len(log), 20)} · rétrospectives : "
                     f"{len(state.get('retrospectives', []))}")
    if last:
        lines.append(f"Dernière conclusion : {last[-1].get('conclusion', '')[:600]}")
        lines.append(f"Suite prévue : {last[-1].get('next_step', '')[:300]}")
    pending = ws.proposals()
    if pending:
        lines.append(f"Propositions à valider : {', '.join(p['id'] + ' ' + p['path'] for p in pending)}")
    return "\n".join(lines)


def _stamp() -> str:
    return now_iso()[:19].replace(":", "").replace("T", "-")


def build(ws: Workspace) -> tuple[str, list[str]]:
    """Rapport de secours, générique : utilisé seulement si la session de rapport de l'agent échoue."""
    folder = ws.root / "reports"
    folder.mkdir(exist_ok=True)
    return summary_text(ws), [str(progress_chart(ws, folder / f"{_stamp()}-progress.png"))]


def record_media(ws: Workspace) -> list[str]:
    """Graphique de progression + vidéo de l'épreuve du record, si le produit en produit une."""
    media = build(ws)[1]
    top = ws.best(1)
    if top and top[0].get("exam_id"):
        video = ws.root / "exams" / top[0]["exam_id"] / "video.mp4"
        if video.exists():
            media.append(str(video))
    return media
