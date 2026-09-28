"""Stockage des designs et journaux JSONL (runs/)."""

from __future__ import annotations

import fcntl
import json
import os
from datetime import datetime
from pathlib import Path

from .spec import REPO_ROOT


def runs_dir() -> Path:
    path = Path(os.environ.get("DRONE_AGENT_RUNS", REPO_ROOT / "runs"))
    path.mkdir(parents=True, exist_ok=True)
    return path


def design_dir(design_id: str) -> Path:
    path = runs_dir() / "designs" / design_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def append_jsonl(path: Path, record: dict) -> None:
    line = json.dumps(record, ensure_ascii=False) + "\n"
    with open(path, "a", encoding="utf-8") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        handle.write(line)
        fcntl.flock(handle, fcntl.LOCK_UN)


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    records = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue  # ligne tronquée par une interruption
    return records


def write_json(path: Path, data: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def read_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None
