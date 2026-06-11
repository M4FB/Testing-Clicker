"""Interfaz pygame del Clicker Game — versión pre-release.

Mejoras sobre la versión estable:
  - Fondo con gradiente, nebulosas y starfield con parallax + estrellas fugaces.
  - Botones con relieve, glow, destello animado y estado presionado.
  - Partículas (chispas, textos flotantes), confeti, screen-shake y toasts.
  - Números rodantes en las estadísticas y combo de clics.
  - 4 minijuegos nuevos con recompensa proporcional al desempeño (src.minigames).
"""
import math
import random
import sys
import time
from dataclasses import dataclass, field

import pygame

from src.game import GameState
from src.config import (
    GENERATORS, CLICK_UPGRADES, GEN_UPGRADES,
    MODE, MINIGAME_COOLDOWN, QTE_COOLDOWN, BOOST,
)
from src.fx import (
    BG, BG2, PANEL, PANEL2, BORDER, TXT, MUTED, ACCENT, GOLD, GOLD_D,
    GREEN, GREEN_D, RED, RED_D, ORANGE, PURPLE,
    clamp, lerp_color, scale_color, ease_out, draw_text, vgradient,
    Nebula, StarField, FX, Toasts, Roll, shiny_button, striped_bar, draw_coin,
)
from src.minigames import MINIGAMES

# ═══════════════════════════════════════════════════════════════════════════════
# Constantes de pantalla
# ═══════════════════════════════════════════════════════════════════════════════
W, H   = 1024, 680
FPS    = 60
SPLIT  = 400
HDR_H  = 50
STS_H  = 30
PAD    = 14

_QTE_KEY_SET = set("ASDFGHJKLZXCVBN")

_FONT_REG  = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
_FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def _f(size, bold=False):
    try:
        return pygame.font.Font(_FONT_BOLD if bold else _FONT_REG, size)
    except Exception:
        return pygame.font.SysFont("sans", size, bold=bold)


def fmt(n: float) -> str:
    if n >= 1e12: return f"{n/1e12:.2f}T"
    if n >= 1e9:  return f"{n/1e9:.2f}B"
    if n >= 1e6:  return f"{n/1e6:.2f}M"
    if n >= 1e3:  return f"{n/1e3:.2f}K"
    return f"{n:.1f}"


def fmt_time(s: float) -> str:
    s = int(s)
    h, rest = divmod(s, 3600)
    m, sec  = divmod(rest, 60)
    return f"{h}h {m:02d}m" if h else f"{m:02d}:{sec:02d}"


def draw_panel(surf, rect, color=PANEL, border=BORDER, radius=9):
    pygame.draw.rect(surf, color, rect, border_radius=radius)
    shine = pygame.Surface((max(1, rect.width - 4), 1), pygame.SRCALPHA)
    shine.fill((255, 255, 255, 16))
    surf.blit(shine, (rect.x + 2, rect.y + 2))
    pygame.draw.rect(surf, border, rect, 1, border_radius=radius)


# ═══════════════════════════════════════════════════════════════════════════════
# QTE
# ═══════════════════════════════════════════════════════════════════════════════
@dataclass
class _QTE:
    sequence:   list
    current:    int   = 0
    start:      float = field(default_factory=time.time)
    duration:   float = 10.0
    failed:     bool  = False
    fail_until: float = 0.0

    @property
    def done(self):      return self.current >= len(self.sequence)
    @property
    def time_left(self): return max(0.0, self.duration - (time.time() - self.start))
    @property
    def expired(self):   return self.time_left <= 0


# ═══════════════════════════════════════════════════════════════════════════════
# GameUI
# ═══════════════════════════════════════════════════════════════════════════════
class GameUI:
    def __init__(self, screen: pygame.Surface | None = None,
                 music: "pygame.mixer.Sound | None" = None):
        if screen is None:
            pygame.init()
            self.screen = pygame.display.set_mode((W, H))
        else:
            self.screen = screen
        pygame.display.set_caption(f"Clicker Game — PRE-RELEASE  [{MODE.upper()}]")
        self.clock  = pygame.time.Clock()
        self.music  = music
        self.canvas = pygame.Surface((W, H))

        # ── Fuentes ───────────────────────────────────────────────────────────
        self.f_title = _f(20, bold=True)
        self.f_big   = _f(32, bold=True)
        self.f_med   = _f(17)
        self.f_sm    = _f(14)
        self.f_xs    = _f(12)
        self.f_btn   = _f(14, bold=True)
        self.f_click = _f(28, bold=True)
        self.f_stat  = _f(16)
        self.f_part  = _f(15, bold=True)
        self.f_part2 = _f(20, bold=True)
        self.F = {"title": self.f_title, "big": self.f_big, "md": self.f_med,
                  "sm": self.f_sm, "xs": self.f_xs, "btn": self.f_btn}

        # ── Juego ─────────────────────────────────────────────────────────────
        self.game       = GameState()
        self.start_time = time.time()

        # ── Fondo y efectos ───────────────────────────────────────────────────
        self.bg_grad  = vgradient(W, H, BG, BG2)
        self.nebulas  = [Nebula(W, H) for _ in range(4)]
        self.stars    = StarField(W, H, 130)
        self.fx       = FX()
        self.toasts   = Toasts()

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
        self._mini_applied  = False
        self._boost_total   = 30.0
        self._qte_total     = 60.0

        # ── QTE ───────────────────────────────────────────────────────────────
        self._qte: _QTE | None = None
        self._next_qte         = time.time() + QTE_COOLDOWN

        # ── Pausa / Victoria ──────────────────────────────────────────────────
        self.paused            = False
        self.victory_dismissed = False
        self._exit_to: str | None = None
        self._pause_resume_rect = None
        self._pause_menu_rect   = None
        self._pause_quit_rect   = None

        # ── Scroll panel derecho (suavizado) ──────────────────────────────────
        self._right_scroll     = 0.0
        self._scroll_target    = 0.0
        self._right_max_scroll = 0

        # ── Rects interactivos ────────────────────────────────────────────────
        self._click_rect:    pygame.Rect | None = None
        self._prestige_rect: pygame.Rect | None = None
        self._mini_rect:     pygame.Rect | None = None
        self._gen_rects:  list = [None] * len(GENERATORS)
        self._gu_rects:   list = [None] * len(GEN_UPGRADES)
        self._upg_rects:  list = [None] * len(CLICK_UPGRADES)

        self._prev_time = time.time()

    # ─────────────────────────────────────────────────────────────────────────
    # Loop principal
    # ─────────────────────────────────────────────────────────────────────────
    def run(self) -> str:
        while True:
            events = pygame.event.get()
            mx, my = pygame.mouse.get_pos()
            self._handle_events(events, mx, my)
            if self._exit_to:
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
                pygame.quit(); sys.exit()

            # Victoria: clic para cerrar overlay
            if self.game.won and not self.victory_dismissed:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.victory_dismissed = True
                continue

            # Pausa
            if self.paused:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.paused = False
                    elif event.key == pygame.K_LEFT and self.music:
                        self.music.set_volume(max(0.0, self.music.get_volume() - 0.05))
                    elif event.key == pygame.K_RIGHT and self.music:
                        self.music.set_volume(min(1.0, self.music.get_volume() + 0.05))
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self._pause_resume_rect and self._pause_resume_rect.collidepoint(mx, my):
                        self.paused = False
                    if self._pause_menu_rect and self._pause_menu_rect.collidepoint(mx, my):
                        self._exit_to = "menu"
                    if self._pause_quit_rect and self._pause_quit_rect.collidepoint(mx, my):
                        pygame.quit(); sys.exit()
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
            if self._qte and not self._qte.done and not self._qte.expired and not self._qte.failed:
                if event.type == pygame.KEYDOWN:
                    kn = pygame.key.name(event.key).upper()
                    if len(kn) == 1 and kn in _QTE_KEY_SET:
                        self._handle_qte_key(kn)
                        continue

            # Scroll panel derecho
            if event.type == pygame.MOUSEWHEEL and mx > SPLIT:
                self._scroll_target = clamp(
                    self._scroll_target - event.y * 42, 0, self._right_max_scroll)

            # Teclado juego
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.paused = True
                elif event.key == pygame.K_SPACE:
                    self._do_click(mx, my)
                elif event.key == pygame.K_p:
                    self._do_prestige()

            # Ratón juego
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self._click_rect and self._click_rect.collidepoint(mx, my):
                    self._do_click(mx, my)
                if self._prestige_rect and self._prestige_rect.collidepoint(mx, my):
                    self._do_prestige()
                if self._mini_rect and self._mini_rect.collidepoint(mx, my):
                    self._open_minigame()
                for i, r in enumerate(self._gen_rects):
                    if r and r.collidepoint(mx, my):
                        self._buy_generator(i)
                for i, r in enumerate(self._gu_rects):
                    if r and r.collidepoint(mx, my):
                        self._buy_gen_upgrade(i)
                for i, r in enumerate(self._upg_rects):
                    if r and r.collidepoint(mx, my):
                        self._buy_upgrade(i)

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

        # Minijuego disponible
        if not self.mini_available and self.mini is None and now >= self.next_minigame:
            self.mini_available = True

        # Minijuego activo
        if self.mini:
            self.mini.update(now, dt)
            if self.mini.finished and not self._mini_applied:
                self._mini_applied = True
                if self.mini.reward:
                    mult, dur = self.mini.reward
                    self.game.activate_minigame(mult, dur)
                    self._boost_total = dur
                    self.fx.confetti_burst(W, 50)
                    self.toasts.add(f"★ Boost ×{mult:.1f} por {dur:.0f}s", PURPLE, 4.0)
                else:
                    self.toasts.add(self.mini.result_msg, RED, 3.0)
            if self.mini.finished and now >= self.mini.close_at:
                self.mini = None

        # QTE: limpiar expirado/fallado
        if self._qte:
            if self._qte.expired or (self._qte.failed and now >= self._qte.fail_until):
                if self._qte.expired and not self._qte.failed:
                    self.toasts.add("QTE expirado. ¡Más rápido!", MUTED, 2.0)
                self._qte      = None
                self._next_qte = now + QTE_COOLDOWN

        # QTE: spawn
        if self._qte is None and now >= self._next_qte and self.mini is None:
            keys = list(_QTE_KEY_SET)
            random.shuffle(keys)
            self._qte = _QTE(sequence=keys[:8])

        # Efectos
        self.fx.update(dt)
        self.stars.update(dt)
        for n in self.nebulas:
            n.update(dt)
        self.roll_points.tick(self.game.points, dt)
        self.roll_pps.tick(self.game.pps(), dt)

        self.ripples = [r for r in self.ripples if now - r["born"] < 0.5]

        if now < self.click_anim_end:
            self.click_anim = clamp((self.click_anim_end - now) / 0.12, 0, 1)
        else:
            self.click_anim = 0.0
        if now - self.last_click > 0.9:
            self.combo = 0

        # Scroll suave
        self._right_scroll += (self._scroll_target - self._right_scroll) * clamp(dt * 14, 0, 1)

    # ─────────────────────────────────────────────────────────────────────────
    # Acciones de juego
    # ─────────────────────────────────────────────────────────────────────────
    def _do_click(self, mx, my):
        now    = time.time()
        earned = self.game.click()
        if self._click_rect and self._click_rect.collidepoint(mx, my):
            cx, cy = mx, my
        elif self._click_rect:
            cx, cy = self._click_rect.center
        else:
            cx, cy = mx, my

        self.combo = self.combo + 1 if now - self.last_click <= 0.9 else 1
        self.last_click = now

        big = self.combo > 0 and self.combo % 25 == 0
        self.fx.float_text(cx, cy - 16, f"+{fmt(earned)}", GOLD, big=big)
        self.fx.sparks_burst(cx, cy, GOLD, 6 if not big else 18, 170)
        if big:
            self.fx.add_shake(0.18)
        self.ripples.append({"x": cx, "y": cy, "born": now})
        self.click_anim_end = now + 0.12

    def _buy_generator(self, idx):
        gen = GENERATORS[idx]
        if self.game.buy_generator(gen["id"]):
            n = self.game.generators[gen["id"]]
            self.toasts.add(f"✓ {gen['name']} comprado (×{n})", GREEN)
            r = self._gen_rects[idx]
            if r:
                self.fx.sparks_burst(r.centerx, r.centery, GREEN, 12, 190)
        elif not self.game.generator_unlocked(gen["id"]):
            self.toasts.add(f"{gen['name']}: bloqueado", RED)
        else:
            falta = self.game.generator_cost(gen["id"]) - self.game.points
            self.toasts.add(f"Faltan {fmt(falta)} pts", RED)

    def _buy_gen_upgrade(self, idx):
        gu = GEN_UPGRADES[idx]
        if self.game.buy_gen_upgrade(gu["id"]):
            tgt = next((g["name"] for g in GENERATORS if g["id"] == gu["target"]), "todos")
            self.toasts.add(f"✓ {gu['name']} — ×{gu['mult']} {tgt}", ORANGE)
            r = self._gu_rects[idx]
            if r:
                self.fx.sparks_burst(r.centerx, r.centery, ORANGE, 12, 190)
        elif self.game.gen_upgrades.get(gu["id"]):
            self.toasts.add("Ya activo.", MUTED)
        else:
            falta = self.game.gen_upgrade_cost(gu["id"]) - self.game.points
            self.toasts.add(f"Faltan {fmt(falta)} pts", RED)

    def _buy_upgrade(self, idx):
        upg = CLICK_UPGRADES[idx]
        if self.game.buy_click_upgrade(upg["id"]):
            bonus, mult = upg.get("bonus", 0), upg.get("mult", 1.0)
            parts = []
            if bonus:       parts.append(f"+{fmt(bonus*BOOST)}/clic")
            if mult != 1.0: parts.append(f"×{mult:.1f}")
            self.toasts.add(f"✓ {upg['name']}  {' '.join(parts)}", GREEN)
            r = self._upg_rects[idx]
            if r:
                self.fx.sparks_burst(r.centerx, r.centery, GREEN, 12, 190)
        elif self.game.click_upgrades[upg["id"]]:
            self.toasts.add("Ya tienes esa mejora.", MUTED)
        elif not self.game.click_upgrade_unlocked(upg["id"]):
            self.toasts.add(f"{upg['name']}: bloqueado", RED)
        else:
            falta = self.game.click_upgrade_cost(upg["id"]) - self.game.points
            self.toasts.add(f"Faltan {fmt(falta)} pts", RED)

    def _do_prestige(self):
        if self.game.can_prestige():
            n = self.game.prestige_count + 1
            self.game.prestige()
            self.toasts.add(f"★ Prestige {n}!  Mult total ×{self.game.prestige_multiplier:.1f}",
                            GOLD, 4.5)
            self.fx.confetti_burst(W, 110)
            self.fx.add_shake(0.45)
            self.combo = 0

    def _open_minigame(self):
        if not self.mini_available:
            return
        self.mini_available = False
        self.next_minigame  = time.time() + MINIGAME_COOLDOWN
        cls    = random.choice(MINIGAMES)
        mw, mh = cls.MODAL
        rect   = pygame.Rect((W - mw) // 2, (H - mh) // 2, mw, mh)
        self.mini          = cls(rect, self.fx)
        self._mini_applied = False

    def _handle_qte_key(self, key):
        if not self._qte or self._qte.done or self._qte.expired:
            return
        if key == self._qte.sequence[self._qte.current]:
            self._qte.current += 1
            if self._qte.done:
                self.game.activate_qte_bonus(3.0, 60.0)
                self._qte_total = 60.0
                self.toasts.add("¡QTE COMPLETADO!  Bonus ×3 por 60s", PURPLE, 5.0)
                self.fx.confetti_burst(W, 60)
                self._qte      = None
                self._next_qte = time.time() + QTE_COOLDOWN
        else:
            self._qte.failed     = True
            self._qte.fail_until = time.time() + 1.5
            self.fx.add_shake(0.25)
            self.toasts.add("QTE fallado.", RED, 2.0)

    # ─────────────────────────────────────────────────────────────────────────
    # Dibujo principal
    # ─────────────────────────────────────────────────────────────────────────
    def _draw(self):
        cv = self.canvas
        cv.blit(self.bg_grad, (0, 0))
        for n in self.nebulas:
            n.draw(cv)
        self.stars.draw(cv)

        mx, my = pygame.mouse.get_pos()
        self._draw_header(cv)
        self._draw_left(cv, mx, my)
        self._draw_right(cv, mx, my)
        pygame.draw.line(cv, BORDER, (SPLIT, HDR_H), (SPLIT, H - STS_H), 1)
        self._draw_status_bar(cv)

        if self.mini:
            overlay = pygame.Surface((W, H), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 165))
            cv.blit(overlay, (0, 0))
            self.mini.draw(cv, self.F, mx, my)

        if self._qte:
            self._draw_qte_panel(cv)

        self.fx.draw(cv, self.f_part, self.f_part2)

        if self.game.won and not self.victory_dismissed:
            self._draw_victory_overlay(cv)
        if self.paused:
            self._draw_pause_overlay(cv, mx, my)

        self.toasts.draw(cv, self.f_sm, PAD, H - STS_H - 6)

        self.screen.fill(BG)
        self.screen.blit(cv, self.fx.offset())
        pygame.display.flip()

    # ─────────────────────────────────────────────────────────────────────────
    # Header
    # ─────────────────────────────────────────────────────────────────────────
    def _draw_header(self, cv):
        now  = time.time()
        rect = pygame.Rect(0, 0, W, HDR_H)
        pygame.draw.rect(cv, PANEL, rect)
        sh = pygame.Surface((W, 1), pygame.SRCALPHA)
        sh.fill((255, 255, 255, 22))
        cv.blit(sh, (0, 0))
        pygame.draw.line(cv, BORDER, (0, HDR_H), (W, HDR_H), 1)

        tag_c = ORANGE if MODE == "demo" else ACCENT
        draw_text(cv, f"[{MODE.upper()}]", self.f_title, tag_c, PAD, HDR_H // 2, "midleft")

        pulse = 0.5 + 0.5 * math.sin(now * 1.4)
        title_c = lerp_color(TXT, (235, 242, 255), pulse * 0.5)
        draw_coin(cv, W // 2 - 118, HDR_H // 2, 13, now, speed=1.1)
        draw_text(cv, "CLICKER  GAME", self.f_title, title_c, W // 2, HDR_H // 2, "center")
        draw_text(cv, "pre-release", self.f_xs, GOLD, W // 2 + 110, HDR_H // 2 + 1, "midleft")

        draw_text(cv, f"t: {fmt_time(now - self.start_time)}", self.f_stat, MUTED,
                  W - PAD, HDR_H // 2, "midright")
        if self.game.infinite_mode:
            draw_text(cv, "★ MODO INFINITO ★", self.f_sm, GOLD,
                      W - PAD - 96, HDR_H // 2, "midright")

    # ─────────────────────────────────────────────────────────────────────────
    # Panel izquierdo
    # ─────────────────────────────────────────────────────────────────────────
    def _draw_left(self, cv, mx, my):
        x0, y0 = PAD, HDR_H + PAD
        pw = SPLIT - PAD * 2
        y = y0
        y = self._draw_stats_box(cv, x0, y, pw) + PAD
        y = self._draw_progress_section(cv, x0, y, pw) + PAD
        y = self._draw_click_button(cv, x0, y, pw, mx, my) + PAD
        y = self._draw_prestige_section(cv, x0, y, pw, mx, my) + PAD
        y = self._draw_minigame_section(cv, x0, y, pw, mx, my) + PAD
        self._draw_booster_bars(cv, x0, y, pw)

    def _draw_stats_box(self, cv, x, y, w) -> int:
        g = self.game
        now = time.time()
        eff_click = (g.click_value * g.click_mult * g.prestige_multiplier
                     * g.minigame_multiplier * g.qte_bonus_mult)
        rows = [
            ("Puntos",    fmt(self.roll_points.v),  GOLD),
            ("PPS",       fmt(self.roll_pps.v) + "/s", ACCENT),
            ("Por clic",  fmt(eff_click),           TXT),
            ("Acumulado", fmt(g.total_points),      MUTED),
            ("× bonus",   f"×{g.prestige_multiplier:.1f}  ×{g.click_mult:.1f}clic", ORANGE),
        ]
        row_h = 24
        box_h = len(rows) * row_h + PAD * 2
        draw_panel(cv, pygame.Rect(x, y, w, box_h))
        draw_coin(cv, x + PAD + 8, y + PAD + 10, 9, now)
        ry = y + PAD
        for i, (label, value, color) in enumerate(rows):
            lx = x + PAD + (24 if i == 0 else 0)
            draw_text(cv, label + ":", self.f_stat, MUTED, lx, ry)
            draw_text(cv, value, self.f_stat, color, x + w - PAD, ry, "topright")
            ry += row_h
        return y + box_h

    def _draw_progress_section(self, cv, x, y, w) -> int:
        g      = self.game
        now    = time.time()
        pct    = g.prestige_progress_pct() / 100.0
        labels = ["PRESTIGE 1", "PRESTIGE 2", "VICTORIA"]
        label  = labels[min(g.prestige_count, 2)]
        color  = ORANGE if g.prestige_count < 2 else GOLD
        draw_text(cv, f"→ {label}", self.f_sm, color, x, y)
        draw_text(cv, f"{pct*100:.1f}%", self.f_sm, MUTED, x + w, y, "topright")
        striped_bar(cv, pygame.Rect(x, y + 22, w, 14), pct, color, now=now, radius=6)
        return y + 40

    def _draw_click_button(self, cv, x, y, w, mx, my) -> int:
        now   = time.time()
        btn_h = 112
        rect  = pygame.Rect(x, y, w, btn_h)
        self._click_rect = rect
        hov    = rect.collidepoint(mx, my)
        shrink = int(self.click_anim * 4)
        draw_r = rect.inflate(-shrink * 2, -shrink * 2)

        base = (26, 56, 36) if not hov else (36, 76, 46)
        body = lerp_color(base, (16, 38, 24), self.click_anim)

        # Glow exterior (pulso suave; más al pasar el mouse)
        glow = 0.35 + 0.3 * math.sin(now * 2.4) + (0.5 if hov else 0.0)
        gs = pygame.Surface((draw_r.width + 28, draw_r.height + 28), pygame.SRCALPHA)
        for rad, a in ((10, 12), (6, 20), (3, 30)):
            pygame.draw.rect(gs, (*GREEN, int(clamp(glow, 0, 1) * a)),
                             pygame.Rect(14 - rad, 14 - rad,
                                         draw_r.width + rad * 2, draw_r.height + rad * 2),
                             3, border_radius=14 + rad)
        cv.blit(gs, (draw_r.x - 14, draw_r.y - 14))

        pygame.draw.rect(cv, body, draw_r, border_radius=14)
        sh = pygame.Surface((max(1, draw_r.width - 8), draw_r.height // 2 - 4), pygame.SRCALPHA)
        sh.fill((255, 255, 255, 18))
        cv.blit(sh, (draw_r.x + 4, draw_r.y + 3))
        pygame.draw.rect(cv, GREEN, draw_r, 2, border_radius=14)

        # Ondas de clic
        clip = cv.get_clip()
        cv.set_clip(draw_r)
        for rp in self.ripples:
            t = (now - rp["born"]) / 0.5
            if t >= 1:
                continue
            rr = int(8 + ease_out(t) * 110)
            col = lerp_color(GREEN, body, t)
            pygame.draw.circle(cv, col, (rp["x"], rp["y"]), rr, 2)
        cv.set_clip(clip)

        # Moneda + texto
        draw_coin(cv, draw_r.x + 52, draw_r.centery, 30, now, speed=2.0)
        bounce = math.sin(now * 3.2) * 2 + self.click_anim * 3
        draw_text(cv, "¡ C L I C !", self.f_click, GREEN,
                  draw_r.centerx + 26, draw_r.centery - 10 + bounce, "center")
        eff = (self.game.click_value * self.game.click_mult * self.game.prestige_multiplier
               * self.game.minigame_multiplier * self.game.qte_bonus_mult)
        draw_text(cv, f"+{fmt(eff)} por clic   [ESPACIO]", self.f_xs, MUTED,
                  draw_r.centerx + 26, draw_r.centery + 22, "center")

        # Combo
        if self.combo >= 5 and now - self.last_click <= 0.9:
            heat = clamp((self.combo - 5) / 40.0, 0, 1)
            cc   = lerp_color(GREEN, RED, heat)
            wob  = 1.0 + 0.08 * math.sin(now * 14)
            cs   = self.f_btn.render(f"COMBO ×{self.combo}", True, cc)
            cs   = pygame.transform.rotozoom(cs, math.sin(now * 9) * 3, wob)
            cv.blit(cs, cs.get_rect(center=(draw_r.right - 64, draw_r.y + 18)))
        return y + btn_h

    def _draw_prestige_section(self, cv, x, y, w, mx, my) -> int:
        g = self.game
        now = time.time()
        btn_h = 40
        if g.can_prestige():
            rect = pygame.Rect(x, y, w, btn_h)
            self._prestige_rect = rect
            hov  = rect.collidepoint(mx, my)
            glow = 0.5 + 0.5 * math.sin(now * 3.0)
            shiny_button(cv, rect, (84, 58, 10), GOLD, hover=hov,
                         glow=glow, shine=True, now=now, radius=9)
            draw_text(cv, f"★  PRESTIGE {g.prestige_count+1}  "
                          f"({'×1.5' if g.prestige_count == 0 else '×2.0'})",
                      self.f_btn, GOLD, rect.centerx, rect.centery, "center")
        else:
            self._prestige_rect = None
            n = g.prestige_count + 1
            if n <= 2:
                draw_text(cv, f"Faltan {fmt(g.prestige_threshold()-g.total_points)} pts "
                              f"→ Prestige {n}", self.f_sm, MUTED, x, y + 12)
            else:
                draw_text(cv, "2 reinicios completados", self.f_sm, MUTED, x, y + 12)
        return y + btn_h

    def _draw_minigame_section(self, cv, x, y, w, mx, my) -> int:
        g     = self.game
        now   = time.time()
        btn_h = 40

        if g.minigame_active:
            self._mini_rect = None
            left = g.minigame_seconds_left()
            bar  = pygame.Rect(x, y, w, btn_h)
            striped_bar(cv, bar, left / max(1.0, self._boost_total),
                        (88, 48, 130), bg=(30, 18, 48), now=now, radius=9)
            pygame.draw.rect(cv, PURPLE, bar, 2, border_radius=9)
            draw_text(cv, f"★ BOOST ×{g.minigame_multiplier:.1f}  {left:.0f}s",
                      self.f_btn, (235, 220, 255), bar.centerx, bar.centery, "center")
        elif self.mini_available:
            rect = pygame.Rect(x, y, w, btn_h)
            self._mini_rect = rect
            hov   = rect.collidepoint(mx, my)
            pulse = 0.5 + 0.5 * math.sin(now * 4.0)
            shiny_button(cv, rect, lerp_color((44, 30, 72), (60, 42, 98), pulse),
                         PURPLE, hover=hov, glow=pulse, shine=True, now=now, radius=9)
            draw_text(cv, "★  MINIJUEGO DISPONIBLE  ★", self.f_btn, (230, 214, 255),
                      rect.centerx, rect.centery, "center")
        else:
            self._mini_rect = None
            cd   = max(0.0, self.next_minigame - now)
            frac = 1.0 - cd / max(1.0, MINIGAME_COOLDOWN)
            draw_text(cv, f"Minijuego en {fmt_time(cd)}", self.f_sm, MUTED, x, y + 4)
            striped_bar(cv, pygame.Rect(x, y + 24, w, 9), frac, (70, 52, 110),
                        now=now, radius=4)
        return y + btn_h

    def _draw_booster_bars(self, cv, x, y, w):
        g = self.game
        if not g.qte_bonus_active:
            return
        now  = time.time()
        left = g.qte_bonus_seconds_left()
        bar  = pygame.Rect(x, y, w, 30)
        striped_bar(cv, bar, left / max(1.0, self._qte_total),
                    (70, 40, 120), bg=(24, 16, 44), now=now, radius=7)
        pygame.draw.rect(cv, PURPLE, bar, 2, border_radius=7)
        draw_text(cv, f"QTE ×3  {left:.0f}s", self.f_xs, (230, 214, 255),
                  bar.centerx, bar.centery, "center")

    # ─────────────────────────────────────────────────────────────────────────
    # Panel derecho (scrollable)
    # ─────────────────────────────────────────────────────────────────────────
    def _sy(self, vy):
        return HDR_H + PAD + vy - int(self._right_scroll)

    def _row_visible(self, vy, rh):
        sy = self._sy(vy)
        return sy + rh > HDR_H and sy < H - STS_H

    def _draw_right(self, cv, mx, my):
        x0 = SPLIT + PAD
        pw = W - SPLIT - PAD * 2

        clip = pygame.Rect(SPLIT + 1, HDR_H + 1, W - SPLIT - 2, H - HDR_H - STS_H - 2)
        cv.set_clip(clip)

        vy = 0
        vy = self._draw_generators_right(cv, x0, vy, pw, mx, my)
        vy += PAD
        sep = self._sy(vy)
        if HDR_H < sep < H - STS_H:
            pygame.draw.line(cv, BORDER, (x0, sep), (x0 + pw, sep), 1)
        vy += PAD + 1
        vy = self._draw_gen_upgrades_right(cv, x0, vy, pw, mx, my)
        vy += PAD
        sep = self._sy(vy)
        if HDR_H < sep < H - STS_H:
            pygame.draw.line(cv, BORDER, (x0, sep), (x0 + pw, sep), 1)
        vy += PAD + 1
        vy = self._draw_click_upgrades_right(cv, x0, vy, pw, mx, my)
        vy += PAD * 2

        cv.set_clip(None)

        visible_h = H - HDR_H - STS_H - PAD * 2
        self._right_max_scroll = max(0, vy - visible_h)
        self._scroll_target    = clamp(self._scroll_target, 0, self._right_max_scroll)

        if self._right_max_scroll > 0:
            panel_h = H - HDR_H - STS_H
            bar_h   = max(18, panel_h * panel_h // max(1, vy))
            bar_y   = HDR_H + int(self._right_scroll / self._right_max_scroll
                                  * (panel_h - bar_h))
            pygame.draw.rect(cv, MUTED, (W - 6, bar_y, 3, bar_h), border_radius=1)

    def _cost_button(self, cv, btn_r, cost, can, mx, my, accent=GREEN):
        """Botón de compra estándar con shine si es comprable."""
        now = time.time()
        hov = btn_r.collidepoint(mx, my)
        base = (24, 64, 34) if can else (32, 24, 26)
        shiny_button(cv, btn_r, base, accent if can else RED,
                     hover=hov and can, shine=can, now=now, radius=7)
        draw_text(cv, fmt(cost), self.f_btn, accent if can else RED,
                  btn_r.centerx, btn_r.centery, "center")

    def _draw_generators_right(self, cv, x, vy, pw, mx, my) -> int:
        if self._row_visible(vy, 24):
            draw_text(cv, "GENERADORES", self.f_med, TXT, x, self._sy(vy))
        vy += 26
        row_h = 70; btn_w = 130; btn_h = 32

        for i, gen in enumerate(GENERATORS):
            if not self._row_visible(vy, row_h):
                self._gen_rects[i] = None
                vy += row_h
                continue
            sy     = self._sy(vy)
            rect   = pygame.Rect(x, sy, pw, row_h - 4)
            locked = not self.game.generator_unlocked(gen["id"])
            if locked:
                draw_panel(cv, rect, color=(15, 19, 28))
                # Candado dibujado (la fuente del sistema no trae emoji)
                lx, ly = x + PAD + 7, sy + 16
                pygame.draw.arc(cv, MUTED, (lx - 5, ly - 2, 10, 12), 0, math.pi, 2)
                pygame.draw.rect(cv, MUTED, (lx - 7, ly + 4, 14, 11), border_radius=3)
                draw_text(cv, "???", self.f_med, MUTED, lx + 14, sy + 12)
                draw_text(cv, f"Desbloquea a {fmt(gen['unlock'] * BOOST)} pts acumulados",
                          self.f_xs, (70, 78, 92), x + PAD, sy + 38)
                self._gen_rects[i] = None
            else:
                owned   = self.game.generators[gen["id"]]
                cost    = self.game.generator_cost(gen["id"])
                can_buy = self.game.can_buy_generator(gen["id"])
                pps_r   = (gen["pps"] * self.game.prestige_multiplier * BOOST
                           * self.game.gen_mult.get(gen["id"], 1.0)
                           * self.game.gen_mult.get("all", 1.0))
                draw_panel(cv, rect, color=(24, 32, 44) if can_buy else PANEL,
                           border=scale_color(GREEN, 0.55) if can_buy else BORDER)
                draw_text(cv, gen["name"], self.f_med, TXT, x + PAD, sy + 10)
                draw_text(cv, f"×{owned}", self.f_med,
                          ACCENT if owned > 0 else MUTED, x + PAD + 132, sy + 10)
                pps_str = f"+{fmt(pps_r * owned)}/s" if owned > 0 else f"{fmt(pps_r)}/s c/u"
                draw_text(cv, pps_str, self.f_xs, MUTED, x + PAD, sy + 36)

                # Mini-barra de ahorro hacia el coste
                if not can_buy:
                    frac = clamp(self.game.points / max(1, cost), 0, 1)
                    mini = pygame.Rect(x + PAD, sy + row_h - 14, pw - btn_w - PAD * 3, 4)
                    pygame.draw.rect(cv, PANEL2, mini, border_radius=2)
                    if frac > 0:
                        f = mini.copy(); f.width = max(2, int(mini.width * frac))
                        pygame.draw.rect(cv, GOLD_D, f, border_radius=2)

                btn_r = pygame.Rect(x + pw - btn_w - PAD,
                                    sy + (row_h - 4 - btn_h) // 2, btn_w, btn_h)
                self._gen_rects[i] = btn_r
                self._cost_button(cv, btn_r, cost, can_buy, mx, my)
            vy += row_h
        return vy

    def _draw_gen_upgrades_right(self, cv, x, vy, pw, mx, my) -> int:
        if self._row_visible(vy, 24):
            draw_text(cv, "POTENCIADORES", self.f_med, TXT, x, self._sy(vy))
        vy += 26
        row_h = 48; btn_w = 110; btn_h = 30; icon_s = 28

        visible = [i for i, gu in enumerate(GEN_UPGRADES)
                   if self.game.gen_upgrades.get(gu["id"])
                   or self.game.gen_upgrade_unlocked(gu["id"])]
        for i in range(len(GEN_UPGRADES)):
            self._gu_rects[i] = None
        if not visible:
            if self._row_visible(vy, 22):
                draw_text(cv, "Compra generadores para desbloquear", self.f_xs,
                          MUTED, x + PAD, self._sy(vy))
            return vy + 22

        for idx in visible:
            gu     = GEN_UPGRADES[idx]
            bought = self.game.gen_upgrades.get(gu["id"], False)
            if not self._row_visible(vy, row_h):
                vy += row_h
                continue
            sy   = self._sy(vy)
            rect = pygame.Rect(x, sy, pw, row_h - 3)
            cost = self.game.gen_upgrade_cost(gu["id"])
            can  = self.game.can_buy_gen_upgrade(gu["id"])

            bg_c = (15, 19, 28) if bought else ((24, 32, 44) if can else PANEL)
            draw_panel(cv, rect, color=bg_c,
                       border=scale_color(ORANGE, 0.55) if can else BORDER)

            icon_c = (62, 46, 14) if bought else \
                     ((52, 38, 10) if gu["target"] == "all" else (28, 46, 72))
            ix, iy = x + PAD, sy + (row_h - 3 - icon_s) // 2
            pygame.draw.rect(cv, icon_c, (ix, iy, icon_s, icon_s), border_radius=6)
            draw_text(cv, gu["icon"], self.f_sm, (225, 225, 230),
                      ix + icon_s // 2, iy + icon_s // 2, "center")

            tx = ix + icon_s + 8
            draw_text(cv, gu["name"], self.f_btn, MUTED if bought else TXT, tx, sy + 8)
            tgt = next((g["name"] for g in GENERATORS if g["id"] == gu["target"]), "Todos")
            draw_text(cv, f"×{gu['mult']:.1f}  {tgt}", self.f_xs, MUTED, tx, sy + 28)

            if bought:
                draw_text(cv, "✓", self.f_btn, GREEN, x + pw - PAD - 20,
                          sy + (row_h - 3) // 2, "midleft")
            else:
                btn_r = pygame.Rect(x + pw - btn_w - PAD,
                                    sy + (row_h - 3 - btn_h) // 2, btn_w, btn_h)
                self._gu_rects[idx] = btn_r
                self._cost_button(cv, btn_r, cost, can, mx, my, accent=ORANGE)
            vy += row_h
        return vy

    def _draw_click_upgrades_right(self, cv, x, vy, pw, mx, my) -> int:
        if self._row_visible(vy, 24):
            draw_text(cv, "MEJORAS DE CLIC", self.f_med, TXT, x, self._sy(vy))
        vy += 26
        row_h = 48; btn_w = 110; btn_h = 30; icon_s = 28

        for i in range(len(CLICK_UPGRADES)):
            self._upg_rects[i] = None

        for i, upg in enumerate(CLICK_UPGRADES):
            if not self.game.click_upgrade_unlocked(upg["id"]):
                continue
            bought = self.game.click_upgrades[upg["id"]]
            if not self._row_visible(vy, row_h):
                vy += row_h
                continue
            sy   = self._sy(vy)
            rect = pygame.Rect(x, sy, pw, row_h - 3)
            cost = self.game.click_upgrade_cost(upg["id"])
            can  = not bought and self.game.points >= cost

            bg_c = (15, 19, 28) if bought else ((24, 32, 44) if can else PANEL)
            draw_panel(cv, rect, color=bg_c,
                       border=scale_color(GREEN, 0.55) if can else BORDER)

            has_mult = upg.get("mult", 1.0) != 1.0
            icon_c   = (62, 46, 14) if has_mult else (28, 46, 72)
            ix, iy   = x + PAD, sy + (row_h - 3 - icon_s) // 2
            pygame.draw.rect(cv, icon_c, (ix, iy, icon_s, icon_s), border_radius=6)
            draw_text(cv, upg["icon"], self.f_sm, (225, 225, 230),
                      ix + icon_s // 2, iy + icon_s // 2, "center")

            tx = ix + icon_s + 8
            draw_text(cv, upg["name"], self.f_btn, MUTED if bought else TXT, tx, sy + 8)
            bonus, mult = upg.get("bonus", 0), upg.get("mult", 1.0)
            parts = []
            if bonus:       parts.append(f"+{fmt(bonus*BOOST)}")
            if mult != 1.0: parts.append(f"×{mult:.1f} clic")
            draw_text(cv, "  ".join(parts) or "—", self.f_xs, MUTED, tx, sy + 28)

            if bought:
                draw_text(cv, "✓", self.f_btn, GREEN, x + pw - PAD - 20,
                          sy + (row_h - 3) // 2, "midleft")
            else:
                btn_r = pygame.Rect(x + pw - btn_w - PAD,
                                    sy + (row_h - 3 - btn_h) // 2, btn_w, btn_h)
                self._upg_rects[i] = btn_r
                self._cost_button(cv, btn_r, cost, can, mx, my)
            vy += row_h
        return vy

    # ─────────────────────────────────────────────────────────────────────────
    # Status bar
    # ─────────────────────────────────────────────────────────────────────────
    def _draw_status_bar(self, cv):
        rect = pygame.Rect(0, H - STS_H, W, STS_H)
        pygame.draw.rect(cv, PANEL, rect)
        pygame.draw.line(cv, BORDER, (0, H - STS_H), (W, H - STS_H), 1)
        draw_text(cv, "ESPACIO: clic  |  P: prestige  |  ESC: pausa  |  scroll: más mejoras",
                  self.f_sm, MUTED, PAD, H - STS_H + 8)
        draw_text(cv, f"récord: {fmt(self.game.high_score)}", self.f_xs, MUTED,
                  W - PAD, H - STS_H + 9, "topright")

    # ─────────────────────────────────────────────────────────────────────────
    # QTE Panel
    # ─────────────────────────────────────────────────────────────────────────
    def _draw_qte_panel(self, cv):
        qte = self._qte
        if not qte:
            return
        qw, qh = 540, 84
        qx, qy = (W - qw) // 2, HDR_H + 8
        now    = time.time()
        pulse  = 0.5 + 0.5 * math.sin(now * 5.0)

        surf = pygame.Surface((qw, qh), pygame.SRCALPHA)
        pygame.draw.rect(surf, (22, 14, 38, 225), surf.get_rect(), border_radius=10)
        cv.blit(surf, (qx, qy))
        pygame.draw.rect(cv, lerp_color(RED, ORANGE, pulse), (qx, qy, qw, qh),
                         2, border_radius=10)

        if qte.failed:
            draw_text(cv, "✗ QTE FALLADO", self.f_btn, RED,
                      qx + qw // 2, qy + qh // 2, "center")
            return

        draw_text(cv, "¡ QTE !  ×3 por 60s", self.f_xs, ORANGE, qx + 12, qy + 7)

        key_w = 32
        seq, cur = qte.sequence, qte.current
        total_w  = len(seq) * key_w + (len(seq) - 1) * 6
        kx, ky   = qx + (qw - total_w) // 2, qy + 24
        for j, k in enumerate(seq):
            krect = pygame.Rect(kx + j * (key_w + 6), ky, key_w, 28)
            if j < cur:
                c_bg, c_txt, c_brd = (22, 80, 35), GREEN, GREEN
            elif j == cur:
                c_bg = lerp_color((60, 40, 80), (90, 62, 120), pulse)
                c_txt, c_brd = (255, 230, 100), ORANGE
                gs = pygame.Surface((key_w + 12, 40), pygame.SRCALPHA)
                pygame.draw.rect(gs, (*ORANGE, int(50 * pulse)), gs.get_rect(),
                                 2, border_radius=8)
                cv.blit(gs, (krect.x - 6, krect.y - 6))
            else:
                c_bg, c_txt, c_brd = (30, 25, 45), MUTED, BORDER
            pygame.draw.rect(cv, c_bg, krect, border_radius=6)
            pygame.draw.rect(cv, c_brd, krect, 1, border_radius=6)
            draw_text(cv, k, self.f_xs, c_txt, krect.centerx, krect.centery, "center")

        frac = qte.time_left / qte.duration
        striped_bar(cv, pygame.Rect(qx + 12, qy + qh - 16, qw - 24, 8),
                    frac, lerp_color(RED, GREEN, frac), now=now, radius=3)

    # ─────────────────────────────────────────────────────────────────────────
    # Overlay de victoria
    # ─────────────────────────────────────────────────────────────────────────
    def _draw_victory_overlay(self, cv):
        overlay = pygame.Surface((W, H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 210))
        cv.blit(overlay, (0, 0))
        now = time.time()

        vw, vh = 520, 330
        vx, vy = (W - vw) // 2, (H - vh) // 2
        vr = pygame.Rect(vx, vy, vw, vh)
        pygame.draw.rect(cv, (18, 28, 18), vr, border_radius=14)
        pulse = 0.5 + 0.5 * math.sin(now * 2.0)
        pygame.draw.rect(cv, lerp_color(GOLD, (255, 226, 110), pulse), vr, 2,
                         border_radius=14)

        draw_coin(cv, vx + 60, vy + 38, 18, now)
        draw_coin(cv, vx + vw - 60, vy + 38, 18, now + 0.9)
        draw_text(cv, "¡  V I C T O R I A  !", self.f_big,
                  lerp_color(GOLD, (255, 220, 80), pulse * 0.5),
                  vx + vw // 2, vy + 36, "center")
        pygame.draw.line(cv, GOLD, (vx + 40, vy + 74), (vx + vw - 40, vy + 74), 1)

        lines = [
            ("Tiempo",     fmt_time(now - self.start_time),    TXT),
            ("Puntuación", fmt(self.game.high_score),          GOLD),
            ("Reinicios",  f"{self.game.prestige_count} / 2",  ORANGE),
            ("Mult click", f"×{self.game.click_mult:.1f}",     ACCENT),
        ]
        for j, (label, val, c) in enumerate(lines):
            ry = vy + 94 + j * 38
            draw_text(cv, label + ":", self.f_med, MUTED, vx + 60, ry)
            draw_text(cv, val, self.f_med, c, vx + vw - 60, ry, "topright")

        draw_text(cv, "★  MODO INFINITO DESBLOQUEADO  ★", self.f_btn, GREEN,
                  vx + vw // 2, vy + 258, "center")
        draw_text(cv, "Haz clic para continuar", self.f_sm, MUTED,
                  vx + vw // 2, vy + 294, "center",
                  alpha=int(128 + 127 * math.sin(now * 3.0)))

    # ─────────────────────────────────────────────────────────────────────────
    # Overlay de pausa
    # ─────────────────────────────────────────────────────────────────────────
    def _draw_pause_overlay(self, cv, mx, my):
        overlay = pygame.Surface((W, H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 175))
        cv.blit(overlay, (0, 0))
        now = time.time()

        pw, ph = 380, 290
        px, py = (W - pw) // 2, (H - ph) // 2
        panel  = pygame.Rect(px, py, pw, ph)
        pygame.draw.rect(cv, (20, 24, 34), panel, border_radius=12)
        pygame.draw.rect(cv, BORDER, panel, 2, border_radius=12)

        cx = px + pw // 2
        draw_text(cv, "PAUSA", self.f_big, TXT, cx, py + 26, "center")
        pygame.draw.line(cv, BORDER, (px + 30, py + 62), (px + pw - 30, py + 62), 1)

        vol = self.music.get_volume() if self.music else 0.0
        bx  = cx - 80
        draw_text(cv, "Vol:", self.f_sm, MUTED, bx - 36, py + 80)
        striped_bar(cv, pygame.Rect(bx, py + 80, 160, 13), vol, ACCENT, now=now, radius=5)
        draw_text(cv, f"{int(vol*100)}%", self.f_sm, MUTED, bx + 170, py + 80)
        draw_text(cv, "← → para ajustar", self.f_xs, MUTED, cx, py + 102, "center")

        y0 = py + 132
        rects = {}
        for label, key in [("CONTINUAR", "resume"), ("MENÚ PRINCIPAL", "menu"),
                           ("SALIR DEL JUEGO", "quit")]:
            r   = pygame.Rect(cx - 125, y0, 250, 42)
            hov = r.collidepoint(mx, my)
            shiny_button(cv, r, (27, 34, 46), ACCENT if hov else BORDER,
                         hover=hov, now=now, radius=9)
            draw_text(cv, label, self.f_btn, (232, 241, 255) if hov else TXT,
                      r.centerx, r.centery, "center")
            rects[key] = r
            y0 += 52

        self._pause_resume_rect = rects.get("resume")
        self._pause_menu_rect   = rects.get("menu")
        self._pause_quit_rect   = rects.get("quit")


# ═══════════════════════════════════════════════════════════════════════════════
# Punto de entrada standalone
# ═══════════════════════════════════════════════════════════════════════════════
def main():
    pygame.init()
    ui = GameUI()
    ui.run()
