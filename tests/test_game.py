"""[TDD] Lógica del núcleo (GameState)."""
import time

from src.config import BOOST, BASE_CLICK_VALUE, PRESTIGE_1_THRESHOLD
from src.game import GameState, _new_stats


def test_new_state_defaults(state):
    assert state.points == 0.0
    assert state.total_points == 0.0
    assert state.click_value == BASE_CLICK_VALUE * BOOST
    assert all(c == 0 for c in state.generators.values())
    assert "history" in state.stats and state.stats["history"] == []


def test_click_increments(state):
    state.crit_chance = 0.0                 # sin críticos: determinista
    earned, crit = state.click()
    assert crit is False
    assert earned == state.effective_click()
    assert state.points == earned
    assert state.total_points == earned
    assert state.stats["clicks"] == 1


def test_crit_path(state):
    state.crit_chance = 1.0                  # siempre crítico
    earned, crit = state.click()
    assert crit is True
    assert state.stats["crits"] == 1
    assert earned == state.effective_click() * 10.0   # CRIT_MULT


def test_buy_generator_and_pps(state):
    gen = "worker"
    state.points = state.generator_cost(gen)
    assert state.pps() == 0.0
    assert state.buy_generator(gen) is True
    assert state.generators[gen] == 1
    assert state.points == 0.0
    assert state.pps() > 0.0


def test_buy_generator_insufficient(state):
    assert state.buy_generator("worker") is False    # 0 puntos
    assert state.generators["worker"] == 0


def test_cost_grows_with_ownership(state):
    c0 = state.generator_cost("worker")
    state.generators["worker"] = 5
    assert state.generator_cost("worker") > c0


def test_max_affordable_and_buy_n(state):
    state.points = state.generator_cost_n("worker", 3)
    assert state.max_affordable_generators("worker") >= 3
    bought = state.buy_generator_n("worker", 3)
    assert bought == 3
    assert state.generators["worker"] == 3


def test_click_upgrade_applies_bonus(state):
    upg = "cu_1"                              # bonus flat, sin requisitos
    base = state.click_value
    state.points = state.click_upgrade_cost(upg)
    assert state.buy_click_upgrade(upg) is True
    assert state.click_value > base
    assert state.buy_click_upgrade(upg) is False   # ya comprada


def test_click_upgrade_locked_until_prereq(state):
    # cu_3 requiere cu_1 o cu_2
    state.points = 10 ** 9
    assert state.click_upgrade_unlocked("cu_3") is False
    assert state.buy_click_upgrade("cu_3") is False
    state.buy_click_upgrade("cu_1")
    assert state.click_upgrade_unlocked("cu_3") is True


def test_prestige_cycle(state):
    assert state.can_prestige() is False
    state.total_points = PRESTIGE_1_THRESHOLD * BOOST
    state.points = 12345.0
    assert state.can_prestige() is True
    pp_expected = state.prestige_points_earned()
    assert state.prestige() is True
    assert state.prestige_count == 1
    assert state.prestige_points == pp_expected
    assert state.points == 0.0 and state.total_points == 0.0
    assert state.prestige_multiplier == 1.5


def test_prestige_upgrade_effect(state):
    state.prestige_points = 10
    assert state.buy_prestige_upgrade("pp_click") is True
    assert state.perm_click_mult > 1.0
    # reaplicar reconstruye el mismo efecto
    before = state.perm_click_mult
    state.reapply_prestige_upgrades()
    assert state.perm_click_mult == before


def test_tick_accumulates_passive(state):
    state.generators["worker"] = 10
    state._last_tick = time.time() - 1.0     # simula 1 s transcurrido
    earned = state.tick()
    assert earned > 0.0
    assert state.high_score >= state.total_points - 1e-6


def test_victory_requires_two_prestiges(state):
    from src.config import VICTORY_THRESHOLD
    state.prestige_count = 2
    state.total_points = VICTORY_THRESHOLD * BOOST
    assert state.check_victory() is True
    assert state.won and state.infinite_mode
    assert state.check_victory() is False    # no se repite


def test_register_mini_result(state):
    state.register_mini_result("simon", True, 5.0)
    state.register_mini_result("simon", False, 0.0)
    assert state.stats["mini_won"] == 1
    assert state.stats["mini_lost"] == 1
    assert state.stats["mini"]["simon"]["best"] == 5.0


def test_new_stats_independent():
    a, b = _new_stats(), _new_stats()
    a["clicks"] = 5
    assert b["clicks"] == 0          # sin estado compartido
