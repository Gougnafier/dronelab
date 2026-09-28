"""Outils de l'épreuve simulée pour l'agent : contrôle du dossier, passage de l'épreuve, télémétrie."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from ..spec import REPO_ROOT
from ..store import append_jsonl, now_iso, read_jsonl
from .exam import check_package, exam_spec, load_package


def workspace_dir(root: Path) -> Path:
    path = root / "workspace"
    (path / "designs").mkdir(parents=True, exist_ok=True)
    return path


def resolve_design(root: Path, design_dir: str) -> Path:
    """Dossier de conception, relatif à l'espace de travail de l'agent ; refuse d'en sortir."""
    base = workspace_dir(root).resolve()
    path = Path(design_dir)
    path = (path if path.is_absolute() else base / path).resolve()
    if base not in path.parents and path != base:
        raise ValueError(f"le dossier doit être dans l'espace de travail {base}")
    return path


def design_fingerprint(drone_xml: str, design: dict) -> str:
    return hashlib.sha1((drone_xml + json.dumps(design, sort_keys=True)).encode()).hexdigest()[:8]


def check_design(root: Path, design_dir: str) -> dict:
    path = resolve_design(root, design_dir)
    xml, design = load_package(path)
    return {"ok": True, "design_dir": str(path), **check_package(xml, design)}


def run_exam(root: Path, design_dir: str, payload_kg: float, cruise_speed_m_s: float | None, cycle: int,
             hypothesis: str, scenario: str = "nominal") -> dict:
    from ..remote import run_module

    path = resolve_design(root, design_dir)
    xml, design = load_package(path)
    fingerprint = design_fingerprint(xml, design)
    name = path.name
    exams = root / "exams"
    exams.mkdir(exist_ok=True)
    exam_id = f"exam-{len(list(exams.iterdir())) + 1:04d}"
    folder = exams / exam_id
    folder.mkdir()
    shutil.copy(path / "drone.xml", folder / "drone.xml")
    shutil.copy(path / "design.json", folder / "design.json")
    result = run_module("drone_agent.lift.exam", {"drone_xml": xml, "design": design, "payload_kg": payload_kg,
                                                  "cruise_speed_m_s": cruise_speed_m_s, "scenario": scenario}, timeout_s=1500)
    if not result.get("ok"):
        (folder / "summary.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))
        return {"ok": False, "exam_id": exam_id, "reason": result.get("reason"), "ran_on": result.get("ran_on")}
    if "model_xml" in result:
        (folder / "model.xml").write_text(result.pop("model_xml"), encoding="utf-8")
        (folder / "telemetry.csv").write_text(result.pop("telemetry_csv"), encoding="utf-8")
        (folder / "trajectory.json").write_text(json.dumps(result.pop("trajectory")), encoding="utf-8")
    summary = {"exam_id": exam_id, "design": name, "design_id": f"{name}-{fingerprint}", "cycle": cycle,
               "hypothesis": hypothesis, **result}
    (folder / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    video = {}
    if (folder / "model.xml").exists():
        from .gl import run_render

        proc = run_render([sys.executable, "-m", "drone_agent.lift.render", str(folder)], folder / "video.mp4",
                          timeout=900, extra_env={"PYTHONPATH": str(REPO_ROOT / "src")})
        out = proc.stdout if proc else ""
        line = next((l for l in reversed(out.splitlines()) if l.startswith("RESULT_JSON ")), None)
        video = json.loads(line[12:]) if line else {"ok": False, "reason": (proc.stderr[-300:] if proc else "délai dépassé")}
    rules = exam_spec()["rules"]
    nominal = result.get("scenario", "nominal") == "nominal"
    feasible = nominal and bool(result.get("passed") and (result.get("rules") or {}).get("aircraft_mass_ok")
                                and (result.get("rules") or {}).get("payload_qualifying"))
    failure = result.get("failure") or {}
    append_jsonl(root / "results.jsonl", {
        "cycle": cycle, "timestamp": now_iso(), "source": "agent", "hypothesis": hypothesis, "part": "lift_challenge",
        "exam_version": result.get("exam_version"), "payload_requested_kg": result.get("payload_requested_kg"),
        "scenario": result.get("scenario", "nominal"), "scenario_score": result.get("scenario_score"),
        "max_motor_temp_c": result.get("max_motor_temp_c"),
        "design_id": summary["design_id"], "design_dir": str(path), "exam_id": exam_id, "valid": True,
        "score": result.get("score"), "feasible": feasible, "passed": result.get("passed"),
        "violations": [failure["reason"]] if failure else ([] if feasible else ["charge non qualifiante"] if result.get("passed") else []),
        "limiting_factors": [failure["reason"]] if failure else [],
        "params": {"payload_kg": result.get("payload_kg"), "cruise_speed_m_s": result.get("cruise_speed_m_s")},
        "aircraft_mass_kg": result.get("aircraft_mass_kg"), "payload_kg": result.get("payload_kg"),
        "payload_ratio": result.get("ratio"), "energy_used_wh": result.get("energy_used_wh"),
        "battery_min_pct": result.get("battery_min_pct"), "max_tilt_deg": result.get("max_tilt_deg"),
        "mission_time_s": result.get("mission_time_s"), "ran_on": result.get("ran_on"),
        "payload_min_kg": rules["payload_min_kg"]})
    phases = {k: {kk: v[kk] for kk in ("t_start", "t_end", "energy_wh", "max_throttle", "mean_power_w", "max_tracking_error_m")}
              for k, v in (result.get("phases") or {}).items()}
    return {"ok": True, "exam_id": exam_id, "design_id": summary["design_id"], "passed": result.get("passed"),
            "failure": result.get("failure"), "score": result.get("score"), "qualifying": feasible,
            "aircraft_mass_kg": result.get("aircraft_mass_kg"), "payload_kg": result.get("payload_kg"),
            "payload_requested_kg": result.get("payload_requested_kg"),
            "payload_note": "charge appliquée = multiple de 2,5 lb inférieur ou égal à la charge demandée",
            "ratio": result.get("ratio"), "exam_version": result.get("exam_version"),
            "scenario": result.get("scenario"), "scenario_description": result.get("scenario_description"),
            "max_motor_temp_c": result.get("max_motor_temp_c"), "ambient_c": result.get("ambient_c"),
            "refused_because": ((result.get("failure") or {}).get("details")), "mission_time_s": result.get("mission_time_s"),
            "planned_time_s": result.get("planned_time_s"), "energy_used_wh": result.get("energy_used_wh"),
            "battery_usable_wh": result.get("battery_usable_wh"), "battery_min_pct": result.get("battery_min_pct"),
            "max_tilt_deg": result.get("max_tilt_deg"), "max_tracking_error_m": result.get("max_tracking_error_m"),
            "phases": phases, "check_warnings": (result.get("check") or {}).get("warnings"),
            "ran_on": result.get("ran_on"), "video": video.get("video"), "video_ok": video.get("ok"),
            "telemetry": "exam_telemetry(exam_id, ...) pour lire les séries temporelles"}


def exam_telemetry(root: Path, exam_id: str, columns: list[str] | None, t_from: float, t_to: float | None,
                   every_s: float) -> dict:
    path = root / "exams" / exam_id / "telemetry.csv"
    if not path.exists():
        return {"ok": False, "reason": f"télémétrie absente pour {exam_id}"}
    rows = list(csv.DictReader(open(path, encoding="utf-8")))
    available = list(rows[0]) if rows else []
    columns = [c for c in (columns or available) if c in available]
    if "t" not in columns:
        columns = ["t"] + columns
    out, next_t = [], t_from
    for row in rows:
        t = float(row["t"])
        if t < t_from or (t_to is not None and t > t_to):
            continue
        if t + 1e-9 >= next_t:
            out.append({c: row[c] for c in columns})
            next_t = t + max(every_s, 0.1)
    truncated = len(out) > 300
    return {"ok": True, "exam_id": exam_id, "available_columns": available, "rows": out[:300],
            "truncated": truncated, "note": "300 lignes max ; augmenter every_s ou réduire l'intervalle"}


def exam_list(root: Path, last: int) -> dict:
    items = []
    for folder in sorted((root / "exams").glob("exam-*"))[-last:]:
        try:
            s = json.loads((folder / "summary.json").read_text())
        except (OSError, json.JSONDecodeError):
            continue
        item = {k: s.get(k) for k in ("exam_id", "design_id", "cycle", "scenario", "passed", "failure", "score", "ratio",
                                      "payload_kg", "aircraft_mass_kg", "max_motor_temp_c", "hypothesis")}
        if (folder / "video.mp4").exists():
            item["video"] = str(folder / "video.mp4")
            item["preview"] = str(folder / "frame-final.png")
        items.append(item)
    return {"ok": True, "exams": items}
