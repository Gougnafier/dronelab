"""Vidéo d'une épreuve : rejoue la trajectoire enregistrée (mêmes données que la télémétrie de l'agent).

Exécuté dans un processus séparé (contexte OpenGL/EGL propre) :
  MUJOCO_GL=egl python -m drone_agent.lift.render <dossier_epreuve>
Le dossier contient model.xml, trajectory.json, telemetry.csv et summary.json ; sortie video.mp4 + aperçus PNG.
"""

from __future__ import annotations

import csv
import json
import os
import sys
from bisect import bisect_left
from pathlib import Path

PHASE_LABELS = {"settle": "au sol", "climb": "montée", "cruise_loaded": "croisière chargée",
                "hover_drop": "largage", "cruise_empty": "croisière à vide", "descent": "descente",
                "landing": "atterrissage"}


def render(folder: Path, width: int = 960, height: int = 540, fps: int = 30) -> dict:
    os.environ.setdefault("MUJOCO_GL", "egl")  # choisi par l'appelant (gl.render_env)
    import imageio.v2 as imageio
    import mujoco
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont

    model = mujoco.MjModel.from_xml_path(str(folder / "model.xml"))
    data = mujoco.MjData(model)
    trajectory = json.loads((folder / "trajectory.json").read_text())
    summary = json.loads((folder / "summary.json").read_text())
    rows = list(csv.DictReader(open(folder / "telemetry.csv", encoding="utf-8")))
    times = [float(r["t"]) for r in rows]
    drone = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "drone")
    payload = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "payload")
    dq = model.jnt_qposadr[model.body_jntadr[drone]]
    pq = model.jnt_qposadr[model.body_jntadr[payload]] if payload >= 0 else None

    renderer = mujoco.Renderer(model, height, width)
    camera = mujoco.MjvCamera()
    camera.type = mujoco.mjtCamera.mjCAMERA_TRACKING
    camera.trackbodyid = drone
    camera.distance = max(4.0, 2.8 * summary.get("span_m", 2.0))
    camera.elevation = -15
    camera.azimuth = 125
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 20)
        big = ImageFont.truetype("DejaVuSans-Bold.ttf", 34)
    except OSError:
        font = big = ImageFont.load_default()

    # Accéléré ×6 hors croisière, ×48 en croisière (échantillons à 5 Hz).
    frames_idx = [i for i, (_, phase, _, _) in enumerate(trajectory)
                  if not phase.startswith("cruise") or i % 8 == 0]
    writer = imageio.get_writer(folder / "video.mp4", fps=fps, codec="libx264", quality=7, macro_block_size=1)
    previews = []
    for n, i in enumerate(frames_idx):
        t, phase, q, qp = trajectory[i]
        data.qpos[dq:dq + 7] = q
        if pq is not None and qp:
            data.qpos[pq:pq + 7] = qp
        mujoco.mj_forward(model, data)
        renderer.update_scene(data, camera)
        image = Image.fromarray(renderer.render())
        row = rows[min(bisect_left(times, t), len(rows) - 1)] if rows else {}
        draw = ImageDraw.Draw(image, "RGBA")
        draw.rectangle([0, 0, width, 64], fill=(15, 18, 24, 170))
        speedup = "×48" if phase.startswith("cruise") else "×6"
        scenario = summary.get("scenario", "nominal")
        extra = f" · scénario {scenario}" if scenario != "nominal" else ""
        temp = f" · moteurs {float(row['motor_temp_max_c']):.0f} °C" if row and row.get("motor_temp_max_c") else ""
        draw.text((14, 8), f"t = {t:6.1f} s · {PHASE_LABELS.get(phase, phase)} · {speedup}{extra}{temp}", font=font, fill="white")
        if row:
            draw.text((14, 34), f"altitude {float(row['z']):5.1f} m · vitesse {float(row['speed']):4.1f} m/s · "
                                f"batterie {float(row['battery_pct']):5.1f} % · poussée max {100 * float(row['throttle_max']):3.0f} % · "
                                f"charge {'accrochée' if row['payload_attached'] == '1' else 'larguée'}", font=font, fill="white")
        frame = np.asarray(image)
        writer.append_data(frame)
        if n in (0, len(frames_idx) // 3, 2 * len(frames_idx) // 3):
            path = folder / f"frame-{len(previews)}.png"
            image.save(path)
            previews.append(str(path))
    # Image finale : verdict de l'épreuve.
    image = Image.fromarray(renderer.render())
    draw = ImageDraw.Draw(image, "RGBA")
    draw.rectangle([0, height // 2 - 70, width, height // 2 + 70], fill=(15, 18, 24, 200))
    if summary.get("passed"):
        verdict = f"PARCOURS RÉUSSI · {summary['payload_kg']:.1f} kg portés pour {summary['aircraft_mass_kg']:.1f} kg · ratio {summary['ratio']:.2f}"
    else:
        fail = summary.get("failure") or {}
        verdict = f"ÉCHEC · {fail.get('reason', '?')} · t = {fail.get('t', '?')} s ({PHASE_LABELS.get(fail.get('phase'), fail.get('phase'))})"
    draw.text((30, height // 2 - 25), verdict, font=big if len(verdict) < 60 else font, fill="white")
    final = np.asarray(image)
    for _ in range(fps * 2):
        writer.append_data(final)
    writer.close()
    last = folder / "frame-final.png"
    image.save(last)
    previews.append(str(last))
    return {"ok": True, "video": str(folder / "video.mp4"), "frames": len(frames_idx), "previews": previews,
            "size_mb": round((folder / "video.mp4").stat().st_size / 1e6, 2)}


def main() -> None:
    try:
        result = render(Path(sys.argv[1]))
    except Exception as exc:
        result = {"ok": False, "reason": f"{type(exc).__name__}: {exc}"}
    print("RESULT_JSON " + json.dumps(result))


if __name__ == "__main__":
    main()
