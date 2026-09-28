"""Choix du moteur de rendu OpenGL pour MuJoCo : EGL (sans écran) s'il fonctionne, sinon GLFW sur l'affichage.

Sur la machine de développement, EGL peut cesser de fonctionner (état du pilote) alors que GLFW sur la session
graphique reste disponible. Le choix est sondé une fois puis mémorisé 10 minutes.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

CACHE = Path("/tmp/dronelab-gl-backend.json")
PROBE = ("import mujoco; m = mujoco.MjModel.from_xml_string('<mujoco><worldbody><light pos=\"0 0 2\"/>"
         "<geom type=\"box\" size=\".1 .1 .1\"/></worldbody></mujoco>'); d = mujoco.MjData(m); "
         "r = mujoco.Renderer(m, 32, 32); r.update_scene(d); print('RENDER_OK', r.render().mean() > 0)")


def _candidates() -> list[dict]:
    display = os.environ.get("DISPLAY") or ":1"
    xauth = os.environ.get("XAUTHORITY") or f"/run/user/{os.getuid()}/gdm/Xauthority"
    return [{"MUJOCO_GL": "egl", "MUJOCO_EGL_DEVICE_ID": "0"}, {"MUJOCO_GL": "egl", "MUJOCO_EGL_DEVICE_ID": "1"},
            {"MUJOCO_GL": "glfw", "DISPLAY": display, "XAUTHORITY": xauth}]


def render_env() -> dict:
    """Environnement à passer aux sous-processus de rendu."""
    try:
        cached = json.loads(CACHE.read_text())
        if time.time() - cached["at"] < 600:
            return {**os.environ, **cached["env"]}
    except (OSError, ValueError, KeyError):
        pass
    for extra in _candidates():
        env = {**os.environ, **extra}
        try:
            out = subprocess.run([sys.executable, "-c", PROBE], env=env, capture_output=True, text=True, timeout=60)
        except subprocess.TimeoutExpired:
            continue
        if "RENDER_OK True" in out.stdout:
            try:
                CACHE.write_text(json.dumps({"at": time.time(), "env": extra}))
            except OSError:
                pass
            return env
    return {**os.environ, "MUJOCO_GL": "egl"}


def invalidate() -> None:
    CACHE.unlink(missing_ok=True)


def run_render(cmd: list[str], output: Path, timeout: int = 900, extra_env: dict | None = None) -> subprocess.CompletedProcess | None:
    """Lance un rendu ; s'il ne produit pas le fichier attendu, sonde à nouveau le moteur et réessaie une fois."""
    proc = None
    for attempt in range(2):
        env = {**render_env(), **(extra_env or {})}
        try:
            proc = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            proc = None
        if output.exists() and (proc is None or "RESULT_JSON" not in (proc.stdout or "") or '"ok": true' in proc.stdout):
            return proc
        invalidate()
    return proc
