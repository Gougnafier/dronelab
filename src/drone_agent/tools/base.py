"""Règle commune des outils : JSON en entrée et en sortie, jamais d'exception."""

from __future__ import annotations

import functools
import time
import traceback

from ..store import append_jsonl, now_iso, runs_dir


def tool(func):
    """Transforme toute erreur en résultat « invalide » et journalise l'appel."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.monotonic()
        try:
            result = func(*args, **kwargs)
        except Exception as exc:  # l'agent doit toujours recevoir un résultat lisible
            result = {
                "ok": False,
                "valid": False,
                "reason": f"{type(exc).__name__}: {exc}",
                "trace": traceback.format_exc(limit=3),
            }
        result.setdefault("ok", True)
        result["tool"] = func.__name__
        result["seconds"] = round(time.monotonic() - start, 2)
        try:
            call = {"timestamp": now_iso(), "cycle": _current_cycle(), "tool": func.__name__,
                    "args": _jsonable(args), "kwargs": _jsonable(kwargs)}
            call.update({k: v for k, v in result.items() if k != "trace"})
            append_jsonl(runs_dir() / "calls.jsonl", call)
        except Exception:
            pass  # le journal ne doit jamais faire échouer l'outil
        return result

    return wrapper


def _current_cycle():
    try:
        import json

        return json.loads((runs_dir() / "state.json").read_text()).get("cycle")
    except (OSError, ValueError):
        return None


def _jsonable(value):
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)
