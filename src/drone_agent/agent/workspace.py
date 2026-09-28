"""Espace de travail persistant d'un projet d'ingénierie : état, cahier de labo, consignes, validations.

Tout est en fichiers dans runs/<produit>/ pour survivre aux interruptions :
  state.json               cycle courant, historique du meilleur score, échecs, rétrospectives
  results.jsonl            une ligne par évaluation (écrit par les outils du produit)
  notebook.md / .jsonl     cahier de labo lisible / structuré
  notebook_summary.md      résumé de 15 lignes max, seul à entrer dans le contexte
  inbox.jsonl              consignes de l'utilisateur et réponses de l'agent
  proposals.jsonl          changements de modèle proposés par l'agent, soumis à validation
  model_overrides.yaml     changements validés, appliqués par le modèle du produit
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import yaml

from ..spec import REPO_ROOT
from ..store import append_jsonl, now_iso, read_json, read_jsonl, write_json

SUMMARY_MAX_LINES = 15


@dataclass
class Workspace:
    product: str
    root: Path

    @classmethod
    def open(cls, product: str, root: Path | None = None) -> "Workspace":
        path = Path(root) if root else REPO_ROOT / "runs" / product
        path.mkdir(parents=True, exist_ok=True)
        return cls(product=product, root=path)

    # --- état ---------------------------------------------------------------------------
    @property
    def state_path(self) -> Path:
        return self.root / "state.json"

    def state(self) -> dict:
        return read_json(self.state_path) or {
            "product": self.product, "cycle": 0, "best_history": [], "consecutive_failures": 0,
            "retrospectives": [], "last_retrospective_cycle": 0, "llm_runs": 0, "created_at": now_iso(),
        }

    def save_state(self, state: dict) -> None:
        write_json(self.state_path, state)

    def current_cycle(self) -> int:
        return int(self.state().get("cycle", 0))

    # --- résultats ------------------------------------------------------------------------
    def results(self) -> list[dict]:
        return read_jsonl(self.root / "results.jsonl")

    def best(self, n: int = 5, feasible_only: bool = False) -> list[dict]:
        rows = [r for r in self.results() if r.get("score") is not None]
        if feasible_only:
            rows = [r for r in rows if r.get("feasible")]
        unique = {}
        for row in sorted(rows, key=lambda r: r["score"], reverse=True):
            unique.setdefault(row.get("design_id"), row)
        return list(unique.values())[:n]

    def best_score(self) -> float | None:
        top = self.best(1)
        return top[0]["score"] if top else None

    # --- cahier de labo ---------------------------------------------------------------------
    def write_notebook(self, entry: dict) -> dict:
        cycle = self.current_cycle()
        record = {"cycle": cycle, "timestamp": now_iso(), **entry}
        append_jsonl(self.root / "notebook.jsonl", record)
        lines = [f"### Cycle {cycle} · {record['timestamp'][:16].replace('T', ' ')}"]
        labels = {"kind": "Type", "hypothesis": "Hypothèse", "tests": "Essais choisis", "result": "Résultat",
                  "conclusion": "Conclusion", "next_step": "Prochain essai", "sources": "Sources",
                  "audit_response": "Réponse à l'audit"}
        for key, label in labels.items():
            if entry.get(key):
                value = entry[key] if isinstance(entry[key], str) else json.dumps(entry[key], ensure_ascii=False)
                lines.append(f"{label} : {value}")
        with open(self.root / "notebook.md", "a", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n\n")
        return record

    def notebook(self, last: int | None = None) -> list[dict]:
        entries = read_jsonl(self.root / "notebook.jsonl")
        return entries[-last:] if last else entries

    def summary(self) -> str:
        path = self.root / "notebook_summary.md"
        return path.read_text(encoding="utf-8") if path.exists() else ""

    def set_summary(self, text: str) -> dict:
        lines = [line for line in text.strip().splitlines() if line.strip()]
        if len(lines) > SUMMARY_MAX_LINES:
            return {"ok": False, "reason": f"{len(lines)} lignes, maximum {SUMMARY_MAX_LINES}"}
        (self.root / "notebook_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        state = self.state()
        state["summary_written_at_entry"] = len(self.notebook())
        self.save_state(state)
        return {"ok": True, "lines": len(lines)}

    def summary_due(self, every: int = 10) -> bool:
        written = self.state().get("summary_written_at_entry", 0)
        return len(self.notebook()) - written >= every

    # --- consignes utilisateur ----------------------------------------------------------------
    def post_instruction(self, text: str, author: str = "user") -> dict:
        record = {"id": f"msg-{len(read_jsonl(self.root / 'inbox.jsonl')) + 1:04d}", "timestamp": now_iso(),
                  "author": author, "text": text, "status": "new"}
        append_jsonl(self.root / "inbox.jsonl", record)
        return record

    def inbox(self, pending_only: bool = True) -> list[dict]:
        latest: dict[str, dict] = {}
        for row in read_jsonl(self.root / "inbox.jsonl"):
            latest[row["id"]] = {**latest.get(row["id"], {}), **row}
        rows = list(latest.values())
        return [r for r in rows if r.get("status") == "new"] if pending_only else rows

    def acknowledge(self, message_id: str, response: str) -> dict:
        if message_id not in {r["id"] for r in self.inbox(pending_only=False)}:
            return {"ok": False, "reason": f"message inconnu : {message_id}"}
        append_jsonl(self.root / "inbox.jsonl", {"id": message_id, "status": "done", "response": response,
                                                 "answered_at": now_iso(), "cycle": self.current_cycle()})
        return {"ok": True, "id": message_id}

    # --- changements de modèle soumis à validation --------------------------------------------------
    def propose(self, path: str, value, source_url: str, excerpt: str, justification: str) -> dict:
        record = {"id": f"prop-{len(self.proposals(pending_only=False)) + 1:04d}", "timestamp": now_iso(),
                  "cycle": self.current_cycle(), "path": path, "value": value, "source_url": source_url,
                  "excerpt": excerpt, "justification": justification, "status": "pending"}
        append_jsonl(self.root / "proposals.jsonl", record)
        return record

    def proposals(self, pending_only: bool = True) -> list[dict]:
        latest: dict[str, dict] = {}
        for row in read_jsonl(self.root / "proposals.jsonl"):
            latest[row["id"]] = {**latest.get(row["id"], {}), **row}
        rows = list(latest.values())
        return [r for r in rows if r.get("status") == "pending"] if pending_only else rows

    def decide(self, proposal_id: str, approve: bool, note: str = "") -> dict:
        proposal = next((p for p in self.proposals(pending_only=False) if p["id"] == proposal_id), None)
        if proposal is None or proposal["status"] != "pending":
            return {"ok": False, "reason": f"proposition absente ou déjà traitée : {proposal_id}"}
        status = "approved" if approve else "rejected"
        append_jsonl(self.root / "proposals.jsonl", {"id": proposal_id, "status": status, "note": note,
                                                     "decided_at": now_iso()})
        if approve:
            overrides = self.overrides()
            overrides[proposal["path"]] = {"value": proposal["value"], "source_url": proposal["source_url"],
                                           "proposal": proposal_id}
            (self.root / "model_overrides.yaml").write_text(
                yaml.safe_dump(overrides, allow_unicode=True, sort_keys=True), encoding="utf-8")
        return {"ok": True, "id": proposal_id, "status": status}

    def overrides(self) -> dict:
        path = self.root / "model_overrides.yaml"
        return (yaml.safe_load(path.read_text(encoding="utf-8")) or {}) if path.exists() else {}

    # --- audits du vérificateur ---------------------------------------------------------------------------
    def record_audit(self, cycle: int, verdict: str, summary: str, issues: list[dict]) -> dict:
        record = {"cycle": cycle, "timestamp": now_iso(), "verdict": verdict, "summary": summary, "issues": issues}
        append_jsonl(self.root / "audits.jsonl", record)
        return record

    def audits(self, last: int | None = None) -> list[dict]:
        rows = read_jsonl(self.root / "audits.jsonl")
        return rows[-last:] if last else rows

    # --- éclaireur : connaissances de terrain et revues de réalisme -------------------------------------
    def add_field_note(self, note: dict) -> dict:
        rows = read_jsonl(self.root / "field_notes.jsonl")
        record = {"id": f"note-{len(rows) + 1:04d}", "timestamp": now_iso(), "cycle": self.current_cycle(), **note}
        append_jsonl(self.root / "field_notes.jsonl", record)
        return record

    def field_notes(self, topic: str | None = None, last: int = 40) -> list[dict]:
        rows = read_jsonl(self.root / "field_notes.jsonl")
        if topic:
            rows = [r for r in rows if topic.lower() in json.dumps(r, ensure_ascii=False).lower()]
        return rows[-last:]

    def record_reality_review(self, review: dict) -> dict:
        record = {"cycle": self.current_cycle(), "timestamp": now_iso(), **review}
        append_jsonl(self.root / "reality_reviews.jsonl", record)
        return record

    def reality_reviews(self, last: int | None = None) -> list[dict]:
        rows = read_jsonl(self.root / "reality_reviews.jsonl")
        return rows[-last:] if last else rows
