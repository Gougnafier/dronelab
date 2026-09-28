#!/usr/bin/env python
"""Contrôle complet du laboratoire avant (ou pendant) une course : profils Hermes, clés, serveurs d'outils,
compétences, personnalités, services, RTX 5090, rendu, transcription, Discord. N'appelle aucun modèle
de langage sauf avec --ping (une requête minimale par profil).

  python scripts/check_lab.py
  python scripts/check_lab.py --ping
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
HERMES = Path.home() / ".hermes" / "profiles"
PY = Path.home() / "miniconda3/envs/drone-agent/bin/python"

ROLES = {  # profil -> (rôle MCP, compétences attendues, outils Hermes interdits)
    "dronelab": ("engineer", ["engineering-cycle", "drone-from-scratch", "lift-exam", "assembly-design", "part-design",
                              "component-research", "progress-report"], ["computer_use", "memory", "clarify", "cronjob"]),
    "dronecheck": ("auditor", ["audit-claims", "lift-exam"], ["terminal", "code_execution", "computer_use", "memory"]),
    "dronescout": ("scout", ["field-research", "reality-review", "component-research", "lift-exam"],
                   ["terminal", "code_execution", "computer_use", "memory"]),
    "dronedesk": ("desk", ["progress-report"], ["terminal", "code_execution", "computer_use"]),
}
KEY_FOR = {"deepseek": "DEEPSEEK_API_KEY", "nvidia": "NVIDIA_API_KEY"}
results: list[tuple[str, str, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append(("OK " if ok else "ÉCHEC", name, detail))


def run(cmd: list[str] | str, timeout: int = 120, **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, shell=isinstance(cmd, str), **kw)


def profiles(ping: bool) -> None:
    import yaml

    for profile, (role, skills, forbidden) in ROLES.items():
        folder = HERMES / profile
        if not folder.exists():
            check(f"{profile} : profil", False, "absent")
            continue
        cfg = yaml.safe_load((folder / "config.yaml").read_text())
        provider, model = cfg["model"].get("provider"), cfg["model"].get("default")
        env = (folder / ".env").read_text() if (folder / ".env").exists() else ""
        key = KEY_FOR.get(provider)
        has_key = key is None or any(line.startswith(f"{key}=") and len(line) > len(key) + 5 for line in env.splitlines())
        check(f"{profile} : modèle", has_key, f"{provider} / {model}" + ("" if has_key else f" — clé {key} absente"))
        servers = cfg.get("mcp_servers") or {}
        server = servers.get(role)
        ok = server is not None and "--role" in server["args"] and server["args"][server["args"].index("--role") + 1] == role \
            and "lift_challenge" in server["args"]
        check(f"{profile} : serveur MCP « {role} »", ok and len(servers) == 1,
              f"serveurs déclarés : {list(servers)}" + ("" if server and server.get("env", {}).get("DRONE_AGENT_NOTIFY_TARGET") else " — sans cible Discord"))
        test = run([str(Path.home() / ".local/bin" / profile), "mcp", "test", role], timeout=120)
        count = next((l for l in test.stdout.splitlines() if "tool" in l.lower()), "").strip()
        check(f"{profile} : outils MCP chargés", test.returncode == 0, count or (test.stderr or test.stdout)[-200:])
        missing = [s for s in skills if not (folder / "skills" / "engineering" / s / "SKILL.md").exists()]
        check(f"{profile} : compétences", not missing, "manquantes : " + ", ".join(missing) if missing else ", ".join(skills))
        soul = folder / "SOUL.md"
        check(f"{profile} : personnalité", soul.is_symlink() and soul.resolve().parent == REPO / "hermes",
              str(soul.resolve()) if soul.exists() else "absente")
        tools = run([str(Path.home() / ".local/bin" / profile), "tools", "list"], timeout=60).stdout
        enabled = [t for t in forbidden if f"✓ enabled  {t}" in tools]
        check(f"{profile} : outils Hermes interdits coupés", not enabled, "encore actifs : " + ", ".join(enabled) if enabled else "")
        if ping:
            out = run([str(Path.home() / ".local/bin" / profile), "chat", "-q", "Réponds uniquement : OK", "-Q", "--source",
                       "tool", "--max-turns", "1", "--ignore-rules"], timeout=240)
            check(f"{profile} : réponse du modèle", "OK" in out.stdout, (out.stdout + out.stderr).strip()[-160:])


def services() -> None:
    active = run("systemctl --user is-active dronelab-agent").stdout.strip()
    args = run("systemctl --user show dronelab-agent -p ExecStart").stdout
    stop = (REPO / "runs/lift_challenge/STOP").exists()
    check("service superviseur", active == "active" and not stop, f"{active}" + (" — fichier STOP présent" if stop else ""))
    for flag in ("--auditor-cmd dronecheck", "--scout-cmd dronescout", "--notify discord", "--report"):
        check(f"superviseur : {flag.split()[0]}", flag in args.replace(";", " ").replace("  ", " ") or flag.split()[0] in args, "")
    check("superviseur : sans plafond de cycles", "--max-cycles-per-day 60" not in args, "")
    gw = run("systemctl --user is-active hermes-gateway-dronedesk").stdout.strip()
    log = HERMES / "dronedesk/logs/gateway.log"
    connected = log.exists() and "discord connected" in log.read_text(errors="replace")[-20000:]
    check("passerelle Discord", gw == "active" and connected, gw)
    check("cible Discord", (REPO / "data/local/notify_target").exists(), "")


def remote() -> None:
    ssh = ["ssh", "-F", str(REPO / "data/local/ssh_config"), "rtx5090"]
    files = ["src/drone_agent/lift/exam.py", "src/drone_agent/lift/partfem.py", "src/drone_agent/fem/calculix.py",
             "spec/lift_exam.yaml", "spec/materials.yaml"]
    local = {f: hashlib.md5((REPO / f).read_bytes()).hexdigest() for f in files}
    cmd = 'wsl.exe -d Ubuntu -- bash -lc "cd ~/drone-agent/repo && md5sum ' + " ".join(files) + \
          ' && ~/drone-agent/env/bin/python -c \\"import mujoco, gmsh; print(\\\\\\"libs\\\\\\", mujoco.__version__)\\" && ls ~/drone-agent/env/bin/ccx"'
    try:
        out = run(ssh + [cmd], timeout=90)
    except subprocess.TimeoutExpired:
        check("RTX 5090 : accès SSH", False, "délai dépassé")
        return
    remote_md5 = {l.split()[1]: l.split()[0] for l in out.stdout.splitlines() if len(l.split()) == 2 and l.split()[1] in local}
    check("RTX 5090 : accès SSH", bool(remote_md5), (out.stderr or "")[-150:] if not remote_md5 else "")
    stale = [f for f in files if remote_md5.get(f) != local[f]]
    check("RTX 5090 : code à jour", not stale, "à resynchroniser : " + ", ".join(stale) if stale else "")
    check("RTX 5090 : MuJoCo, Gmsh, CalculiX", "libs" in out.stdout and "ccx" in out.stdout, "")


def local_stack() -> None:
    code = ("import mujoco; m = mujoco.MjModel.from_xml_string('<mujoco><worldbody><light pos=\"0 0 2\"/>"
            "<geom type=\"box\" size=\".1 .1 .1\"/></worldbody></mujoco>'); d = mujoco.MjData(m); "
            "r = mujoco.Renderer(m, 64, 64); r.update_scene(d); print('rendu', r.render().mean() > 0)")
    from drone_agent.lift.gl import CACHE, render_env

    CACHE.unlink(missing_ok=True)
    env = render_env()
    out = run([str(PY), "-c", code], timeout=60, env=env)
    check("rendu vidéo local", "rendu True" in out.stdout, f"moteur {env.get('MUJOCO_GL')}" + (f" (EGL indisponible, repli sur l'affichage {env.get('DISPLAY')})" if env.get("MUJOCO_GL") == "glfw" else ""))
    whisper = Path.home() / ".cache/huggingface/hub/models--Systran--faster-whisper-small"
    check("transcription locale (Whisper)", any(whisper.rglob("model.bin")), "")
    out = run([str(PY), "-c", "import yt_dlp, youtube_transcript_api, faster_whisper; print('ok')"], timeout=60)
    check("bibliothèques YouTube", "ok" in out.stdout, out.stderr[-150:])
    check("CalculiX local", (PY.parent / "ccx").exists(), "")
    free = os.statvfs(REPO)
    gb = free.f_bavail * free.f_frsize / 1e9
    check("espace disque", gb > 20, f"{gb:.0f} Go libres")


def project() -> None:
    from drone_agent.agent.toolbox import tools_for
    from drone_agent.products import get_product

    product = get_product("lift_challenge")
    for role in ("engineer", "auditor", "scout", "desk"):
        check(f"outils du rôle {role}", len(tools_for(role, "lift_challenge")) > 5,
              f"{len(tools_for(role, 'lift_challenge'))} outils")
    missing = [s for s in product.skills if not (REPO / "skills" / s / "SKILL.md").exists()]
    check("compétences du produit dans le dépôt", not missing, ", ".join(missing))
    from drone_agent.lift.exam import exam_spec

    spec = exam_spec()
    check("épreuve", spec.get("version") == 3 and spec["plausibility"].get("require_compiled"),
          f"version {spec.get('version')}, scénarios : {', '.join(spec.get('scenarios', {}))}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--ping", action="store_true", help="une requête minimale à chaque modèle")
    args = parser.parse_args()
    for step in (project, profiles, services, remote, local_stack):
        try:
            step(args.ping) if step is profiles else step()
        except Exception as exc:
            check(step.__name__, False, f"{type(exc).__name__}: {exc}")
    width = max(len(n) for _, n, _ in results)
    for status, name, detail in results:
        print(f"{status}  {name.ljust(width)}  {detail}")
    failed = sum(1 for s, _, _ in results if s != "OK ")
    print(f"\n{len(results) - failed}/{len(results)} contrôles réussis")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
