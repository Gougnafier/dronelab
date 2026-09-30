#!/usr/bin/env python
"""Tableau de bord autonome (HTML) d'une course, construit uniquement à partir de ses fichiers.

  python scripts/highlights.py --run runs/lift_challenge   (produit timeline.json et le graphique)
  python scripts/dashboard.py --run runs/lift_challenge [--annotations docs/demo/corrections-lift_challenge.json]
Sortie : <run>/dashboard/index.html et media/ (vidéos en WebM VP9 avec repli MP4, images citées,
graphique de progression où chaque correction de réalisme est marquée d'une barre verticale).
"""

from __future__ import annotations

import argparse
import html
import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

KIND_COLORS = {"équipe": "#3D8BD9", "limite": "#8B6FD0", "réalisme": "#E07B2E", "audit": "#B25A12"}


def rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return out


def esc(value) -> str:
    return html.escape(str(value if value is not None else "—"))


CSS = """
:root{--bg:#f6f7f9;--card:#fff;--ink:#16202c;--muted:#5b6776;--line:#dde2e8;--accent:#1f6feb;--ok:#1a7f4b;--warn:#b76e00;--bad:#c0392b}
@media (prefers-color-scheme:dark){:root{--bg:#0f141b;--card:#171e27;--ink:#e6ebf1;--muted:#98a4b3;--line:#2a3441;--accent:#5aa2ff;--ok:#4cc38a;--warn:#e8a33d;--bad:#ef6b5e}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,-apple-system,Segoe UI,sans-serif}
main{max-width:1100px;margin:0 auto;padding:24px 16px 64px}h1{font-size:28px;margin:0 0 6px}h2{font-size:19px;margin:36px 0 12px}
.muted{color:var(--muted)}.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-top:18px}
.tile{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 14px}.tile b{display:block;font-size:24px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:14px}.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px}
.card img,.card video{width:100%;border-radius:6px;display:block;background:#000}.tag{display:inline-block;font-size:12px;padding:1px 8px;border-radius:99px;border:1px solid var(--line);margin-right:6px}
.ok{color:var(--ok)}.warn{color:var(--warn)}.bad{color:var(--bad)}ol.timeline{padding-left:18px}ol.timeline li{margin:0 0 14px}
table{width:100%;border-collapse:collapse;font-size:14px}td,th{border-bottom:1px solid var(--line);padding:6px 4px;text-align:left;vertical-align:top}
a{color:var(--accent)}blockquote{margin:6px 0;padding-left:10px;border-left:3px solid var(--line);color:var(--muted)}
"""


def design_stem(design_id: str | None) -> str:
    return (design_id or "").rsplit("-", 1)[0]


def progress_story(run: Path, annotations: dict, target: Path) -> bool:
    """Ratio de chaque vol par cycle, record du design en cours et barres des corrections annotées."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    results = [r for r in rows(run / "results.jsonl") if r.get("payload_ratio") is not None]
    if not results:
        return False
    state = json.loads((run / "state.json").read_text()) if (run / "state.json").exists() else {}
    last_cycle = max([r["cycle"] for r in results] + [state.get("cycle") or 0])
    before = [r for r in rows(run / "results-exam-v1.jsonl") if r.get("passed") and (r.get("score") or 0) > 0]
    fig = plt.figure(figsize=(14, 8), dpi=140)
    grid = fig.add_gridspec(2, 2 if before else 1, width_ratios=[1, 3] if before else [1], height_ratios=[5, 1.5], hspace=0.42, wspace=0.12)
    ax = fig.add_subplot(grid[0, -1])
    ax.set_ylabel("ratio charge / masse de l'aéronef")
    if before:
        left = fig.add_subplot(grid[0, 0])
        record = max(before, key=lambda r: r["score"])
        left.scatter([r["cycle"] for r in before], [r["score"] for r in before], s=14, color="#9AA5B1")
        left.set_title("Avant l'audit du 28/09 (épreuve v1)", fontsize=11, color="#4A5663")
        left.set_xlabel("cycle")
        left.set_ylim(0, record["score"] * 1.12)
        left.annotate(f"record {record['score']:.2f}\ninvalidé par l'audit", (record["cycle"], record["score"]), xytext=(0.05, 0.08),
                      textcoords="axes fraction", fontsize=10, color="#C0392B", arrowprops={"arrowstyle": "->", "color": "#C0392B"})
        left.grid(alpha=0.3)
    nominal = [r for r in results if r.get("scenario", "nominal") == "nominal"]
    bench = [r for r in results if r.get("scenario", "nominal") != "nominal"]
    ok = [r for r in nominal if r.get("passed")]
    ko = [r for r in nominal if not r.get("passed")]
    ax.scatter([r["cycle"] for r in ok], [r["payload_ratio"] for r in ok], s=30, color="#3FA37A", label="vol réussi (parcours nominal)", zorder=3)
    ax.scatter([r["cycle"] for r in ko], [r["payload_ratio"] for r in ko], s=34, marker="x", color="#C0392B", label="vol raté (charge tentée)", zorder=3)
    ax.scatter([r["cycle"] for r in bench], [r["payload_ratio"] for r in bench], s=34, facecolors="none", edgecolors="#E07B2E",
               label="banc d'essai (vent, chaleur, altitude)", zorder=3)
    # Record du design en cours : meilleur vol réussi de la dernière version qui a volé avec succès.
    best_by_design: dict[str, float] = {}
    current, line_x, line_y = None, [], []
    by_cycle: dict[int, list[dict]] = {}
    for r in nominal:
        by_cycle.setdefault(r["cycle"], []).append(r)
    first = min(r["cycle"] for r in results)
    for cycle in range(first, last_cycle + 1):
        for r in by_cycle.get(cycle, []):
            if r.get("passed"):
                stem = design_stem(r.get("design_id"))
                best_by_design[stem] = max(best_by_design.get(stem, 0.0), r["payload_ratio"])
                current = stem
        if current:
            line_x.append(cycle)
            line_y.append(best_by_design[current])
    ax.step(line_x, line_y, where="post", color="#16222E", linewidth=2, label="record du design en cours")
    history = [(c, v) for c, v in state.get("best_history", []) if v is not None and v > 0]
    if history:
        ax.step([c for c, _ in history], [v for _, v in history], where="post", color="#9AA5B1", linestyle="--", linewidth=1.3,
                label="meilleur score brut (jamais revu à la baisse)")
    notes = fig.add_subplot(grid[1, :])
    notes.axis("off")
    ymax = max(r["payload_ratio"] for r in results) + 0.08
    legend_lines = []
    for number, item in enumerate(annotations.get("corrections", []), start=1):
        color = KIND_COLORS.get(item.get("kind"), "#4A5663")
        ax.axvline(item["cycle"], color=color, linewidth=1.6, alpha=0.85, zorder=1)
        ax.text(item["cycle"], ymax, str(number), color="white", fontsize=9, ha="center", va="center", fontweight="bold",
                bbox={"boxstyle": "circle,pad=0.25", "facecolor": color, "edgecolor": "none"})
        legend_lines.append((number, color, f"{number}. cycle {item['cycle']:g} · {item['label']}"))
    half = (len(legend_lines) + 1) // 2
    for index, (_, color, text) in enumerate(legend_lines):
        column, row = divmod(index, half)
        notes.text(0.0 + 0.5 * column, 1.0 - row * 0.24, text, color=color, fontsize=10, va="top", transform=notes.transAxes)
    ax.set_ylim(min(r["payload_ratio"] for r in results) - 0.1, ymax + 0.08)
    ax.set_title("Épreuve v3 : chaque barre est une correction ; le record baisse, puis remonte sur un design plus honnête",
                 fontsize=11, color="#16222E")
    ax.set_xlabel("cycle")
    ax.grid(alpha=0.3)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.11), ncol=3, fontsize=9, frameon=False)
    fig.savefig(target, bbox_inches="tight")
    plt.close(fig)
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run", type=Path, default=Path("runs/lift_challenge"))
    parser.add_argument("--annotations", type=Path, default=None, help="JSON de corrections à marquer sur le graphique de progression")
    args = parser.parse_args()
    run = args.run
    out = run / "dashboard"
    media = out / "media"
    media.mkdir(parents=True, exist_ok=True)
    timeline = json.loads((run / "highlights" / "timeline.json").read_text()) if (run / "highlights" / "timeline.json").exists() else {}
    state = json.loads((run / "state.json").read_text()) if (run / "state.json").exists() else {}
    audits, notes, inbox = rows(run / "audits.jsonl"), rows(run / "field_notes.jsonl"), rows(run / "inbox.jsonl")
    notebook, catalog = rows(run / "notebook.jsonl"), rows(run / "catalog.jsonl")

    def copy(path: Path, name: str) -> str | None:
        if not path.exists():
            return None
        target = media / name
        shutil.copy(path, target)
        return f"media/{name}"

    def video(path: Path, name: str) -> str:
        """Balise <video> lisible partout : WebM VP9 d'abord (Firefox, VS Code), MP4 H.264 « faststart » en repli."""
        if not path.exists():
            return ""
        webm, mp4 = media / f"{name}.webm", media / f"{name}.mp4"
        if shutil.which("ffmpeg"):
            if not webm.exists() or webm.stat().st_mtime < path.stat().st_mtime:
                subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(path), "-an", "-c:v", "libvpx-vp9", "-crf", "34", "-b:v", "0",
                                "-deadline", "good", "-cpu-used", "4", "-row-mt", "1", str(webm)], check=False)
            if not mp4.exists() or mp4.stat().st_mtime < path.stat().st_mtime:
                subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(path), "-c", "copy", "-movflags", "+faststart", str(mp4)], check=False)
        if not mp4.exists():
            shutil.copy(path, mp4)
        sources = (f'<source src="media/{webm.name}" type="video/webm">' if webm.exists() and webm.stat().st_size else "")
        sources += f'<source src="media/{mp4.name}" type="video/mp4">'
        return f'<video controls preload="metadata" playsinline>{sources}<a href="media/{mp4.name}">ouvrir la vidéo</a></video>'

    manifest = timeline.get("manifest") or {}
    mission = (state.get("mission") or {}).get("text") or "Concevoir de zéro un multirotor pour l'épreuve DARPA Lift (aéronef < 55 lb, charge ≥ 110 lb, 4 nmi chargé + 1 nmi à vide), avec le meilleur ratio charge / masse."
    parts_html = []
    for img in sorted(run.glob("workspace/parts/*/view.png")):
        build = json.loads((img.parent / "build.json").read_text()) if (img.parent / "build.json").exists() else {}
        src = copy(img, f"part-{img.parent.name}.png")
        parts_html.append(f'<div class="card"><img src="{src}" alt="{esc(img.parent.name)}"><p><b>{esc(img.parent.name)}</b><br>'
                          f'<span class="muted">{esc(build.get("material"))} · {esc(build.get("process"))} · {esc(build.get("mass_kg"))} kg</span></p></div>')
    for img in sorted(run.glob("workspace/designs/*/view.png"), key=lambda p: p.stat().st_mtime)[-4:]:
        comp = json.loads((img.parent / "compile.json").read_text()) if (img.parent / "compile.json").exists() else {}
        src = copy(img, f"design-{img.parent.name}.png")
        parts_html.append(f'<div class="card"><img src="{src}" alt="{esc(img.parent.name)}"><p><b>Assemblage {esc(img.parent.name)}</b><br>'
                          f'<span class="muted">{esc(comp.get("aircraft_mass_kg"))} kg · poussée max {esc(comp.get("max_static_thrust_n"))} N</span></p></div>')
    milestone_html = []
    for m in timeline.get("milestones", []):
        clip = video(Path(m["video"]), m["exam_id"])
        verdict = '<span class="ok">réussi</span>' if m.get("passed") else f'<span class="bad">échec : {esc((m.get("failure") or {}).get("reason"))}</span>'
        when = datetime.fromtimestamp(m["time"]).strftime("%d/%m %H:%M")
        milestone_html.append(f'<div class="card"><p><b>{esc(m["label"])}</b> <span class="muted">· {when} · cycle {esc(m.get("cycle"))}</span><br>'
                              f'{esc(m.get("design_id"))} · {esc(m.get("payload_kg"))} kg pour {esc(m.get("aircraft_mass_kg"))} kg · ratio {esc(m.get("ratio"))} · {verdict}</p>'
                              + clip + "</div>")
    annotations = json.loads(args.annotations.read_text(encoding="utf-8")) if args.annotations and args.annotations.exists() else {}
    progress = "media/progression.png" if progress_story(run, annotations, media / "progression.png") else copy(run / "highlights" / "progress.png", "progress.png")
    highlights = video(run / "highlights" / "highlights.mp4", "highlights")
    audit_rows = "".join(f'<tr><td>{esc(a["cycle"])}</td><td class="{"ok" if a["verdict"] == "ok" else "warn" if a["verdict"] == "réserves" else "bad"}">{esc(a["verdict"])}</td>'
                         f'<td>{esc(a["summary"][:400])}</td></tr>' for a in reversed(audits[-15:]))
    note_rows = "".join(f'<tr><td>{esc(n["topic"])}<br><span class="tag">{esc(n["severity"])}</span></td><td>{esc(n["problem"][:300])}'
                        f'<blockquote>« {esc(n["evidence_quote"][:220])} »</blockquote><a href="{esc(n["evidence_url"])}">source</a></td></tr>' for n in notes[-20:])
    human_rows = "".join(f'<tr><td>{esc(r.get("timestamp", "")[:16].replace("T", " "))}</td><td>{esc(r.get("author"))}</td><td>{esc(r.get("text", "")[:300])}</td></tr>'
                         for r in inbox if r.get("author") in ("user", "équipe") and r.get("text"))
    last = notebook[-1] if notebook else {}
    tiles = [("cycles", timeline.get("cycles", state.get("cycle"))), ("vols simulés", timeline.get("flights")),
             ("pièces achetées sourcées", timeline.get("catalog_parts", len(catalog))), ("pièces conçues", timeline.get("custom_parts")),
             ("assemblages", timeline.get("assemblies")), ("problèmes réels consignés", timeline.get("field_notes", len(notes))),
             ("audits", timeline.get("audits", len(audits))), ("messages humains", timeline.get("human_messages"))]
    page = f"""<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Course de l'ingénieur autonome</title><style>{CSS}</style></head><body><main>
<h1>Ingénieur produit autonome</h1><p class="muted">{esc(manifest.get("tag", "course de développement"))} · généré le {datetime.now().strftime("%d/%m/%Y %H:%M")} à partir des fichiers de la course</p>
<p><b>Mission :</b> {esc(mission)}</p>
<div class="tiles">{''.join(f'<div class="tile"><b>{esc(v)}</b><span class="muted">{esc(k)}</span></div>' for k, v in tiles)}</div>
{f'<h2>Temps forts</h2><div class="card">{highlights}</div>' if highlights else ''}
<h2>Jalons</h2><div class="grid">{''.join(milestone_html) or '<p class="muted">Pas encore de vol dans l épreuve v3.</p>'}</div>
{f'<h2>Progression</h2><div class="card"><img src="{progress}" alt="Ratio de chaque vol par cycle et corrections de réalisme"></div>' if progress else ''}
{f'<p class="muted">{esc(annotations["before"]["label"])} ({esc(annotations["before"]["source"])}).</p>' if annotations.get("before") else ''}
<h2>Pièces et assemblages conçus par l'agent</h2><div class="grid">{''.join(parts_html) or '<p class="muted">Aucune pièce pour l instant.</p>'}</div>
<h2>Dernière conclusion de l'ingénieur</h2><div class="card"><p><b>Cycle {esc(last.get("cycle"))}</b> · {esc(last.get("conclusion", "")[:900])}</p><p class="muted">Suite : {esc(last.get("next_step", "")[:500])}</p></div>
<h2>Le vérificateur</h2><div class="card"><table><tr><th>Cycle</th><th>Verdict</th><th>Résumé</th></tr>{audit_rows}</table></div>
<h2>L'éclaireur : problèmes réels du terrain</h2><div class="card"><table><tr><th>Sujet</th><th>Problème et preuve</th></tr>{note_rows}</table></div>
<h2>Messages humains à l'ingénieur</h2><div class="card"><table><tr><th>Date</th><th>Auteur</th><th>Message</th></tr>{human_rows or '<tr><td colspan="3">Aucun</td></tr>'}</table></div>
</main></body></html>"""
    (out / "index.html").write_text(page, encoding="utf-8")
    print(out / "index.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
