import math
import random
import time
from src.config import (
    BASE_CLICK_VALUE, PRICE_SCALE, BOOST,
    GENERATORS, CLICK_UPGRADES, GEN_UPGRADES, PRESTIGE_UPGRADES,
    PRESTIGE_1_THRESHOLD, PRESTIGE_2_THRESHOLD, VICTORY_THRESHOLD,
    CRIT_CHANCE, CRIT_MULT,
)


def _new_stats() -> dict:
    return {
        "clicks": 0, "crits": 0, "best_combo": 0,
        "golden": 0, "qte_won": 0, "qte_fail": 0,
        "mini_won": 0, "mini_lost": 0,
        "mini": {},          # clave de minijuego → {"won", "lost", "best"}
        "prestiges": 0,
    }


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

        # Puntos y mejoras permanentes de prestigio
        self.prestige_points: int = 0
        self.prestige_upgrades: dict[str, bool] = {u["id"]: False
                                                   for u in PRESTIGE_UPGRADES}
        self.perm_pps_mult:   float = 1.0
        self.perm_click_mult: float = 1.0
        self.crit_chance:     float = CRIT_CHANCE
        self.golden_freq:     float = 1.0    # factor sobre el cooldown dorado
        self.boost_dur_mult:  float = 1.0    # factor sobre duración de boosts
        self.start_workers:   int   = 0      # trabajadores tras cada prestige

        # Minijuego (booster de PPS ×N por N segundos)
        self.minigame_active:     bool  = False
        self.minigame_multiplier: float = 1.0
        self.minigame_end_time:   float = 0.0

        # Bono QTE (booster extra, independiente del minijuego)
        self.qte_bonus_active: bool  = False
        self.qte_bonus_mult:   float = 1.0
        self.qte_bonus_end:    float = 0.0

        # Fiebre dorada (evento de moneda dorada)
        self.golden_active: bool  = False
        self.golden_mult:   float = 1.0
        self.golden_end:    float = 0.0

        # Estadísticas de la partida y logros desbloqueados
        self.stats: dict = _new_stats()
        self.achievements: dict[str, bool] = {}

        # Victoria
        self.won:          bool  = False
        self.infinite_mode: bool = False
        self.high_score:    float = 0.0

        self._last_tick: float = time.time()

    # ── Multiplicador combinado de boosts temporales + permanentes ──────────

    def _boosts(self) -> float:
        return (self.prestige_multiplier * self.minigame_multiplier
                * self.qte_bonus_mult * self.golden_mult)

    def effective_click(self) -> float:
        return (self.click_value * self.click_mult * self.perm_click_mult
                * self._boosts())

    # ── Clic ─────────────────────────────────────────────────────────────────

    def click(self) -> tuple[float, bool]:
        """Suma el clic (con posible crítico). Devuelve (ganado, fue_crítico)."""
        earned = self.effective_click()
        crit   = random.random() < self.crit_chance
        if crit:
            earned *= CRIT_MULT
            self.stats["crits"] += 1
        self.stats["clicks"] += 1
        self.points       += earned
        self.total_points += earned
        return earned, crit

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

        if self.golden_active and now >= self.golden_end:
            self.golden_active = False
            self.golden_mult   = 1.0

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
        return base * BOOST * self.perm_pps_mult * self._boosts()

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

    # ── Compra múltiple ──────────────────────────────────────────────────────

    def generator_cost_n(self, gen_id: str, n: int) -> int:
        """Coste total de comprar n unidades seguidas (suma de ceils por unidad)."""
        base  = next(g["cost"] for g in GENERATORS if g["id"] == gen_id)
        owned = self.generators[gen_id]
        return sum(math.ceil(base * (PRICE_SCALE ** (owned + i)) * BOOST)
                   for i in range(n))

    def max_affordable_generators(self, gen_id: str, cap: int = 200) -> int:
        """Cuántas unidades seguidas alcanzan los puntos actuales (máx. cap)."""
        if not self.generator_unlocked(gen_id):
            return 0
        base  = next(g["cost"] for g in GENERATORS if g["id"] == gen_id)
        owned = self.generators[gen_id]
        pts   = self.points
        cnt   = 0
        while cnt < cap:
            c = math.ceil(base * (PRICE_SCALE ** (owned + cnt)) * BOOST)
            if pts < c:
                break
            pts -= c
            cnt += 1
        return cnt

    def buy_generator_n(self, gen_id: str, n: int) -> int:
        """Compra hasta n unidades; devuelve cuántas se compraron."""
        bought = 0
        for _ in range(n):
            if not self.buy_generator(gen_id):
                break
            bought += 1
        return bought

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

    def register_mini_result(self, key: str, won: bool, score: float = 0.0):
        """Acumula victorias/derrotas y mejor marca por minijuego."""
        st = self.stats["mini"].setdefault(key, {"won": 0, "lost": 0, "best": 0.0})
        if won:
            st["won"] += 1
            self.stats["mini_won"] += 1
        else:
            st["lost"] += 1
            self.stats["mini_lost"] += 1
        if score > st["best"]:
            st["best"] = score

    # ── Bono QTE ─────────────────────────────────────────────────────────────

    def activate_qte_bonus(self, multiplier: float = 3.0, duration: float = 60.0):
        self.qte_bonus_active = True
        self.qte_bonus_mult   = multiplier
        self.qte_bonus_end    = time.time() + duration

    def qte_bonus_seconds_left(self) -> float:
        if not self.qte_bonus_active:
            return 0.0
        return max(0.0, self.qte_bonus_end - time.time())

    # ── Fiebre dorada ────────────────────────────────────────────────────────

    def activate_golden(self, multiplier: float = 7.0, duration: float = 15.0):
        self.golden_active = True
        self.golden_mult   = multiplier
        self.golden_end    = time.time() + duration

    def golden_seconds_left(self) -> float:
        if not self.golden_active:
            return 0.0
        return max(0.0, self.golden_end - time.time())

    # ── Prestige ─────────────────────────────────────────────────────────────

    def can_prestige(self) -> bool:
        if self.prestige_count >= 2:
            return False
        threshold = PRESTIGE_1_THRESHOLD if self.prestige_count == 0 else PRESTIGE_2_THRESHOLD
        return self.total_points >= threshold * BOOST

    def prestige_points_earned(self) -> int:
        """PP que daría reiniciar ahora: 2 por llegar al umbral, +2 por cada
        múltiplo extra del umbral acumulado, máximo 6."""
        ratio = self.total_points / max(1.0, self.prestige_threshold())
        return max(2, min(6, int(2 * ratio)))

    def prestige(self) -> bool:
        if not self.can_prestige():
            return False
        self.prestige_points += self.prestige_points_earned()
        self.stats["prestiges"] += 1
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

        # Las mejoras de prestigio sobreviven: arranque con trabajadores
        if self.start_workers:
            self.generators["worker"] = self.start_workers

        self.minigame_active     = False
        self.minigame_multiplier = 1.0
        self.qte_bonus_active    = False
        self.qte_bonus_mult      = 1.0
        self.golden_active       = False
        self.golden_mult         = 1.0
        return True

    # ── Mejoras de prestigio ─────────────────────────────────────────────────

    def can_buy_prestige_upgrade(self, upg_id: str) -> bool:
        upg = next(u for u in PRESTIGE_UPGRADES if u["id"] == upg_id)
        return (not self.prestige_upgrades.get(upg_id, False)
                and self.prestige_points >= upg["cost"])

    def buy_prestige_upgrade(self, upg_id: str) -> bool:
        if not self.can_buy_prestige_upgrade(upg_id):
            return False
        upg = next(u for u in PRESTIGE_UPGRADES if u["id"] == upg_id)
        self.prestige_points -= upg["cost"]
        self.prestige_upgrades[upg_id] = True
        self._apply_prestige_effect(upg)
        return True

    def _apply_prestige_effect(self, upg: dict):
        eff, val = upg["effect"], upg["value"]
        if eff == "pps_mult":
            self.perm_pps_mult *= val
        elif eff == "click_mult":
            self.perm_click_mult *= val
        elif eff == "crit_chance":
            self.crit_chance = val
        elif eff == "start_workers":
            self.start_workers = val
        elif eff == "golden_freq":
            self.golden_freq = val
        elif eff == "boost_dur":
            self.boost_dur_mult = val

    def reapply_prestige_upgrades(self):
        """Reconstruye los efectos permanentes desde prestige_upgrades.
        (Se usa al cargar partida: los efectos no se serializan.)"""
        self.perm_pps_mult   = 1.0
        self.perm_click_mult = 1.0
        self.crit_chance     = CRIT_CHANCE
        self.golden_freq     = 1.0
        self.boost_dur_mult  = 1.0
        self.start_workers   = 0
        for upg in PRESTIGE_UPGRADES:
            if self.prestige_upgrades.get(upg["id"], False):
                self._apply_prestige_effect(upg)

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
