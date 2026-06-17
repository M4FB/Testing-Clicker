import pytest
from unittest.mock import patch
from src.game import GameState
from src.config import GENERATORS, CLICK_UPGRADES, BOOST, PRICE_SCALE


# ── Helpers ──────────────────────────────────────────────────────────────────

def game_with_points(pts: float) -> GameState:
    g = GameState()
    g.points = pts
    g.total_points = pts
    return g


# ── Clic básico ───────────────────────────────────────────────────────────────

def test_click_adds_points():
    g = GameState()
    before = g.points
    g.click()
    assert g.points > before

def test_click_returns_earned_value():
    g = GameState()
    earned = g.click()
    assert earned == g.click_value

def test_total_points_accumulates_clicks():
    g = GameState()
    for _ in range(10):
        g.click()
    assert g.total_points == pytest.approx(g.click_value * 10)

def test_click_value_equals_base_times_boost():
    g = GameState()
    from src.config import BASE_CLICK_VALUE
    assert g.click_value == BASE_CLICK_VALUE * BOOST


# ── Generadores ───────────────────────────────────────────────────────────────

def test_buy_generator_without_funds_fails():
    g = GameState()
    g.points = 0
    assert g.buy_generator("worker") is False
    assert g.generators["worker"] == 0

def test_buy_generator_success():
    g = GameState()
    cost = g.generator_cost("worker")
    g.points = cost
    g.total_points = cost
    assert g.buy_generator("worker") is True
    assert g.generators["worker"] == 1
    assert g.points == pytest.approx(0)

def test_buy_generator_deducts_points():
    g = GameState()
    cost = g.generator_cost("worker")
    g.points = cost * 3
    g.total_points = cost * 3
    g.buy_generator("worker")
    assert g.points < cost * 3

def test_generator_cost_scales_with_quantity():
    g = GameState()
    cost_0 = g.generator_cost("worker")
    g.generators["worker"] = 1
    cost_1 = g.generator_cost("worker")
    import math
    base = next(gen["cost"] for gen in GENERATORS if gen["id"] == "worker")
    expected = math.ceil(base * (PRICE_SCALE ** 1) * BOOST)
    assert cost_1 == expected
    assert cost_1 > cost_0

def test_pps_zero_without_generators():
    g = GameState()
    assert g.pps() == pytest.approx(0.0)

def test_pps_one_worker():
    g = GameState()
    cost = g.generator_cost("worker")
    g.points = cost
    g.total_points = cost
    g.buy_generator("worker")
    base_pps = next(gen["pps"] for gen in GENERATORS if gen["id"] == "worker")
    assert g.pps() == pytest.approx(base_pps * BOOST)

def test_pps_multiple_generators():
    g = GameState()
    for gen in GENERATORS:
        g.generators[gen["id"]] = 3
    expected = sum(gen["pps"] * 3 for gen in GENERATORS) * BOOST
    assert g.pps() == pytest.approx(expected)

def test_locked_generator_cannot_be_bought():
    g = GameState()
    g.total_points = 0
    factory_unlock = next(gen["unlock"] for gen in GENERATORS if gen["id"] == "factory")
    assert factory_unlock > 0, "factory debería tener umbral de desbloqueo > 0"
    g.points = 9_999_999
    assert g.buy_generator("factory") is False


# ── Mejoras de clic ───────────────────────────────────────────────────────────

def test_buy_click_upgrade_increases_click_value():
    g = GameState()
    upg = CLICK_UPGRADES[0]
    cost = g.click_upgrade_cost(upg["id"])
    g.points = cost
    g.total_points = cost
    old_cv = g.click_value
    assert g.buy_click_upgrade(upg["id"]) is True
    assert g.click_value > old_cv

def test_buy_click_upgrade_twice_fails():
    g = GameState()
    upg = CLICK_UPGRADES[0]
    cost = g.click_upgrade_cost(upg["id"])
    g.points = cost * 2
    g.total_points = cost * 2
    g.buy_click_upgrade(upg["id"])
    assert g.buy_click_upgrade(upg["id"]) is False

def test_buy_click_upgrade_without_funds_fails():
    g = GameState()
    g.points = 0
    g.total_points = 9_999_999
    assert g.buy_click_upgrade(CLICK_UPGRADES[0]["id"]) is False


# ── Prestige ──────────────────────────────────────────────────────────────────

def test_prestige_not_available_below_threshold():
    g = GameState()
    g.total_points = 0
    assert g.can_prestige() is False

def test_prestige_available_at_threshold():
    from src.config import PRESTIGE_1_THRESHOLD
    g = GameState()
    g.total_points = PRESTIGE_1_THRESHOLD * BOOST
    assert g.can_prestige() is True

def test_prestige_resets_points():
    from src.config import PRESTIGE_1_THRESHOLD
    g = GameState()
    g.points = 999_999
    g.total_points = PRESTIGE_1_THRESHOLD * BOOST
    g.prestige()
    assert g.points == pytest.approx(0.0)
    assert g.total_points == pytest.approx(0.0)

def test_prestige_1_applies_multiplier():
    from src.config import PRESTIGE_1_THRESHOLD
    g = GameState()
    g.total_points = PRESTIGE_1_THRESHOLD * BOOST
    g.prestige()
    assert g.prestige_count == 1
    assert g.prestige_multiplier == pytest.approx(1.5)

def test_prestige_2_applies_combined_multiplier():
    from src.config import PRESTIGE_1_THRESHOLD, PRESTIGE_2_THRESHOLD
    g = GameState()
    g.total_points = PRESTIGE_1_THRESHOLD * BOOST
    g.prestige()
    g.total_points = PRESTIGE_2_THRESHOLD * BOOST
    g.prestige()
    assert g.prestige_count == 2
    assert g.prestige_multiplier == pytest.approx(3.0)  # 1.5 × 2.0

def test_third_prestige_not_possible():
    from src.config import PRESTIGE_1_THRESHOLD, PRESTIGE_2_THRESHOLD
    g = GameState()
    g.total_points = PRESTIGE_1_THRESHOLD * BOOST
    g.prestige()
    g.total_points = PRESTIGE_2_THRESHOLD * BOOST
    g.prestige()
    g.total_points = 999_999_999
    assert g.can_prestige() is False
    assert g.prestige() is False

def test_prestige_resets_generators():
    from src.config import PRESTIGE_1_THRESHOLD
    g = GameState()
    g.generators["worker"] = 5
    g.total_points = PRESTIGE_1_THRESHOLD * BOOST
    g.prestige()
    assert g.generators["worker"] == 0


# ── Victoria ──────────────────────────────────────────────────────────────────

def test_victory_not_triggered_before_two_prestiges():
    from src.config import VICTORY_THRESHOLD
    g = GameState()
    g.total_points = VICTORY_THRESHOLD * BOOST * 10
    assert g.check_victory() is False
    assert g.won is False

def test_victory_triggered_after_two_prestiges():
    from src.config import PRESTIGE_1_THRESHOLD, PRESTIGE_2_THRESHOLD, VICTORY_THRESHOLD
    g = GameState()
    g.total_points = PRESTIGE_1_THRESHOLD * BOOST
    g.prestige()
    g.total_points = PRESTIGE_2_THRESHOLD * BOOST
    g.prestige()
    g.total_points = VICTORY_THRESHOLD * BOOST
    assert g.check_victory() is True
    assert g.won is True
    assert g.infinite_mode is True

def test_victory_only_triggers_once():
    from src.config import PRESTIGE_1_THRESHOLD, PRESTIGE_2_THRESHOLD, VICTORY_THRESHOLD
    g = GameState()
    g.total_points = PRESTIGE_1_THRESHOLD * BOOST
    g.prestige()
    g.total_points = PRESTIGE_2_THRESHOLD * BOOST
    g.prestige()
    g.total_points = VICTORY_THRESHOLD * BOOST
    g.check_victory()
    assert g.check_victory() is False  # segunda llamada no re-dispara


# ── Minijuego ────────────────────────────────────────────────────────────────

def test_minigame_activates_multiplier():
    g = GameState()
    g.activate_minigame(multiplier=2.0, duration=60.0)
    assert g.minigame_active is True
    assert g.minigame_multiplier == pytest.approx(2.0)

def test_minigame_affects_pps():
    g = GameState()
    g.generators["worker"] = 1
    pps_base = g.pps()
    g.activate_minigame(multiplier=2.0, duration=60.0)
    assert g.pps() == pytest.approx(pps_base * 2.0)

def test_minigame_expires():
    import time
    g = GameState()
    g.activate_minigame(multiplier=2.0, duration=0.01)
    time.sleep(0.05)
    g.tick()
    assert g.minigame_active is False
    assert g.minigame_multiplier == pytest.approx(1.0)
