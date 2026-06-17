import math
import time
from src.config import (
    BASE_CLICK_VALUE, PRICE_SCALE, BOOST,
    GENERATORS, CLICK_UPGRADES,
    PRESTIGE_1_THRESHOLD, PRESTIGE_2_THRESHOLD, VICTORY_THRESHOLD,
)


class GameState:
    def __init__(self):
        self.points: float = 0.0
        self.total_points: float = 0.0
        self.click_value: float = BASE_CLICK_VALUE * BOOST
        self.generators: dict[str, int] = {g["id"]: 0 for g in GENERATORS}
        self.click_upgrades: dict[str, bool] = {u["id"]: False for u in CLICK_UPGRADES}

        # Prestige
        self.prestige_count: int = 0
        self.prestige_multiplier: float = 1.0

        # Minijuego
        self.minigame_active: bool = False
        self.minigame_multiplier: float = 1.0
        self.minigame_end_time: float = 0.0

        # Victoria
        self.won: bool = False
        self.infinite_mode: bool = False
        self.high_score: float = 0.0

        self._last_tick: float = time.time()

    # ── Clic ─────────────────────────────────────────────────────────────────

    def click(self) -> float:
        earned = self.click_value * self.prestige_multiplier * self.minigame_multiplier
        self.points += earned
        self.total_points += earned
        return earned

    # ── Tick pasivo ──────────────────────────────────────────────────────────

    def tick(self) -> float:
        now = time.time()
        dt = now - self._last_tick
        self._last_tick = now

        if self.minigame_active and now >= self.minigame_end_time:
            self.minigame_active = False
            self.minigame_multiplier = 1.0

        earned = self.pps() * dt
        self.points += earned
        self.total_points += earned

        if self.total_points > self.high_score:
            self.high_score = self.total_points

        return earned

    # ── Producción ───────────────────────────────────────────────────────────

    def pps(self) -> float:
        base = sum(
            g["pps"] * self.generators[g["id"]]
            for g in GENERATORS
        )
        return base * BOOST * self.prestige_multiplier * self.minigame_multiplier

    # ── Generadores ──────────────────────────────────────────────────────────

    def generator_cost(self, gen_id: str) -> int:
        base = next(g["cost"] for g in GENERATORS if g["id"] == gen_id)
        owned = self.generators[gen_id]
        return math.ceil(base * (PRICE_SCALE ** owned) * BOOST)

    def generator_unlocked(self, gen_id: str) -> bool:
        threshold = next(g["unlock"] for g in GENERATORS if g["id"] == gen_id)
        return self.total_points >= threshold * BOOST

    def can_buy_generator(self, gen_id: str) -> bool:
        return self.generator_unlocked(gen_id) and self.points >= self.generator_cost(gen_id)

    def buy_generator(self, gen_id: str) -> bool:
        if not self.can_buy_generator(gen_id):
            return False
        self.points -= self.generator_cost(gen_id)
        self.generators[gen_id] += 1
        return True

    # ── Mejoras de clic ──────────────────────────────────────────────────────

    def click_upgrade_cost(self, upg_id: str) -> int:
        base = next(u["cost"] for u in CLICK_UPGRADES if u["id"] == upg_id)
        return math.ceil(base * BOOST)

    def click_upgrade_unlocked(self, upg_id: str) -> bool:
        threshold = next(u["unlock"] for u in CLICK_UPGRADES if u["id"] == upg_id)
        return self.total_points >= threshold * BOOST

    def buy_click_upgrade(self, upg_id: str) -> bool:
        if self.click_upgrades[upg_id]:
            return False
        if not self.click_upgrade_unlocked(upg_id):
            return False
        cost = self.click_upgrade_cost(upg_id)
        if self.points < cost:
            return False
        self.points -= cost
        self.click_upgrades[upg_id] = True
        bonus = next(u["bonus"] for u in CLICK_UPGRADES if u["id"] == upg_id)
        self.click_value += bonus * BOOST
        return True

    # ── Minijuego ────────────────────────────────────────────────────────────

    def activate_minigame(self, multiplier: float = 2.0, duration: float = 30.0):
        self.minigame_active = True
        self.minigame_multiplier = multiplier
        self.minigame_end_time = time.time() + duration

    def minigame_seconds_left(self) -> float:
        if not self.minigame_active:
            return 0.0
        return max(0.0, self.minigame_end_time - time.time())

    # ── Prestige ─────────────────────────────────────────────────────────────

    def can_prestige(self) -> bool:
        if self.prestige_count >= 2:
            return False
        threshold = PRESTIGE_1_THRESHOLD if self.prestige_count == 0 else PRESTIGE_2_THRESHOLD
        return self.total_points >= threshold * BOOST

    def prestige(self) -> bool:
        if not self.can_prestige():
            return False
        self.prestige_count += 1
        if self.prestige_count == 1:
            self.prestige_multiplier *= 1.5
        elif self.prestige_count == 2:
            self.prestige_multiplier *= 2.0

        self.points = 0.0
        self.total_points = 0.0
        self.click_value = BASE_CLICK_VALUE * BOOST
        self.generators = {g["id"]: 0 for g in GENERATORS}
        self.click_upgrades = {u["id"]: False for u in CLICK_UPGRADES}
        self.minigame_active = False
        self.minigame_multiplier = 1.0
        return True

    # ── Victoria ─────────────────────────────────────────────────────────────

    def check_victory(self) -> bool:
        if self.won:
            return False
        if self.prestige_count == 2 and self.total_points >= VICTORY_THRESHOLD * BOOST:
            self.won = True
            self.infinite_mode = True
            return True
        return False

    # ── Estado legible ───────────────────────────────────────────────────────

    def prestige_threshold(self) -> float:
        if self.prestige_count == 0:
            return PRESTIGE_1_THRESHOLD * BOOST
        if self.prestige_count == 1:
            return PRESTIGE_2_THRESHOLD * BOOST
        return VICTORY_THRESHOLD * BOOST

    def prestige_progress_pct(self) -> float:
        threshold = self.prestige_threshold()
        return min(100.0, (self.total_points / threshold) * 100)
