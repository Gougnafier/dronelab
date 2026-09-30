#!/usr/bin/env python
"""Montage des temps forts d'une course, construit uniquement à partir de ses fichiers (aucune retouche).

  python scripts/highlights.py --run runs/lift_challenge
Sorties dans <run>/highlights/ : highlights.mp4, timeline.json (jalons datés), cartes PNG.
"""

from __future__ import annotations

import argparse
import json
import sys
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

W, H, FPS = 960, 540, 30


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


def font(size: int, bold: bool = False):
    try:
        return ImageFont.truetype("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf", size)
    except OSError:
        return ImageFont.load_default()


def card(title: str, lines: list[str], accent: str = "#4da3ff") -> np.ndarray:
    image = Image.new("RGB", (W, H), "#11151c")
    draw = ImageDraw.Draw(image)
    draw.rectangle([0, 0, 12, H], fill=accent)
    draw.text((50, 50), title, font=font(34, True), fill="white")
    y = 120
    for line in lines:
        for chunk in textwrap.wrap(line, 62) or [""]:
            draw.text((50, y), chunk, font=font(22), fill="#d7dde6")
            y += 32
        y += 8
        if y > H - 40:
            break
    return np.asarray(image)


def fit(path: Path) -> np.ndarray | None:
    try:
        image = Image.open(path).convert("RGB")
    except OSError:
        return None
    image.thumbnail((W, H))
    canvas = Image.new("RGB", (W, H), "#11151c")
    canvas.paste(image, ((W - image.width) // 2, (H - image.height) // 2))
    return np.asarray(canvas)


def clip_frames(video: Path, head_s: float = 3.0, tail_s: float = 5.0) -> list[np.ndarray]:
    """Début et fin d'une vidéo d'épreuve (la fin contient le verdict)."""
    import imageio.v2 as imageio

    try:
        frames = [f for f in imageio.get_reader(video)]
    except Exception:
        return []
    fps = FPS
    head, tail = int(head_s * fps), int(tail_s * fps)
    chosen = frames if len(frames) <= head + tail else frames[:head] + frames[-tail:]
    return [np.asarray(Image.fromarray(f).resize((W, H))) for f in chosen]


def milestones(run: Path) -> list[dict]:
    exams = sorted(run.glob("exams/exam-*/summary.json"))
    summaries = []
    for f in exams:
        try:
            s = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        s["_dir"] = str(f.parent)
        s["_time"] = f.stat().st_mtime
        summaries.append(s)
    nominal = [s for s in summaries if s.get("scenario", "nominal") == "nominal" and s.get("exam_version", 0) >= 3]
    picks = []

    def add(kind, s, label):
        if s and all(p["exam_id"] != s["exam_id"] for p in picks):
            picks.append({"kind": kind, "label": label, "exam_id": s["exam_id"], "cycle": s.get("cycle"),
                          "design_id": s.get("design_id"), "passed": s.get("passed"), "failure": s.get("failure"),
                          "ratio": s.get("ratio"), "payload_kg": s.get("payload_kg"), "aircraft_mass_kg": s.get("aircraft_mass_kg"),
                          "video": str(Path(s["_dir"]) / "video.mp4"), "time": s["_time"], "scenario": s.get("scenario")})

    v3 = [s for s in summaries if s.get("exam_version", 0) >= 3]
    add("premier_vol", v3[0] if v3 else None, "Premier vol dans l'épreuve")
    add("premier_echec", next((s for s in v3 if not s.get("passed") and (s.get("failure") or {}).get("reason") != "dossier refusé"), None),
        "Premier échec en vol")
    add("premier_succes", next((s for s in nominal if s.get("passed")), None), "Premier parcours réussi")
    qualifying = [s for s in nominal if s.get("passed") and (s.get("rules") or {}).get("payload_qualifying")
                  and (s.get("rules") or {}).get("aircraft_mass_ok")]
    add("premier_qualifiant", qualifying[0] if qualifying else None, "Premier vol qualifiant (≥ 110 lb)")
    add("record", max(qualifying, key=lambda s: s.get("ratio") or 0) if qualifying else None, "Meilleur score brut")
    # Record du dernier design qualifié : un record antérieur peut porter sur une version corrigée depuis.
    final_stem = (qualifying[-1].get("design_id") or "").rsplit("-", 1)[0] if qualifying else ""
    final = [s for s in qualifying if (s.get("design_id") or "").rsplit("-", 1)[0] == final_stem]
    add("record_final", max(final, key=lambda s: s.get("ratio") or 0) if final else None, "Record du design final")
    add("banc", next((s for s in v3 if s.get("scenario") not in (None, "nominal")), None), "Banc d'essai")
    return picks


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run", type=Path, default=Path("runs/lift_challenge"))
    args = parser.parse_args()
    run = args.run
    out = run / "highlights"
    out.mkdir(exist_ok=True)
    state = json.loads((run / "state.json").read_text()) if (run / "state.json").exists() else {}
    manifest = json.loads((run / "manifest.json").read_text()) if (run / "manifest.json").exists() else {}
    notebook, audits, notes = rows(run / "notebook.jsonl"), rows(run / "audits.jsonl"), rows(run / "field_notes.jsonl")
    catalog, inbox = rows(run / "catalog.jsonl"), rows(run / "inbox.jsonl")
    human_by_author: dict[str, set] = {}
    for r in inbox:
        if r.get("author") in ("user", "équipe"):
            human_by_author.setdefault(r["author"], set()).add(r["id"])
    human = sorted(set().union(*human_by_author.values())) if human_by_author else []
    picks = milestones(run)
    parts = sorted(run.glob("workspace/parts/*/view.png"))
    designs = sorted(run.glob("workspace/designs/*/view.png"), key=lambda p: p.stat().st_mtime)
    timeline = {"manifest": manifest, "mission": state.get("mission"), "cycles": state.get("cycle"),
                "flights": len(list(run.glob("exams/exam-*"))), "catalog_parts": len({r.get("id") for r in catalog}),
                "custom_parts": len(parts), "assemblies": len(designs), "field_notes": len(notes), "audits": len(audits),
                "retrospectives": len(state.get("retrospectives", [])), "human_messages": len(human),
                "human_messages_by_author": {k: len(v) for k, v in human_by_author.items()}, "milestones": picks}
    (out / "timeline.json").write_text(json.dumps(timeline, indent=2, ensure_ascii=False), encoding="utf-8")

    frames: list[np.ndarray] = []

    def hold(image: np.ndarray, seconds: float):
        frames.extend([image] * int(seconds * FPS))

    mission = (state.get("mission") or {}).get("text") or "Concevoir de zéro un multirotor pour l'épreuve DARPA Lift : porter la plus grande charge possible par kg d'aéronef."
    hold(card("Ingénieur produit autonome", [f"Mission : {mission}",
                                             "Un agent conçoit, teste en simulation, se corrige ; un vérificateur et un éclaireur le contrôlent.",
                                             f"Laboratoire : {manifest.get('tag', 'course de développement')}"]), 5)
    for pick in picks:
        verdict = "réussi" if pick["passed"] else f"échec : {(pick.get('failure') or {}).get('reason', '?')}"
        lines = [f"Cycle {pick['cycle']} · {pick['exam_id']} · {pick['design_id']}",
                 f"{pick['payload_kg']} kg portés pour {pick['aircraft_mass_kg']} kg d'aéronef (ratio {pick['ratio']}) · {verdict}"]
        if pick.get("scenario") not in (None, "nominal"):
            lines.append(f"Scénario : {pick['scenario']}")
        hold(card(pick["label"], lines), 3)
        frames.extend(clip_frames(Path(pick["video"])))
    try:
        from drone_agent.agent import report
        from drone_agent.agent.workspace import Workspace

        chart = report.progress_chart(Workspace(product=run.name, root=run), out / "progress.png")
        image = fit(chart)
        if image is not None:
            hold(card("Progression", ["Meilleur score par cycle ; lignes orange : rétrospectives imposées."]), 2)
            hold(image, 5)
    except Exception as exc:  # le montage ne doit pas échouer pour un graphique
        print("graphique non produit :", exc)
    for path, title in [*[(p, f"Pièce conçue par l'agent : {p.parent.name}") for p in parts[:3]],
                        *[(p, f"Assemblage : {p.parent.name}") for p in designs[-2:]]]:
        image = fit(path)
        if image is not None:
            hold(card(title, ["CAO par script, matériau et procédé choisis, calcul par éléments finis."
                              if "Pièce" in title else "Squelette compilé : masses calculées, interfaces vérifiées."]), 2)
            hold(image, 3)
    strong = next((a for a in reversed(audits) if a.get("verdict") != "ok" and a.get("issues")), None)
    if strong:
        issue = strong["issues"][0]
        hold(card(f"Le vérificateur · cycle {strong['cycle']} · {strong['verdict']}",
                  [f"Affirmation : {issue.get('claim', '')[:220]}", f"Preuve : {issue.get('evidence', '')[:260]}"], "#e8a33d"), 7)
    note = next((n for n in notes if n.get("severity") == "forte"), notes[0] if notes else None)
    if note:
        hold(card(f"L'éclaireur · {note['topic']}", [note["problem"][:240], f"« {note['evidence_quote'][:200]} »",
                                                      note["evidence_url"]], "#5cc28a"), 7)
    hold(card("Bilan de la course", [
        f"{state.get('cycle', 0)} cycles · {timeline['flights']} vols simulés · {timeline['catalog_parts']} pièces achetées sourcées",
        f"{timeline['custom_parts']} pièces conçues · {timeline['assemblies']} assemblages · {timeline['field_notes']} problèmes réels consignés",
        f"{timeline['audits']} audits · {timeline['retrospectives']} rétrospectives",
        f"Messages humains à l'ingénieur : {timeline['human_messages']}"
        + (f" (utilisateur {timeline['human_messages_by_author'].get('user', 0)}, équipe {timeline['human_messages_by_author'].get('équipe', 0)})" if human else "")
        + (" — dont la mission" if state.get("mission") else "")]), 6)

    import imageio.v2 as imageio

    writer = imageio.get_writer(out / "highlights.mp4", fps=FPS, codec="libx264", quality=7, macro_block_size=1)
    for frame in frames:
        writer.append_data(frame)
    writer.close()
    print(json.dumps({"video": str(out / "highlights.mp4"), "seconds": round(len(frames) / FPS, 1),
                      "milestones": [p["kind"] for p in picks]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
