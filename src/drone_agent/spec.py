"""Lecture du cahier des charges machine (spec/cahier_des_charges.yaml)."""

from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SPEC_PATH = REPO_ROOT / "spec" / "cahier_des_charges.yaml"


@lru_cache(maxsize=8)
def load_spec(path: str | Path = DEFAULT_SPEC_PATH) -> dict:
    with open(path, encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def canonical_json(data: dict) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def short_hash(data: dict, length: int = 8) -> str:
    return hashlib.sha1(canonical_json(data).encode("utf-8")).hexdigest()[:length]
