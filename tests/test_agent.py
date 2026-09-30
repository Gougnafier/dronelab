"""Tests du noyau de l'agent sans LLM : un faux runner joue l'ingénieur via la boîte à outils."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def loose_exam(monkeypatch):
    """Le drone de test est écrit à la main : on lève ici l'obligation de dossier compilé (épreuve v3)."""
    import copy

    from drone_agent.lift import exam

    spec = copy.deepcopy(exam.exam_spec())
    spec["plausibility"]["require_compiled"] = False
    monkeypatch.setattr(exam, "exam_spec", lambda: spec)

from drone_agent.agent import toolbox
from drone_agent.agent.supervisor import Config, Supervisor, build_prompt, plateau
from drone_agent.agent.workspace import Workspace

GOOD = {"n_arms": 6, "coaxial": False, "prop_diameter_in": 47.57, "motor_power_kw": 3.82, "battery_kg": 8.39,
        "battery": "lipo", "cruise_speed_m_s": 24.47, "arm_od_mm": 59.45, "arm_wall_mm": 1.32}
WEAK = {**GOOD, "battery_kg": 3.0}


@pytest.fixture
def root(tmp_path, monkeypatch):
    monkeypatch.delenv("DRONE_AGENT_NOTIFY_TARGET", raising=False)
    return tmp_path / "heavylift"


def scripted_runner(plan):
    """plan(cycle) -> liste d'actions exécutées comme le ferait l'ingénieur ; renvoie un code de sortie 0."""
    prompts = []

    def run(prompt, cycle, log_path):
        prompts.append(prompt)
        log_path.write_text("faux runner", encoding="utf-8")
        for action in plan(cycle):
            action()
        return {"returncode": 0, "seconds": 0.0}

    run.prompts = prompts
    return run


def make(root, plan, **overrides):
    toolbox.init("heavylift", root)
    runner = scripted_runner(plan)
    config = Config(product="heavylift", root=root, pause_s=0, failure_backoff_s=0, **overrides)
    return Supervisor(config, runner=runner, sleep=lambda s: None), runner


def entry(text="essai"):
    return lambda: toolbox.notebook_write(hypothesis=text, tests="évaluation", result="-", conclusion="-", next_step="-")


def test_cycle_needs_a_notebook_entry(root):
    sup, _ = make(root, lambda c: [lambda: toolbox.evaluate_design(WEAK, "sans conclusion")])
    for _ in range(3):
        assert sup.run_cycle()["success"] is False
    outbox = (root / "outbox.jsonl").read_text(encoding="utf-8")
    assert '"blocked"' in outbox  # alerte après trois échecs d'affilée


def test_record_is_notified_and_state_survives_restart(root):
    plan = lambda c: [lambda: toolbox.evaluate_design(WEAK if c == 1 else GOOD, f"cycle {c}"), entry()]
    sup, _ = make(root, plan)
    first = sup.run_cycle()
    assert first["success"] and not first["record"]  # design non qualifiant : pas de notification
    second = sup.run_cycle()
    assert second["record"] and second["best"] > 3
    assert '"record"' in (root / "outbox.jsonl").read_text(encoding="utf-8")

    again, _ = make(root, plan)  # nouveau processus, même dossier
    assert again.run_cycle()["cycle"] == 3


def test_plateau_forces_a_retrospective(root):
    plan = lambda c: [lambda: toolbox.evaluate_design(GOOD, "même design"), entry()]
    sup, runner = make(root, plan, plateau_window=3)
    flags = [sup.run_cycle()["retrospective"] for _ in range(6)]
    assert flags == [False, False, False, False, True, False]
    assert "RÉTROSPECTIVE IMPOSÉE" in runner.prompts[4]
    assert Workspace.open("heavylift", root).state()["retrospectives"][0]["cycle"] == 5


def test_plateau_detector_thresholds():
    flat = [[i, 2.0] for i in range(1, 20)]
    assert plateau(flat, 15, 0.01, 0)
    rising = [[i, 2.0 + 0.1 * i] for i in range(1, 20)]
    assert not plateau(rising, 15, 0.01, 0)
    assert not plateau(flat, 15, 0.01, since_cycle=10)  # fenêtre remise à zéro après une rétrospective


def test_user_instruction_reaches_engineer_and_gets_answered(root):
    sup, runner = make(root, lambda c: [
        lambda: toolbox.reply_to_user(toolbox.user_inbox()["pending"][0]["id"], "Compris, j'essaie 8 bras."),
        entry()])
    toolbox.post_instruction("Essaie une configuration à 8 bras.")
    sup.run_cycle()
    assert "Consignes utilisateur en attente : 1" in runner.prompts[0]
    assert toolbox.user_inbox()["pending"] == []


def test_model_update_needs_user_approval(root):
    toolbox.init("heavylift", root)
    before = toolbox.evaluate_design(GOOD, "référence")["score"]
    proposal = toolbox.propose_model_update(
        "batteries.lipo.specific_energy_wh_kg", 140, "https://example.org/datasheet",
        "Pack LiPo 12S 22Ah : 140 Wh/kg mesurés au niveau du pack", "fiche plus prudente que l'hypothèse")
    assert proposal["status"] == "pending"
    assert toolbox.brief()["approved_overrides"] == {}
    assert toolbox.decide_proposal not in toolbox.ENGINEER_TOOLS  # l'ingénieur ne se valide pas lui-même
    assert toolbox.decide_proposal(proposal["id"], True, "ok")["status"] == "approved"
    after = toolbox.evaluate_design(GOOD, "après validation")["score"]
    assert after < before


def test_prompt_is_fresh_and_bounded(root):
    toolbox.init("heavylift", root)
    ws = Workspace.open("heavylift", root)
    for i in range(30):
        toolbox.evaluate_design({**GOOD, "battery_kg": 5 + i * 0.1}, f"essai {i}")
    prompt = build_prompt(ws, Config(root=root), retrospective=False, summary_due=True)
    assert prompt.count("heavylift-") == 5  # 5 meilleurs designs seulement, pas tout l'historique
    assert "notebook_summary_write" in prompt


def test_tools_never_raise(root):
    toolbox.init("heavylift", root)
    assert toolbox.evaluate_design({"wings": 3}, "paramètres invalides")["ok"] is False
    assert toolbox.optimize_local(GOOD, ["battery"], 10)["ok"] is False
    assert toolbox.reply_to_user("msg-9999", "rien")["ok"] is False


def test_generic_report_tools_work_for_any_numeric_field(root):
    sup, _ = make(root, lambda c: [lambda: toolbox.evaluate_design(GOOD, "record"), entry()])
    sup.run_cycle()
    fields = toolbox.result_fields()["fields"]
    assert "aircraft_mass_kg" in fields and "mission.needed_wh" in fields
    chart = toolbox.plot_results("aircraft_mass_kg", "max_payload_kg",
                                 reference_lines=[{"kind": "slope", "value": 2, "label": "2:1"}])
    assert chart["ok"] and Path(chart["image"]).stat().st_size > 10_000
    assert toolbox.plot_results("nope", "score")["ok"] is False
    progress = toolbox.plot_progress()
    sent = toolbox.send_report("Rapport de test : record qualifiant au cycle 1, rien d'autre à signaler.",
                               [chart["image"], progress["image"]])
    assert sent["ok"] and sent["images"] == 2
    assert toolbox.send_report("Rapport avec une image hors dossier du projet, refusée.", ["/etc/passwd"])["ok"] is False


def test_report_session_by_agent_with_generic_fallback(root):
    sup, runner = make(root, lambda c: [entry()], report_times=("08:00", "20:00"))
    assert sup.report_due("2026-09-28T07:59:00+02:00") is None
    assert sup.report_due("2026-09-28T08:05:00+02:00") == "2026-09-28 08:00"
    # la session de rapport du faux runner n'envoie rien : le rapport générique de secours part
    assert sup.send_report("2026-09-28 08:00") == {"slot": "2026-09-28 08:00", "by_agent": False}
    assert "Session de RAPPORT" in runner.prompts[-1]
    assert sup.report_due("2026-09-28T12:00:00+02:00") is None
    assert sup.report_due("2026-09-28T20:01:00+02:00") == "2026-09-28 20:00"

    def writes_report(cycle):
        return [lambda: toolbox.send_report("Rapport rédigé par l'agent : aucun design qualifiant pour l'instant.",
                                            [toolbox.plot_progress()["image"]])]
    agent_sup, _ = make(root, writes_report)
    assert agent_sup.send_report("2026-09-28 20:00")["by_agent"] is True


def test_rate_limit_is_a_wait_not_a_failure(root):
    toolbox.init("heavylift", root)

    def limited(prompt, cycle, log_path):
        log_path.write_text("API call failed after 3 retries: HTTP 429: {\"title\":\"Too Many Requests\"}")
        return {"returncode": 1, "seconds": 1.0}

    sup = Supervisor(Config(product="heavylift", root=root, rate_limit_alert_after=3), runner=limited, sleep=lambda s: None)
    backoffs = [sup.run_cycle()["backoff_s"] for _ in range(4)]
    assert backoffs == [60, 120, 240, 480]
    state = Workspace.open("heavylift", root).state()
    assert state["cycle"] == 0 and state.get("consecutive_failures", 0) == 0 and not state.get("best_history")
    outbox = (root / "outbox.jsonl").read_text(encoding="utf-8")
    assert outbox.count('"blocked"') == 1  # une seule alerte pour l'épisode


def test_failure_alert_is_sent_once_then_recovery(root):
    plan = lambda c: [entry()] if c > 5 else []
    sup, _ = make(root, plan)
    for _ in range(6):
        sup.run_cycle()
    outbox = (root / "outbox.jsonl").read_text(encoding="utf-8")
    assert outbox.count('"blocked"') == 1 and outbox.count('"recovered"') == 1


def test_engineer_must_answer_audit_points(root):
    toolbox.init("heavylift", root)
    ws = Workspace.open("heavylift", root)
    state = ws.state()
    state["cycle"] = 1
    ws.save_state(state)
    ws.record_audit(1, "problème", "URL 404", [{"claim": "source", "evidence": "404", "severity": "moyenne"}])
    state["cycle"] = 2
    ws.save_state(state)
    refused = toolbox.notebook_write("h", "t", "r", "c", "n")
    assert refused["ok"] is False and "audit du cycle 1" in refused["reason"]
    ok = toolbox.notebook_write("h", "t", "r", "c", "n",
                                audit_response="Source remplacée par la fiche produit, URL vérifiée ; chiffre inchangé.")
    assert ok["ok"] and ws.notebook()[-1]["audit_cycle"] == 1
    assert toolbox.notebook_write("h2", "t", "r", "c", "n")["ok"]  # audit déjà traité


def test_scout_notes_requests_and_reality_review(root):
    toolbox.init("lift_challenge", root)
    assert toolbox.field_note_add("moteurs", "supports en contreplaqué cassés", "notanurl", "x", "y", "z", "forte")["ok"] is False
    note = toolbox.field_note_add("structure", "supports moteur en contreplaqué rompus en vol d'essai",
                                  "https://www.youtube.com/watch?v=LrQPa1_s8Qs&t=18s",
                                  "the final thing that broke was the plywood motor mounts",
                                  "supports moteur usinés en aluminium", "cas de charge de choc sur le support", "forte", 18)
    assert note["ok"] and toolbox.field_notes("structure")["notes"][0]["id"] == note["id"]
    request = toolbox.request_test("choc sur support moteur", "rupture observée sur un drone de 100 kg",
                                   "part_fem avec 3 × poussée max", [note["id"]])
    pending = toolbox.user_inbox()["pending"]
    assert pending[0]["id"] == request["message_id"] and pending[0]["author"] == "éclaireur"
    review = toolbox.record_reality_review("à renforcer", "le vent n'est testé que sur demande", [
        {"aspect": "rafales", "simulation": "air calme", "reality": "rafales fréquentes en extérieur",
         "evidence": note["id"], "severity": "moyenne", "action": "épreuve"}])
    assert review["exam_gaps_sent_to_team"] == 1
    assert '"reality"' in (root / "outbox.jsonl").read_text(encoding="utf-8")
    names = [f.__name__ for f in toolbox.tools_for("scout", "lift_challenge")]
    assert "youtube_transcript" in names and "run_exam" not in names and "record_audit" not in names


def test_scout_sessions_alternate_every_n_successful_cycles(root):
    sup, _ = make(root, lambda c: [entry()], scout_every=2)
    sup.config.scout_cmd = "true"  # commande neutre : on teste l'ordonnancement, pas le modèle
    assert sup.scout_due() is None
    sup.run_cycle()
    assert sup.scout_due() is None
    sup.run_cycle()
    assert sup.scout_due() == "veille"
    sup.run_scout("veille")
    assert sup.scout_due() is None
    sup.run_cycle(); sup.run_cycle()
    assert sup.scout_due() == "revue"


def test_clean_run_waits_for_the_mission_from_discord(root):
    sup, runner = make(root, lambda c: [entry()], await_mission=True, max_cycles=1)
    calls = []

    def fake_sleep(seconds):
        calls.append(seconds)
        if len(calls) == 2:  # l'utilisateur écrit sa mission pendant l'attente
            toolbox.post_instruction("Concevoir un drone qui porte 4 fois son poids sur le parcours DARPA Lift.")

    sup.sleep = fake_sleep
    sup.run()
    state = Workspace.open("heavylift", root).state()
    assert state["mission"]["text"].startswith("Concevoir un drone")
    cycle_prompts = [p for p in runner.prompts if "Session de RAPPORT" not in p]
    assert "Mission confiée par l'utilisateur" in cycle_prompts[0]
    assert toolbox.user_inbox()["pending"] == []  # la mission n'est pas traitée comme une consigne ordinaire
