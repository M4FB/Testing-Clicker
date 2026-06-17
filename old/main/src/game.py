import math
import time
from src.config import (
    BASE_CLICK_VALUE, PRICE_SCALE, BOOST,
    GENERATORS, CLICK_UPGRADES, GEN_UPGRADES,
    PRESTIGE_1_THRESHOLD, PRESTIGE_2_THRESHOLD, VICTORY_THRESHOLD,
)


class GameState:
    def __init__(self):
        self.points: float = 0.0
        self.total_points: float = 0.0

        # Valor base por clic + multiplicador acumulado de mejoras de clic
        self.click_value: float = BASE_CLICK_VALUE * BOOST
        self.click_mult:  float = 1.0

        # Generadores y sus multiplicadores individuales / globales
        self.generators:   dict[str, int]   = {g["id"]: 0   for g in GENERATORS}
        self.gen_upgrades: dict[str, bool]  = {u["id"]: False for u in GEN_UPGRADES}
        self.gen_mult:     dict[str, float] = {}   # key = gen_id | "all"

        # Mejoras de clic compradas
        self.click_upgrades: dict[str, bool] = {u["id"]: False for u in CLICK_UPGRADES}

        # Prestige
        self.prestige_count:      int   = 0
        self.prestige_multiplier: float = 1.0

        # Minijuego (booster de PPS ×N por N segundos)
        self.minigame_active:     bool  = False
        self.minigame_multiplier: float = 1.0
        self.minigame_end_time:   float = 0.0

        # Bono QTE (booster extra, independiente del minijuego)
        self.qte_bonus_active: bool  = False
        self.qte_bonus_mult:   float = 1.0
        self.qte_bonus_end:    float = 0.0

        # Victoria
        self.won:          bool  = False
        self.infinite_mode: bool = False
        self.high_score:    float = 0.0

        self._last_tick: float = time.time()

    # ── Clic ─────────────────────────────────────────────────────────────────

    def click(self) -> float:
        earned = (self.click_value * self.click_mult
                  * self.prestige_multiplier
                  * self.minigame_multiplier
                  * self.qte_bonus_mult)
        self.points      += earned
        self.total_points += earned
        return earned

    # ── Tick pasivo ──────────────────────────────────────────────────────────

    def tick(self) -> float:
        now = time.time()
        dt  = now - self._last_tick
        self._last_tick = now

        if self.minigame_active and now >= self.minigame_end_time:
            self.minigame_active     = False
            self.minigame_multiplier = 1.0

        if self.qte_bonus_active and now >= self.qte_bonus_end:
            self.qte_bonus_active = False
            self.qte_bonus_mult   = 1.0

        earned = self.pps() * dt
        self.points       += earned
        self.total_points += earned

        if self.total_points > self.high_score:
            self.high_score = self.total_points

        return earned

    # ── Producción ───────────────────────────────────────────────────────────

    def pps(self) -> float:
        global_m = self.gen_mult.get("all", 1.0)
        base = 0.0
        for g in GENERATORS:
            cnt = self.generators[g["id"]]
            if cnt == 0:
                continue
            gen_m = self.gen_mult.get(g["id"], 1.0)
            base += g["pps"] * cnt * gen_m * global_m
        return (base * BOOST
                * self.prestige_multiplier
                * self.minigame_multiplier
                * self.qte_bonus_mult)

    # ── Generadores ──────────────────────────────────────────────────────────

    def generator_cost(self, gen_id: str) -> int:
        base  = next(g["cost"] for g in GENERATORS if g["id"] == gen_id)
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
        upg = next(u for u in CLICK_UPGRADES if u["id"] == upg_id)

        # Legado: umbral de puntos (solo cu_1 lo usa, con valor 0)
        pts_req = upg.get("unlock", 0)
        if pts_req > 0 and self.total_points < pts_req * BOOST:
            return False

        # Árbol de desbloqueo: se activa si CUALQUIER requisito está comprado
        after = upg.get("unlock_after", [])
        if after:
            return any(self.click_upgrades.get(rid, False) for rid in after)

        return True

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
        upg = next(u for u in CLICK_UPGRADES if u["id"] == upg_id)
        # Bonus flat
        bonus = upg.get("bonus", 0)
        if bonus:
            self.click_value += bonus * BOOST
        # Multiplicador acumulativo
        mult = upg.get("mult", 1.0)
        if mult != 1.0:
            self.click_mult *= mult
        return True

    # ── Mejoras de generadores ────────────────────────────────────────────────

    def gen_upgrade_cost(self, upg_id: str) -> int:
        base = next(u["cost"] for u in GEN_UPGRADES if u["id"] == upg_id)
        return math.ceil(base * BOOST)

    def gen_upgrade_unlocked(self, upg_id: str) -> bool:
        upg = next(u for u in GEN_UPGRADES if u["id"] == upg_id)

        # Requiere tener cierta cantidad de generadores
        for gen_id, min_count in upg.get("unlock_own", {}).items():
            if self.generators.get(gen_id, 0) < min_count:
                return False

        # Requiere haber comprado otras mejoras de generador
        for req_id in upg.get("unlock_after", []):
            if not self.gen_upgrades.get(req_id, False):
                return False

        return True

    def can_buy_gen_upgrade(self, upg_id: str) -> bool:
        return (not self.gen_upgrades.get(upg_id, False)
                and self.gen_upgrade_unlocked(upg_id)
                and self.points >= self.gen_upgrade_cost(upg_id))

    def buy_gen_upgrade(self, upg_id: str) -> bool:
        if self.gen_upgrades.get(upg_id, False):
            return False
        if not self.gen_upgrade_unlocked(upg_id):
            return False
        cost = self.gen_upgrade_cost(upg_id)
        if self.points < cost:
            return False
        self.points -= cost
        self.gen_upgrades[upg_id] = True
        upg    = next(u for u in GEN_UPGRADES if u["id"] == upg_id)
        target = upg["target"]
        mult   = upg["mult"]
        self.gen_mult[target] = self.gen_mult.get(target, 1.0) * mult
        return True

    # ── Minijuego ────────────────────────────────────────────────────────────

    def activate_minigame(self, multiplier: float = 2.0, duration: float = 30.0):
        self.minigame_active     = True
        self.minigame_multiplier = multiplier
        self.minigame_end_time   = time.time() + duration

    def minigame_seconds_left(self) -> float:
        if not self.minigame_active:
            return 0.0
        return max(0.0, self.minigame_end_time - time.time())

    # ── Bono QTE ─────────────────────────────────────────────────────────────

    def activate_qte_bonus(self, multiplier: float = 3.0, duration: float = 60.0):
        self.qte_bonus_active = True
        self.qte_bonus_mult   = multiplier
        self.qte_bonus_end    = time.time() + duration

    def qte_bonus_seconds_left(self) -> float:
        if not self.qte_bonus_active:
            return 0.0
        return max(0.0, self.qte_bonus_end - time.time())

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

        self.points       = 0.0
        self.total_points = 0.0
        self.click_value  = BASE_CLICK_VALUE * BOOST
        self.click_mult   = 1.0
        self.generators   = {g["id"]: 0     for g in GENERATORS}
        self.click_upgrades = {u["id"]: False for u in CLICK_UPGRADES}
        self.gen_upgrades = {u["id"]: False  for u in GEN_UPGRADES}
        self.gen_mult     = {}

        self.minigame_active     = False
        self.minigame_multiplier = 1.0
        self.qte_bonus_active    = False
        self.qte_bonus_mult      = 1.0
        return True

    # ── Victoria ─────────────────────────────────────────────────────────────

    def check_victory(self) -> bool:
        if self.won:
            return False
        if self.prestige_count == 2 and self.total_points >= VICTORY_THRESHOLD * BOOST:
            self.won           = True
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
