"""Tests du modèle de multirotor lourd (analytique, rapide)."""

from __future__ import annotations

import math

import pytest

from drone_agent.heavylift.evaluate import evaluate_vehicle, lift_spec
from drone_agent.heavylift.model import Vehicle, max_payload

# Fixture de test : design qualifiant trouvé lors de la vérification du modèle (évolution différentielle,
# 27/09/2026). Sert à tester le code ; ce n’est pas un résultat de l’agent.
FIXTURE_DESIGN = {
    "n_arms": 6, "coaxial": False, "prop_diameter_in": 47.57, "motor_power_kw": 3.82, "battery_kg": 8.39,
    "battery": "lipo", "cruise_speed_m_s": 24.47, "arm_od_mm": 59.45, "arm_wall_mm": 1.32,
}


@pytest.fixture(autouse=True)
def isolated_runs(tmp_path, monkeypatch):
    monkeypatch.setenv("DRONE_AGENT_RUNS", str(tmp_path / "runs"))


@pytest.fixture
def vehicle():
    return Vehicle(dict(FIXTURE_DESIGN), lift_spec())


def test_hover_power_matches_momentum_theory(vehicle):
    thrust = 1000.0
    ideal = thrust**1.5 / math.sqrt(2 * vehicle.rho * vehicle.total_area_m2)
    assert vehicle.hover_power(thrust) == pytest.approx(ideal / vehicle.fm)


def test_climb_and_cruise_reduce_to_hover_at_zero_speed(vehicle):
    weight = 800.0
    assert vehicle.climb_power(weight, 0.0) == pytest.approx(vehicle.hover_power(weight))
    assert vehicle.cruise_power(weight, 1e-9, 0.1) == pytest.approx(vehicle.hover_power(weight), rel=1e-6)


def test_forward_flight_lowers_induced_power(vehicle):
    weight = 800.0
    assert vehicle.cruise_power(weight, 12.0, 0.0) < vehicle.hover_power(weight)


def test_max_payload_is_the_last_passing_plate_step(vehicle):
    spec = lift_spec()
    edition, step = spec["editions"]["dlc1"], spec["payload_step_kg"]
    result = max_payload(vehicle, edition, step)
    k = round(result["payload_kg"] / step)
    ok, _ = vehicle.payload_checks(k * step, edition)
    ko, _ = vehicle.payload_checks((k + 1) * step, edition)
    assert all(v >= 0 for v in ok.values())
    assert any(v < 0 for v in ko.values())
    assert result["limiting_factors"]


def test_fixture_design_qualifies_for_dlc1():
    result = evaluate_vehicle(FIXTURE_DESIGN)
    assert result["feasible"], result["violations"]
    assert result["aircraft_mass_kg"] < 24.94
    assert result["max_payload_kg"] >= 49.9
    assert 3.0 < result["payload_ratio"] < 3.5


def test_same_design_fails_the_longer_dlc2_course():
    result = evaluate_vehicle(FIXTURE_DESIGN, edition="dlc2")
    assert result["max_payload_kg"] < evaluate_vehicle(FIXTURE_DESIGN)["max_payload_kg"]


def test_bad_inputs_return_readable_results():
    unknown = evaluate_vehicle({**FIXTURE_DESIGN, "wings": 2})
    assert unknown["ok"] is False and "inconnus" in unknown["reason"]
    solid_tube = evaluate_vehicle({**FIXTURE_DESIGN, "arm_od_mm": 16.0, "arm_wall_mm": 4.0})
    assert solid_tube["feasible"] is False and solid_tube["score"] < 0
