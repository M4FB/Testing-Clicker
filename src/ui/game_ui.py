"""GameUI: orquestador del juego.

Mantiene el estado (GameState, boosts, eventos) y delega el dibujo y los
rects interactivos en los componentes:

    HeaderBar / draw_status_bar   (ui.header)
    LeftPanel                     (ui.left_panel)
    ShopPanel                     (ui.shop)
    Pause/Victory/Achievements/MiniSelect overlays (ui.overlays)
    QTE + panel                   (ui.qte)
"""
import random
import sys
import time

import pygame

from src.game import GameState
from src.config import (
    GENERATORS, CLICK_UPGRADES, GEN_UPGRADES, PRESTIGE_UPGRADES,
    MODE, MINIGAME_COOLDOWN, QTE_COOLDOWN, BOOST, MINI_SELECT_WINS, CHEATS,
)
from src.fx import (
    BG, BG2, MUTED, GOLD, GREEN, RED, ORANGE, PURPLE,
    clamp, draw_text, vgradient,
    Nebula, StarField, FX, Toasts, Roll,
)
from src.minigames import MINIGAMES
from src.save import save_game, save_prefs
from src.events import GoldenEvents, roll_outcome
from src import achievements as ach
from src import sfx

from src.ui.common import (
    W, H, FPS, SPLIT, PAD, STS_H,
    make_fonts, fmt, is_fullscreen, toggle_fullscreen,
    fade_in_alpha, fade_out,
)
from src.ui.header import HeaderBar, draw_status_bar
from src.ui.left_panel import LeftPanel
from src.ui.shop import ShopPanel
from src.ui.overlays import (
    PauseOverlay, VictoryOverlay, AchievementsOverlay, MiniSelectOverlay,
)
from src.ui.qte import QTE, QTE_KEY_SET, draw_qte_panel
from src.ui.cheats import CheatPanel


class GameUI:
    def __init__(self, screen: pygame.Surface | None = None,
                 music: "pygame.mixer.Sound | None" = None,
                 state: GameState | None = None, elapsed: float = 0.0):
        if screen is None:
            pygame.init()
            self.screen = pygame.display.set_mode((W, H), pygame.SCALED)
        else:
            self.screen = screen
        pygame.display.set_caption(f"Clicker Game  [{MODE.upper()}]")
        self.clock  = pygame.time.Clock()
        self.music  = music
        self.canvas = pygame.Surface((W, H))
        self.F      = make_fonts()

        # ── Juego ─────────────────────────────────────────────────────────────
        self.game       = state if state is not None else GameState()
        self.start_time = time.time() - elapsed
        self._next_autosave  = time.time() + 15.0
        self._next_ach_check = time.time() + 0.5
        self._next_hist      = time.time() + 5.0
        self.HIST_MAX        = 40

        # ── Fondo y efectos ───────────────────────────────────────────────────
        self.bg_grad  = vgradient(W, H, BG, BG2)
        self.nebulas  = [Nebula(W, H) for _ in range(4)]
        self.stars    = StarField(W, H, 130)
        self.fx       = FX()
        self.toasts   = Toasts()
        self.golden   = GoldenEvents(W, H)

        # ── Animaciones de UI ─────────────────────────────────────────────────
        self.roll_points = Roll()
        self.roll_pps    = Roll()
        self.ripples: list[dict] = []
        self.click_anim     = 0.0
        self.click_anim_end = 0.0
        self.combo      = 0
        self.last_click = 0.0

        # ── Minijuegos ────────────────────────────────────────────────────────
        self.next_minigame  = time.time() + MINIGAME_COOLDOWN
        self.mini_available = False
        self.mini           = None
        self.mini_select    = False
        self._mini_applied  = False
        self._boost_total   = 30.0
        self._qte_total     = 60.0
        self._golden_total  = 15.0

        # ── QTE ───────────────────────────────────────────────────────────────
        self.qte: QTE | None = None
        self._next_qte       = time.time() + QTE_COOLDOWN

        # ── Overlays / estado de navegación ───────────────────────────────────
        self.paused            = False
        self.show_achievements = False
        self.victory_dismissed = False
        self._exit_to: str | None = None

        # ── Cheat Table (solo si CHEAT_TABLE=on) ──────────────────────────────
        self.cheats_open  = False
        self.cheat_panel  = CheatPanel(self) if CHEATS else None

        # ── Compra múltiple ───────────────────────────────────────────────────
        self.buy_qty: int | str = 1          # 1 | 10 | "max"

        # ── Componentes ───────────────────────────────────────────────────────
        self.header      = HeaderBar(self)
        self.left        = LeftPanel(self)
        self.shop        = ShopPanel(self)
        self.pause_ovl   = PauseOverlay(self)
        self.victory_ovl = VictoryOverlay(self)
        self.ach_ovl     = AchievementsOverlay(self)
        self.select_ovl  = MiniSelectOverlay(self)

        self._prev_time = time.time()
        self._fade_in   = time.time()

    # ─────────────────────────────────────────────────────────────────────────
    # Loop principal
    # ─────────────────────────────────────────────────────────────────────────
    def run(self) -> str:
        while True:
            events = pygame.event.get()
            mx, my = pygame.mouse.get_pos()
            self._handle_events(events, mx, my)
            if self._exit_to:
                if self._exit_to == "menu":
                    fade_out(self.screen, self.clock, 0.28)
                return self._exit_to
            if not self.paused:
                self._update()
            self._draw()
            self.clock.tick(FPS)

    # ─────────────────────────────────────────────────────────────────────────
    # Eventos
    # ─────────────────────────────────────────────────────────────────────────
    def _handle_events(self, events, mx, my):
        for event in events:
            if event.type == pygame.QUIT:
                self._save()
                pygame.quit(); sys.exit()

            # Pantalla completa: funciona en cualquier estado
            if event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                self.toggle_fullscreen()
                continue

            # Cheat Table (F1): solo si CHEAT_TABLE=on
            if self.cheat_panel is not None:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_F1:
                    self.cheats_open = not self.cheats_open
                    continue
                if self.cheats_open:
                    if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                        self.cheats_open = False
                    elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        self.cheat_panel.click(mx, my)
                    continue

            # Victoria: clic para cerrar overlay
            if self.game.won and not self.victory_dismissed:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.victory_dismissed = True
                continue

            # Pausa
            if self.paused:
                self._handle_pause_event(event, mx, my)
                continue

            # Vitrina de logros
            if self.show_achievements:
                if event.type == pygame.KEYDOWN and \
                        event.key in (pygame.K_ESCAPE, pygame.K_l):
                    self.show_achievements = False
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 \
                        and self.ach_ovl.click_outside(mx, my):
                    self.show_achievements = False
                continue

            # Selector de minijuego
            if self.mini_select:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.mini_select = False        # conserva el minijuego
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    cls = self.select_ovl.click(mx, my)
                    if cls:
                        self.mini_select = False
                        self._start_minigame(cls)
                continue

            # Minijuego modal: bloquea el resto del input
            if self.mini:
                if (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE
                        and not self.mini.finished):
                    self.mini = None
                    self.toasts.add("Minijuego cancelado", MUTED, 2.0)
                else:
                    self.mini.event(event, mx, my)
                continue

            # QTE: intercepta teclas de letra (no bloquea mouse)
            if self.qte and not self.qte.done and not self.qte.expired \
                    and not self.qte.failed:
                if event.type == pygame.KEYDOWN:
                    kn = pygame.key.name(event.key).upper()
                    if len(kn) == 1 and kn in QTE_KEY_SET:
                        self._handle_qte_key(kn)
                        continue

            # Scroll panel derecho
            if event.type == pygame.MOUSEWHEEL and mx > SPLIT:
                self.shop.wheel(event.y)

            # Teclado juego
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.paused = True
                    if self.music:
                        self.music.duck(0.4)      # misma música, más bajita
                    self._save()
                    self.toasts.add("Partida guardada", MUTED, 1.6)
                elif event.key == pygame.K_SPACE:
                    self._do_click(mx, my)
                elif event.key == pygame.K_p:
                    self._do_prestige()
                elif event.key == pygame.K_l:
                    self.toggle_achievements()

            # Ratón juego
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # La moneda dorada tiene prioridad sobre todo
                coin = self.golden.coin
                if coin and coin.hit(mx, my):
                    pos = (coin.x, coin.y)
                    self.golden.try_click(mx, my)
                    self._golden_caught(pos)
                    continue
                if self.header.click(mx, my):
                    continue
                if self.left.click_rect and self.left.click_rect.collidepoint(mx, my):
                    self._do_click(mx, my)
                    continue
                if self.left.prestige_rect and \
                        self.left.prestige_rect.collidepoint(mx, my):
                    self._do_prestige()
                    continue
                if self.left.mini_rect and self.left.mini_rect.collidepoint(mx, my):
                    self._open_minigame()
                    continue
                self.shop.click(mx, my)

    def _unpause(self):
        self.paused = False
        if self.music:
            self.music.unduck()

    def _handle_pause_event(self, event, mx, my):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._unpause()
            elif event.key == pygame.K_LEFT and self.music:
                self.music.set_volume(max(0.0, self.music.get_volume() - 0.05))
                self._save_prefs()
            elif event.key == pygame.K_RIGHT and self.music:
                self.music.set_volume(min(1.0, self.music.get_volume() + 0.05))
                self._save_prefs()
            elif event.key == pygame.K_UP:
                sfx.set_volume(sfx.get_volume() + 0.05)
                sfx.play("tick")
                self._save_prefs()
            elif event.key == pygame.K_DOWN:
                sfx.set_volume(sfx.get_volume() - 0.05)
                sfx.play("tick")
                self._save_prefs()
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            action = self.pause_ovl.click(mx, my)
            if action == "resume":
                self._unpause()
            elif action == "fullscreen":
                self.toggle_fullscreen()
            elif action == "menu":
                self._unpause()
                self._save()
                self._exit_to = "menu"
            elif action == "quit":
                self._save()
                pygame.quit(); sys.exit()

    # ─────────────────────────────────────────────────────────────────────────
    # Update
    # ─────────────────────────────────────────────────────────────────────────
    def _update(self):
        now = time.time()
        dt  = min(0.05, now - self._prev_time)
        self._prev_time = now

        self.game.tick()
        if self.game.check_victory():
            self.fx.confetti_burst(W, 130)
            self.fx.add_shake(0.5)
            self.toasts.add("★ ¡VICTORIA! Modo infinito desbloqueado", GOLD, 5.0)
            sfx.play("fanfare")

        # Autoguardado periódico
        if now >= self._next_autosave:
            self._save()
            self._next_autosave = now + 30.0

        # Muestreo del histórico para el sparkline del menú
        if now >= self._next_hist:
            self._next_hist = now + 6.0
            hist = self.game.stats.setdefault("history", [])
            hist.append(round(self.game.total_points, 2))
            if len(hist) > self.HIST_MAX:
                del hist[:-self.HIST_MAX]

        # Logros
        if now >= self._next_ach_check:
            self._next_ach_check = now + 0.5
            for a in ach.check(self.game):
                self.toasts.add(f"★ LOGRO: {a['name']}", GOLD, 4.0)
                self.fx.confetti_burst(W, 40)
                sfx.play("logro")

        # Minijuego disponible
        if not self.mini_available and self.mini is None and now >= self.next_minigame:
            self.mini_available = True
            sfx.play("coin", 0.6)

        # Minijuego activo
        if self.mini:
            self.mini.update(now, dt)
            if self.mini.finished and not self._mini_applied:
                self._mini_applied = True
                won = self.mini.reward is not None
                self.game.register_mini_result(self.mini.KEY, won,
                                               self.mini.score_value())
                if won:
                    mult, dur = self.mini.reward
                    dur *= self.game.boost_dur_mult
                    self.game.activate_minigame(mult, dur)
                    self._boost_total = dur
                    self.fx.confetti_burst(W, 50)
                    self.toasts.add(f"★ Boost ×{mult:.1f} por {dur:.0f}s", PURPLE, 4.0)
                    sfx.play("win")
                else:
                    self.toasts.add(self.mini.result_msg, RED, 3.0)
                    sfx.play("fail", 0.7)
            if self.mini.finished and now >= self.mini.close_at:
                self.mini = None

        # Moneda dorada (no aparece bajo modales)
        blocked = bool(self.mini or self.mini_select or self.show_achievements
                       or (self.game.won and not self.victory_dismissed))
        self.golden.update(now, dt, freq_factor=self.game.golden_freq,
                           blocked=blocked)

        # QTE: limpiar expirado/fallado
        if self.qte:
            if self.qte.expired or (self.qte.failed and now >= self.qte.fail_until):
                if self.qte.expired and not self.qte.failed:
                    self.toasts.add("QTE expirado. ¡Más rápido!", MUTED, 2.0)
                self.qte       = None
                self._next_qte = now + QTE_COOLDOWN

        # QTE: spawn
        if self.qte is None and now >= self._next_qte and self.mini is None:
            keys = list(QTE_KEY_SET)
            random.shuffle(keys)
            self.qte = QTE(sequence=keys[:8])

        # Efectos
        self.fx.update(dt)
        self.stars.update(dt)
        for n in self.nebulas:
            n.update(dt)
        self.roll_points.tick(self.game.points, dt)
        self.roll_pps.tick(self.game.pps(), dt)

        # Brasas en el botón con combo alto
        if (self.combo >= 20 and now - self.last_click <= 0.9
                and self.left.click_rect and random.random() < dt * 9):
            r = self.left.click_rect
            self.fx.ember_burst(random.uniform(r.x + 14, r.right - 14),
                                r.bottom - 6, ORANGE, n=3, spread=8)

        self.ripples = [r for r in self.ripples if now - r["born"] < 0.5]

        if now < self.click_anim_end:
            self.click_anim = clamp((self.click_anim_end - now) / 0.12, 0, 1)
        else:
            self.click_anim = 0.0
        if now - self.last_click > 0.9:
            self.combo = 0

        self.shop.update(dt)

    # ─────────────────────────────────────────────────────────────────────────
    # Acciones de juego
    # ─────────────────────────────────────────────────────────────────────────
    def _do_click(self, mx, my):
        now = time.time()
        earned, crit = self.game.click()
        if self.left.click_rect and self.left.click_rect.collidepoint(mx, my):
            cx, cy = mx, my
        elif self.left.click_rect:
            cx, cy = self.left.click_rect.center
        else:
            cx, cy = mx, my

        self.combo = self.combo + 1 if now - self.last_click <= 0.9 else 1
        self.last_click = now
        if self.combo > self.game.stats["best_combo"]:
            self.game.stats["best_combo"] = self.combo

        if crit:
            self.fx.float_text(cx, cy - 22, f"¡CRÍTICO! +{fmt(earned)}", GOLD, big=True)
            self.fx.sparks_burst(cx, cy, GOLD, 24, 280)
            self.fx.ring(cx, cy, GOLD, max_r=95, width=4)
            self.fx.add_shake(0.28)
            sfx.play("crit", 0.9)
        else:
            big = self.combo > 0 and self.combo % 25 == 0
            self.fx.float_text(cx, cy - 16, f"+{fmt(earned)}", GOLD, big=big)
            self.fx.sparks_burst(cx, cy, GOLD, 6 if not big else 18, 170)
            if big:
                self.fx.add_shake(0.18)
            sfx.play("click", 0.7)
        self.ripples.append({"x": cx, "y": cy, "born": now})
        self.click_anim_end = now + 0.12

    def set_buy_qty(self, val):
        self.buy_qty = val
        sfx.play("tick", 0.6)

    def buy_generator(self, idx):
        gen = GENERATORS[idx]
        g   = self.game
        if not g.generator_unlocked(gen["id"]):
            self.toasts.add(f"{gen['name']}: bloqueado", RED)
            sfx.play("error", 0.5)
            return
        n = g.max_affordable_generators(gen["id"]) if self.buy_qty == "max" \
            else self.buy_qty
        if n == 0 or g.points < g.generator_cost_n(gen["id"], n):
            want  = 1 if self.buy_qty == "max" else self.buy_qty
            falta = g.generator_cost_n(gen["id"], want) - g.points
            self.toasts.add(f"Faltan {fmt(falta)} pts (×{want})", RED)
            sfx.play("error", 0.5)
            return
        bought = g.buy_generator_n(gen["id"], n)
        total  = g.generators[gen["id"]]
        self.toasts.add(f"✓ {gen['name']} +{bought}  (total ×{total})", GREEN)
        sfx.play("buy")
        r = self.shop.gen_rects[idx]
        if r:
            self.fx.sparks_burst(r.centerx, r.centery, GREEN,
                                 12 + min(18, bought * 2), 190)

    def buy_gen_upgrade(self, idx):
        gu = GEN_UPGRADES[idx]
        if self.game.buy_gen_upgrade(gu["id"]):
            tgt = next((g["name"] for g in GENERATORS if g["id"] == gu["target"]),
                       "todos")
            self.toasts.add(f"✓ {gu['name']} — ×{gu['mult']} {tgt}", ORANGE)
            sfx.play("upgrade")
            r = self.shop.gu_rects[idx]
            if r:
                self.fx.sparks_burst(r.centerx, r.centery, ORANGE, 12, 190)
        elif self.game.gen_upgrades.get(gu["id"]):
            self.toasts.add("Ya activo.", MUTED)
        else:
            falta = self.game.gen_upgrade_cost(gu["id"]) - self.game.points
            self.toasts.add(f"Faltan {fmt(falta)} pts", RED)
            sfx.play("error", 0.5)

    def buy_upgrade(self, idx):
        upg = CLICK_UPGRADES[idx]
        if self.game.buy_click_upgrade(upg["id"]):
            bonus, mult = upg.get("bonus", 0), upg.get("mult", 1.0)
            parts = []
            if bonus:       parts.append(f"+{fmt(bonus*BOOST)}/clic")
            if mult != 1.0: parts.append(f"×{mult:.1f}")
            self.toasts.add(f"✓ {upg['name']}  {' '.join(parts)}", GREEN)
            sfx.play("upgrade")
            r = self.shop.upg_rects[idx]
            if r:
                self.fx.sparks_burst(r.centerx, r.centery, GREEN, 12, 190)
        elif self.game.click_upgrades[upg["id"]]:
            self.toasts.add("Ya tienes esa mejora.", MUTED)
        elif not self.game.click_upgrade_unlocked(upg["id"]):
            self.toasts.add(f"{upg['name']}: bloqueado", RED)
        else:
            falta = self.game.click_upgrade_cost(upg["id"]) - self.game.points
            self.toasts.add(f"Faltan {fmt(falta)} pts", RED)
            sfx.play("error", 0.5)

    def buy_prestige_upgrade(self, idx):
        pu = PRESTIGE_UPGRADES[idx]
        if self.game.buy_prestige_upgrade(pu["id"]):
            self.toasts.add(f"★ {pu['name']} — permanente", PURPLE, 4.0)
            sfx.play("upgrade")
            r = self.shop.pp_rects[idx]
            if r:
                self.fx.sparks_burst(r.centerx, r.centery, PURPLE, 14, 200)
        elif self.game.prestige_upgrades.get(pu["id"]):
            self.toasts.add("Ya activo.", MUTED)
        else:
            falta = pu["cost"] - self.game.prestige_points
            self.toasts.add(f"Faltan {falta} PP (se ganan con prestige)", RED)
            sfx.play("error", 0.5)

    def _do_prestige(self):
        if self.game.can_prestige():
            n  = self.game.prestige_count + 1
            pp = self.game.prestige_points_earned()
            self.game.prestige()
            self.toasts.add(f"★ Prestige {n}!  +{pp} PP — "
                            f"mult ×{self.game.prestige_multiplier:.1f}",
                            GOLD, 4.5)
            self.fx.confetti_burst(W, 110)
            self.fx.add_shake(0.45)
            self.combo = 0
            sfx.play("fanfare")

    # ─────────────────────────────────────────────────────────────────────────
    # Moneda dorada
    # ─────────────────────────────────────────────────────────────────────────
    def _golden_caught(self, pos):
        g = self.game
        g.stats["golden"] += 1
        self.golden.schedule_next(g.golden_freq)
        x, y = pos
        self.fx.sparks_burst(x, y, GOLD, 26, 300)
        self.fx.ring(x, y, GOLD, max_r=130, width=4, life=0.6)
        self.fx.add_shake(0.2)
        sfx.play("golden")

        outcome = roll_outcome()
        if outcome == "rafaga":
            gain = max(g.pps() * 60, g.effective_click() * 75)
            g.points       += gain
            g.total_points += gain
            self.fx.float_text(x, y - 24, f"¡RÁFAGA! +{fmt(gain)}", GOLD, big=True)
            self.toasts.add(f"☀ Moneda dorada: ¡ráfaga de +{fmt(gain)} pts!",
                            GOLD, 4.5)
        elif outcome == "fiebre":
            dur = 15.0 * g.boost_dur_mult
            g.activate_golden(7.0, dur)
            self._golden_total = dur
            self.fx.float_text(x, y - 24, "¡FIEBRE ×7!", GOLD, big=True)
            self.fx.confetti_burst(W, 60)
            self.toasts.add(f"☀ ¡FIEBRE DORADA!  ×7 durante {dur:.0f}s", GOLD, 4.5)
        else:   # "mini"
            self.mini_available = True
            self.fx.float_text(x, y - 24, "¡MINIJUEGO!", PURPLE, big=True)
            self.toasts.add("☀ Moneda dorada: ¡minijuego disponible ya!",
                            PURPLE, 4.5)

    # ─────────────────────────────────────────────────────────────────────────
    # Minijuegos
    # ─────────────────────────────────────────────────────────────────────────
    def can_select_minigame(self) -> bool:
        return self.game.stats["mini_won"] >= MINI_SELECT_WINS

    def _open_minigame(self):
        if not self.mini_available:
            return
        if self.can_select_minigame():
            self.mini_select = True
            sfx.play("tick", 0.7)
        else:
            self._start_minigame(random.choice(MINIGAMES))

    def _start_minigame(self, cls):
        self.mini_available = False
        self.next_minigame  = time.time() + MINIGAME_COOLDOWN
        mw, mh = cls.MODAL
        rect   = pygame.Rect((W - mw) // 2, (H - mh) // 2, mw, mh)
        self.mini          = cls(rect, self.fx)
        self._mini_applied = False

    # ─────────────────────────────────────────────────────────────────────────
    # QTE
    # ─────────────────────────────────────────────────────────────────────────
    def _handle_qte_key(self, key):
        if not self.qte or self.qte.done or self.qte.expired:
            return
        if key == self.qte.sequence[self.qte.current]:
            self.qte.current += 1
            sfx.play("tick", 0.6)
            if self.qte.done:
                self.game.activate_qte_bonus(3.0, 60.0)
                self.game.stats["qte_won"] += 1
                self._qte_total = 60.0
                self.toasts.add("¡QTE COMPLETADO!  Bonus ×3 por 60s", PURPLE, 5.0)
                self.fx.confetti_burst(W, 60)
                sfx.play("win")
                self.qte       = None
                self._next_qte = time.time() + QTE_COOLDOWN
        else:
            self.qte.failed     = True
            self.qte.fail_until = time.time() + 1.5
            self.game.stats["qte_fail"] += 1
            self.fx.add_shake(0.25)
            self.toasts.add("QTE fallado.", RED, 2.0)
            sfx.play("fail", 0.7)

    # ─────────────────────────────────────────────────────────────────────────
    # Otros
    # ─────────────────────────────────────────────────────────────────────────
    def toggle_achievements(self):
        self.show_achievements = not self.show_achievements
        sfx.play("tick", 0.6)

    def toggle_fullscreen(self):
        full = toggle_fullscreen()
        self.toasts.add("Pantalla completa" if full else "Modo ventana",
                        MUTED, 1.6)

    def _save_prefs(self):
        try:
            save_prefs(music_vol=self.music.get_volume() if self.music else None,
                       sfx_vol=sfx.get_volume(), fullscreen=is_fullscreen())
        except OSError:
            pass

    def _save(self):
        try:
            save_game(self.game,
                      elapsed=time.time() - self.start_time,
                      music_vol=self.music.get_volume() if self.music else None,
                      sfx_vol=sfx.get_volume(),
                      fullscreen=is_fullscreen())
        except OSError:
            pass

    # ─────────────────────────────────────────────────────────────────────────
    # Dibujo
    # ─────────────────────────────────────────────────────────────────────────
    def _draw(self):
        cv = self.canvas
        cv.blit(self.bg_grad, (0, 0))
        for n in self.nebulas:
            n.draw(cv)
        self.stars.draw(cv)

        mx, my = pygame.mouse.get_pos()
        self.header.draw(cv, mx, my)
        self.left.draw(cv, mx, my)
        self.shop.draw(cv, mx, my)
        pygame.draw.line(cv, (52, 60, 78), (SPLIT, 50), (SPLIT, H - STS_H), 1)
        draw_status_bar(self, cv)

        self.golden.draw(cv)

        if self.mini:
            overlay = pygame.Surface((W, H), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 165))
            cv.blit(overlay, (0, 0))
            self.mini.draw(cv, self.F, mx, my)

        if self.qte:
            draw_qte_panel(self, cv)

        self.fx.draw(cv, self.F["part"], self.F["part2"])

        if self.game.won and not self.victory_dismissed:
            self.victory_ovl.draw(cv)
        if self.mini_select:
            self.select_ovl.draw(cv, mx, my)
        if self.show_achievements:
            self.ach_ovl.draw(cv, mx, my)
        if self.paused:
            self.pause_ovl.draw(cv, mx, my)

        # Cheat Table: panel encima de todo, o un pequeño distintivo si está oculta
        if self.cheat_panel is not None:
            if self.cheats_open:
                self.cheat_panel.draw(cv, mx, my)
            else:
                draw_text(cv, "⚙ CHEATS · F1", self.F["xs"], RED, 8, 54)

        self.toasts.draw(cv, self.F["sm"], PAD, H - STS_H - 6)

        self.screen.fill(BG)
        self.screen.blit(cv, self.fx.offset())

        a = fade_in_alpha(self._fade_in, 0.30)
        if a > 0:
            veil = pygame.Surface((W, H))
            veil.fill((0, 0, 0))
            veil.set_alpha(a)
            self.screen.blit(veil, (0, 0))
        pygame.display.flip()


def main():
    pygame.init()
    ui = GameUI()
    ui.run()
