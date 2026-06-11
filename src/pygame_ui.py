"""Interfaz pygame del Clicker Game."""

import pygame
import sys
import time
import random
import math

from src.game import GameState
from src.config import GENERATORS, CLICK_UPGRADES, MODE, MINIGAME_COOLDOWN, BOOST

# ═══════════════════════════════════════════════════════════════════════════════
# Constantes de pantalla
# ═══════════════════════════════════════════════════════════════════════════════
W, H    = 960, 640
FPS     = 60
SPLIT   = 375      # divisor panel izquierdo / derecho
HDR_H   = 46       # alto de la cabecera
STS_H   = 30       # alto de la barra de estado
PAD     = 14

# ═══════════════════════════════════════════════════════════════════════════════
# Paleta de colores  (GitHub dark)
# ═══════════════════════════════════════════════════════════════════════════════
BG      = ( 13,  17,  23)
PANEL   = ( 22,  27,  34)
PANEL2  = ( 30,  35,  45)
BORDER  = ( 48,  54,  61)
TXT     = (201, 209, 217)
MUTED   = (110, 118, 129)
ACCENT  = ( 88, 166, 255)
GOLD    = (210, 153,  34)
GREEN   = ( 63, 185,  80)
GREEN_D = ( 22,  80,  35)
RED     = (248,  81,  73)
RED_D   = ( 80,  25,  22)
ORANGE  = (255, 166,  87)
PURPLE  = (188, 140, 255)
BTN_N   = ( 33,  38,  45)
BTN_H   = ( 55,  65,  80)
BTN_D   = ( 18,  22,  27)


# ═══════════════════════════════════════════════════════════════════════════════
# Utilidades
# ═══════════════════════════════════════════════════════════════════════════════
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
    if h:
        return f"{h}h {m:02d}m"
    return f"{m:02d}:{sec:02d}"


def lerp_color(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def draw_panel(surf, rect, color=PANEL, border=BORDER, radius=8):
    pygame.draw.rect(surf, color, rect, border_radius=radius)
    pygame.draw.rect(surf, border, rect, 1, border_radius=radius)


def draw_text(surf, text, font, color, x, y, anchor="topleft"):
    s = font.render(text, True, color)
    r = s.get_rect(**{anchor: (x, y)})
    surf.blit(s, r)
    return r


def draw_progress_bar(surf, rect, pct, fg=ACCENT, bg=PANEL2, radius=4):
    pygame.draw.rect(surf, bg, rect, border_radius=radius)
    if pct > 0:
        fill = rect.copy()
        fill.width = max(radius * 2, int(rect.width * min(pct, 1.0)))
        pygame.draw.rect(surf, fg, fill, border_radius=radius)
    pygame.draw.rect(surf, BORDER, rect, 1, border_radius=radius)


# ═══════════════════════════════════════════════════════════════════════════════
# Partícula flotante  (+X puntos al hacer clic)
# ═══════════════════════════════════════════════════════════════════════════════
class Particle:
    DURATION = 0.9

    def __init__(self, x: float, y: float, text: str, color=GREEN):
        self.x    = float(x)
        self.y    = float(y)
        self.text = text
        self.color = color
        self.born = time.time()
        self.vx   = random.uniform(-0.6, 0.6)
        self.vy   = random.uniform(-2.2, -1.4)

    @property
    def alive(self) -> bool:
        return (time.time() - self.born) < self.DURATION

    @property
    def alpha(self) -> int:
        t = (time.time() - self.born) / self.DURATION
        return int(max(0, 255 * (1 - t ** 1.4)))

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.06   # gravedad suave


# ═══════════════════════════════════════════════════════════════════════════════
# GameUI
# ═══════════════════════════════════════════════════════════════════════════════
class GameUI:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((W, H))
        pygame.display.set_caption(f"Clicker Game  [{MODE.upper()}]")
        self.clock = pygame.time.Clock()

        # ── Fuentes ──────────────────────────────────────────────────────────
        mono = "monospace"
        self.f_title  = pygame.font.SysFont(mono, 22, bold=True)
        self.f_big    = pygame.font.SysFont(mono, 32, bold=True)
        self.f_med    = pygame.font.SysFont(mono, 17)
        self.f_sm     = pygame.font.SysFont(mono, 14)
        self.f_btn    = pygame.font.SysFont(mono, 15, bold=True)
        self.f_click  = pygame.font.SysFont(mono, 26, bold=True)
        self.f_stat   = pygame.font.SysFont(mono, 16)
        self.f_part   = pygame.font.SysFont(mono, 15, bold=True)

        # ── Estado del juego ─────────────────────────────────────────────────
        self.game       = GameState()
        self.start_time = time.time()
        self.particles: list[Particle] = []

        # ── Feedback de UI ───────────────────────────────────────────────────
        self.status_msg = ""
        self.status_end = 0.0

        # ── Animación del botón clic ──────────────────────────────────────────
        self.click_anim     = 0.0   # 0 = normal, 1 = pulsado
        self.click_anim_end = 0.0

        # ── Minijuego ────────────────────────────────────────────────────────
        self.next_minigame    = time.time() + MINIGAME_COOLDOWN
        self.mini_available   = False
        self.mini_open        = False
        self.mini_answer      = 0
        self.mini_selected    = -1       # qué botón pulsó el usuario
        self.mini_result_end  = 0.0      # cuándo cerrar el modal

        # ── Rects interactivos (se recalculan cada frame en _draw) ────────────
        self._click_rect:    pygame.Rect | None = None
        self._prestige_rect: pygame.Rect | None = None
        self._mini_rect:     pygame.Rect | None = None
        self._gen_rects:     list[pygame.Rect | None] = [None] * len(GENERATORS)
        self._upg_rects:     list[pygame.Rect | None] = [None] * len(CLICK_UPGRADES)
        self._mini_num_rects: list[pygame.Rect] = []

    # ─────────────────────────────────────────────────────────────────────────
    # Loop principal
    # ─────────────────────────────────────────────────────────────────────────
    def run(self):
        while True:
            events = pygame.event.get()
            self._handle_events(events)
            self._update()
            self._draw()
            self.clock.tick(FPS)

    # ─────────────────────────────────────────────────────────────────────────
    # Eventos
    # ─────────────────────────────────────────────────────────────────────────
    def _handle_events(self, events):
        mx, my = pygame.mouse.get_pos()
        for event in events:
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            # ── Modal minijuego activo ────────────────────────────────────────
            if self.mini_open:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.mini_open = False
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    # Solo permitir selección si no hay resultado todavía
                    if self.mini_selected == -1:
                        for i, rect in enumerate(self._mini_num_rects):
                            if rect.collidepoint(mx, my):
                                self._resolve_minigame(i + 1)
                continue   # no procesar otros botones mientras el modal está abierto

            # ── Teclado ───────────────────────────────────────────────────────
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    self._do_click(mx, my)
                elif event.key == pygame.K_p:
                    self._do_prestige()

            # ── Ratón ─────────────────────────────────────────────────────────
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self._click_rect and self._click_rect.collidepoint(mx, my):
                    self._do_click(mx, my)
                if self._prestige_rect and self._prestige_rect.collidepoint(mx, my):
                    self._do_prestige()
                if self._mini_rect and self._mini_rect.collidepoint(mx, my):
                    self._open_minigame()
                for i, rect in enumerate(self._gen_rects):
                    if rect and rect.collidepoint(mx, my):
                        self._buy_generator(i)
                for i, rect in enumerate(self._upg_rects):
                    if rect and rect.collidepoint(mx, my):
                        self._buy_upgrade(i)

    # ─────────────────────────────────────────────────────────────────────────
    # Lógica de frame
    # ─────────────────────────────────────────────────────────────────────────
    def _update(self):
        self.game.tick()
        self.game.check_victory()

        now = time.time()
        if not self.mini_available and now >= self.next_minigame:
            self.mini_available = True

        # Cerrar modal de minijuego tras mostrar resultado
        if self.mini_open and self.mini_selected != -1 and now >= self.mini_result_end:
            self.mini_open = False

        # Actualizar partículas
        for p in self.particles:
            p.update()
        self.particles = [p for p in self.particles if p.alive]

        # Animación botón clic (spring back)
        if now < self.click_anim_end:
            t = (self.click_anim_end - now) / 0.12
            self.click_anim = min(1.0, t)
        else:
            self.click_anim = 0.0

    # ─────────────────────────────────────────────────────────────────────────
    # Acciones
    # ─────────────────────────────────────────────────────────────────────────
    def _do_click(self, mx, my):
        earned = self.game.click()
        cx = mx if self._click_rect and self._click_rect.collidepoint(mx, my) else (
            self._click_rect.centerx if self._click_rect else mx)
        cy = my if self._click_rect and self._click_rect.collidepoint(mx, my) else (
            self._click_rect.centery if self._click_rect else my)
        self.particles.append(Particle(cx, cy - 10, f"+{fmt(earned)}", GOLD))
        self.click_anim_end = time.time() + 0.12

    def _buy_generator(self, idx: int):
        gen = GENERATORS[idx]
        if self.game.buy_generator(gen["id"]):
            n = self.game.generators[gen["id"]]
            self._set_status(f"✓ {gen['name']} comprado (×{n})", GREEN)
        elif not self.game.generator_unlocked(gen["id"]):
            self._set_status(f"{gen['name']}: aún bloqueado", RED)
        else:
            cost = self.game.generator_cost(gen["id"])
            self._set_status(f"Faltan {fmt(cost - self.game.points)} pts", RED)

    def _buy_upgrade(self, idx: int):
        upg = CLICK_UPGRADES[idx]
        if self.game.buy_click_upgrade(upg["id"]):
            self._set_status(f"✓ {upg['name']} desbloqueado (+{upg['bonus']*100}/clic)", GREEN)
        elif self.game.click_upgrades[upg["id"]]:
            self._set_status("Ya tienes esa mejora.", MUTED)
        elif not self.game.click_upgrade_unlocked(upg["id"]):
            self._set_status(f"{upg['name']}: aún bloqueado", RED)
        else:
            cost = self.game.click_upgrade_cost(upg["id"])
            self._set_status(f"Faltan {fmt(cost - self.game.points)} pts", RED)

    def _do_prestige(self):
        if self.game.can_prestige():
            n = self.game.prestige_count + 1
            self.game.prestige()
            mult = self.game.prestige_multiplier
            self._set_status(f"★ Prestige {n} completado!  Multiplicador total: ×{mult:.1f}", GOLD, duration=4.0)
            self.particles.clear()

    def _open_minigame(self):
        if not self.mini_available:
            return
        self.mini_answer   = random.randint(1, 9)
        self.mini_selected = -1
        self.mini_open     = True
        self.mini_available = False
        self.next_minigame  = time.time() + MINIGAME_COOLDOWN

    def _resolve_minigame(self, guess: int):
        self.mini_selected   = guess
        self.mini_result_end = time.time() + 1.8
        if guess == self.mini_answer:
            self.game.activate_minigame(multiplier=2.0, duration=30.0)
            self._set_status("¡CORRECTO! Boost ×2 activo durante 30s", PURPLE, duration=4.0)
        else:
            self._set_status(f"Fallaste (era {self.mini_answer}). Sin recompensa.", RED, duration=3.0)

    def _set_status(self, msg: str, color=TXT, duration: float = 2.5):
        self.status_msg   = msg
        self.status_color = color
        self.status_end   = time.time() + duration

    # ─────────────────────────────────────────────────────────────────────────
    # Dibujo principal
    # ─────────────────────────────────────────────────────────────────────────
    def _draw(self):
        self.screen.fill(BG)
        mx, my = pygame.mouse.get_pos()

        self._draw_header()
        self._draw_left(mx, my)
        self._draw_right(mx, my)
        self._draw_divider()
        self._draw_status_bar()
        self._draw_particles()

        if self.mini_open:
            self._draw_minigame_modal(mx, my)

        if self.game.won:
            self._draw_victory_overlay()

        pygame.display.flip()

    # ─────────────────────────────────────────────────────────────────────────
    # Cabecera
    # ─────────────────────────────────────────────────────────────────────────
    def _draw_header(self):
        rect = pygame.Rect(0, 0, W, HDR_H)
        pygame.draw.rect(self.screen, PANEL, rect)
        pygame.draw.line(self.screen, BORDER, (0, HDR_H), (W, HDR_H), 1)

        tag_color = ORANGE if MODE == "demo" else ACCENT
        draw_text(self.screen, f"[{MODE.upper()}]", self.f_title, tag_color, PAD, HDR_H // 2, "midleft")
        draw_text(self.screen, "CLICKER  GAME", self.f_title, TXT, W // 2, HDR_H // 2, "center")

        elapsed = fmt_time(time.time() - self.start_time)
        draw_text(self.screen, f"⏱  {elapsed}", self.f_stat, MUTED, W - PAD, HDR_H // 2, "midright")

        if self.game.infinite_mode:
            draw_text(self.screen, "★ MODO INFINITO ★", self.f_sm, GOLD,
                      W // 2 + 120, HDR_H // 2, "midleft")

    # ─────────────────────────────────────────────────────────────────────────
    # Panel izquierdo
    # ─────────────────────────────────────────────────────────────────────────
    def _draw_left(self, mx, my):
        x0  = PAD
        y0  = HDR_H + PAD
        pw  = SPLIT - PAD * 2

        y = y0
        y = self._draw_stats_box(x0, y, pw)
        y += PAD
        y = self._draw_progress_section(x0, y, pw)
        y += PAD
        y = self._draw_click_button(x0, y, pw, mx, my)
        y += PAD
        y = self._draw_prestige_section(x0, y, pw, mx, my)
        y += PAD
        self._draw_minigame_section(x0, y, pw, mx, my)

    def _draw_stats_box(self, x, y, w) -> int:
        g = self.game
        rows = [
            ("Puntos",    fmt(g.points),          GOLD),
            ("PPS",       fmt(g.pps()) + "/s",    ACCENT),
            ("Por clic",  fmt(g.click_value * g.prestige_multiplier * g.minigame_multiplier), TXT),
            ("Acumulado", fmt(g.total_points),     MUTED),
            ("×bonus",    f"×{g.prestige_multiplier:.1f}  ({g.prestige_count}/2 reinicios)", ORANGE),
        ]
        row_h   = 22
        box_h   = len(rows) * row_h + PAD * 2
        rect    = pygame.Rect(x, y, w, box_h)
        draw_panel(self.screen, rect)

        ry = y + PAD
        for label, value, color in rows:
            draw_text(self.screen, label + ":", self.f_stat, MUTED, x + PAD, ry)
            draw_text(self.screen, value,        self.f_stat, color, x + w - PAD, ry, "topright")
            ry += row_h
        return y + box_h

    def _draw_progress_section(self, x, y, w) -> int:
        g = self.game
        pct    = g.prestige_progress_pct() / 100.0
        labels = ["PRESTIGE 1", "PRESTIGE 2", "VICTORIA"]
        label  = labels[min(g.prestige_count, 2)]
        color  = ORANGE if g.prestige_count < 2 else GOLD

        draw_text(self.screen, f"→ {label}", self.f_sm, color, x, y)
        bar_rect = pygame.Rect(x, y + 22, w, 12)
        draw_progress_bar(self.screen, bar_rect, pct, fg=color)
        pct_str = f"{pct*100:.1f}%"
        draw_text(self.screen, pct_str, self.f_sm, MUTED, x + w, y + 22, "topright")
        return y + 38

    def _draw_click_button(self, x, y, w, mx, my) -> int:
        btn_h  = 84
        rect   = pygame.Rect(x, y, w, btn_h)
        self._click_rect = rect

        hov    = rect.collidepoint(mx, my)
        anim_t = self.click_anim
        shrink = int(anim_t * 4)
        draw_rect = rect.inflate(-shrink * 2, -shrink * 2)

        # Color base del botón: verde oscuro siempre, más claro en hover
        base_c = (30, 65, 40)
        hov_c  = (45, 90, 55)
        c      = hov_c if hov else base_c
        if anim_t > 0:
            c = lerp_color(c, (20, 45, 28), anim_t)

        pygame.draw.rect(self.screen, c,     draw_rect, border_radius=10)
        pygame.draw.rect(self.screen, GREEN, draw_rect, 2,  border_radius=10)

        txt = "¡ C L I C !"
        draw_text(self.screen, txt, self.f_click, GREEN, draw_rect.centerx, draw_rect.centery, "center")

        hint = "[ESPACIO]" if not hov else "clic aquí"
        draw_text(self.screen, hint, self.f_sm, MUTED,
                  draw_rect.centerx, draw_rect.bottom - 14, "center")
        return y + btn_h

    def _draw_prestige_section(self, x, y, w, mx, my) -> int:
        g = self.game
        btn_h = 40
        if g.can_prestige():
            rect = pygame.Rect(x, y, w, btn_h)
            self._prestige_rect = rect
            hov  = rect.collidepoint(mx, my)
            c    = (80, 55, 10) if not hov else (110, 80, 15)
            pygame.draw.rect(self.screen, c,    rect, border_radius=8)
            pygame.draw.rect(self.screen, GOLD, rect, 2, border_radius=8)
            n    = g.prestige_count + 1
            mult = "×1.5" if g.prestige_count == 0 else "×2.0"
            draw_text(self.screen, f"★  PRESTIGE {n}  ({mult} permanente)",
                      self.f_btn, GOLD, rect.centerx, rect.centery, "center")
        else:
            self._prestige_rect = None
            remaining = g.prestige_threshold() - g.total_points
            n = g.prestige_count + 1
            if n <= 2:
                msg = f"Faltan {fmt(remaining)} pts → Prestige {n}"
                draw_text(self.screen, msg, self.f_sm, MUTED, x, y + (btn_h - 14) // 2)
            else:
                draw_text(self.screen, "2 reinicios completados", self.f_sm, MUTED, x, y + (btn_h - 14) // 2)
        return y + btn_h

    def _draw_minigame_section(self, x, y, w, mx, my) -> int:
        g   = self.game
        now = time.time()
        btn_h = 40

        if g.minigame_active:
            # Boost activo
            left = g.minigame_seconds_left()
            bar_w = int(w * left / 30.0)
            bg_r  = pygame.Rect(x, y, w, btn_h)
            bar_r = pygame.Rect(x, y, bar_w, btn_h)
            pygame.draw.rect(self.screen, (40, 20, 60), bg_r,  border_radius=8)
            pygame.draw.rect(self.screen, (70, 40, 100), bar_r, border_radius=8)
            pygame.draw.rect(self.screen, PURPLE, bg_r, 2, border_radius=8)
            draw_text(self.screen, f"★ BOOST ×2  activo  {left:.0f}s",
                      self.f_btn, PURPLE, bg_r.centerx, bg_r.centery, "center")
            self._mini_rect = None

        elif self.mini_available:
            rect = pygame.Rect(x, y, w, btn_h)
            self._mini_rect = rect
            hov  = rect.collidepoint(mx, my)
            c    = (45, 30, 70) if not hov else (65, 45, 100)
            pygame.draw.rect(self.screen, c,      rect, border_radius=8)
            pygame.draw.rect(self.screen, PURPLE, rect, 2, border_radius=8)
            draw_text(self.screen, "★  MINIJUEGO DISPONIBLE  ★",
                      self.f_btn, PURPLE, rect.centerx, rect.centery, "center")
        else:
            self._mini_rect = None
            cd = max(0.0, self.next_minigame - now)
            draw_text(self.screen, f"Minijuego en: {fmt_time(cd)}", self.f_sm, MUTED, x, y + 13)

        return y + btn_h

    # ─────────────────────────────────────────────────────────────────────────
    # Divisor vertical
    # ─────────────────────────────────────────────────────────────────────────
    def _draw_divider(self):
        pygame.draw.line(self.screen, BORDER, (SPLIT, HDR_H), (SPLIT, H - STS_H), 1)

    # ─────────────────────────────────────────────────────────────────────────
    # Panel derecho
    # ─────────────────────────────────────────────────────────────────────────
    def _draw_right(self, mx, my):
        x0 = SPLIT + PAD
        y0 = HDR_H + PAD
        pw = W - SPLIT - PAD * 2

        y = y0
        y = self._draw_generators(x0, y, pw, mx, my)
        y += PAD
        pygame.draw.line(self.screen, BORDER, (x0, y), (x0 + pw, y), 1)
        y += PAD
        self._draw_upgrades(x0, y, pw, mx, my)

    def _draw_generators(self, x, y, w, mx, my) -> int:
        draw_text(self.screen, "GENERADORES", self.f_med, TXT, x, y)
        y += 26

        row_h   = 68
        btn_w   = 130
        btn_h   = 30

        for i, gen in enumerate(GENERATORS):
            rect = pygame.Rect(x, y, w, row_h - 4)
            locked = not self.game.generator_unlocked(gen["id"])

            if locked:
                draw_panel(self.screen, rect, color=(18, 22, 27))
                draw_text(self.screen, "???", self.f_med, MUTED, x + PAD, y + (row_h - 4) // 2 - 9)
                draw_text(self.screen, "bloqueado", self.f_sm, BTN_D[0:3], x + 60, y + (row_h - 4) // 2 - 7)
                self._gen_rects[i] = None
                y += row_h
                continue

            owned    = self.game.generators[gen["id"]]
            cost     = self.game.generator_cost(gen["id"])
            can_buy  = self.game.can_buy_generator(gen["id"])
            pps_each = gen["pps"] * self.game.prestige_multiplier
            pps_tot  = pps_each * owned

            bg_c = (25, 32, 42) if can_buy else PANEL
            draw_panel(self.screen, rect, color=bg_c)

            # Nombre + cantidad
            draw_text(self.screen, gen["name"], self.f_med, TXT, x + PAD, y + 10)
            count_c = ACCENT if owned > 0 else MUTED
            draw_text(self.screen, f"×{owned}", self.f_med, count_c, x + PAD + 130, y + 10)

            # PPS info  (incluye BOOST y prestige_multiplier)
            pps_each_real = pps_each * BOOST
            pps_tot_real  = pps_each_real * owned
            pps_str = f"+{fmt(pps_tot_real)}/s" if owned > 0 else f"{fmt(pps_each_real)}/s c/u"
            draw_text(self.screen, pps_str, self.f_sm, MUTED, x + PAD, y + 36)

            # Botón comprar
            btn_rect = pygame.Rect(x + w - btn_w - PAD, y + (row_h - 4 - btn_h) // 2, btn_w, btn_h)
            self._gen_rects[i] = btn_rect
            hov  = btn_rect.collidepoint(mx, my)
            bc   = GREEN_D if can_buy else (30, 25, 25)
            bc   = lerp_color(bc, (50, 110, 60), 0.5) if (hov and can_buy) else bc
            pygame.draw.rect(self.screen, bc, btn_rect, border_radius=6)
            bord = GREEN if can_buy else RED
            pygame.draw.rect(self.screen, bord, btn_rect, 1, border_radius=6)
            txt_c = GREEN if can_buy else RED
            draw_text(self.screen, fmt(cost), self.f_btn, txt_c,
                      btn_rect.centerx, btn_rect.centery, "center")

            y += row_h

        return y

    def _draw_upgrades(self, x, y, w, mx, my) -> int:
        draw_text(self.screen, "MEJORAS DE CLIC", self.f_med, TXT, x, y)
        y += 26

        row_h  = 54
        btn_w  = 130
        btn_h  = 28

        for i, upg in enumerate(CLICK_UPGRADES):
            rect   = pygame.Rect(x, y, w, row_h - 4)
            locked = not self.game.click_upgrade_unlocked(upg["id"])
            bought = self.game.click_upgrades[upg["id"]]

            if locked:
                draw_panel(self.screen, rect, color=(18, 22, 27))
                draw_text(self.screen, "??? [bloqueado]", self.f_sm, MUTED,
                          x + PAD, y + (row_h - 4) // 2 - 7)
                self._upg_rects[i] = None
                y += row_h
                continue

            bg_c = (25, 32, 42) if (not bought and self.game.points >= self.game.click_upgrade_cost(upg["id"])) else PANEL
            draw_panel(self.screen, rect, color=bg_c)

            draw_text(self.screen, upg["name"], self.f_med, TXT, x + PAD, y + 10)
            bonus_str = f"+{upg['bonus'] * 100}/clic"
            draw_text(self.screen, bonus_str, self.f_sm, MUTED, x + PAD, y + 32)

            if bought:
                draw_text(self.screen, "✓ COMPRADO", self.f_btn, GREEN,
                          x + w - btn_w - PAD + 15, y + (row_h - 4) // 2 - 9)
                self._upg_rects[i] = None
            else:
                cost    = self.game.click_upgrade_cost(upg["id"])
                can_buy = self.game.points >= cost
                btn_rect = pygame.Rect(x + w - btn_w - PAD, y + (row_h - 4 - btn_h) // 2, btn_w, btn_h)
                self._upg_rects[i] = btn_rect
                hov  = btn_rect.collidepoint(mx, my)
                bc   = GREEN_D if can_buy else (30, 25, 25)
                bc   = lerp_color(bc, (50, 110, 60), 0.5) if (hov and can_buy) else bc
                pygame.draw.rect(self.screen, bc, btn_rect, border_radius=6)
                bord = GREEN if can_buy else RED
                pygame.draw.rect(self.screen, bord, btn_rect, 1, border_radius=6)
                txt_c = GREEN if can_buy else RED
                draw_text(self.screen, fmt(cost), self.f_btn, txt_c,
                          btn_rect.centerx, btn_rect.centery, "center")

            y += row_h

        return y

    # ─────────────────────────────────────────────────────────────────────────
    # Barra de estado
    # ─────────────────────────────────────────────────────────────────────────
    def _draw_status_bar(self):
        rect = pygame.Rect(0, H - STS_H, W, STS_H)
        pygame.draw.rect(self.screen, PANEL, rect)
        pygame.draw.line(self.screen, BORDER, (0, H - STS_H), (W, H - STS_H), 1)

        now = time.time()
        if self.status_msg and now < self.status_end:
            draw_text(self.screen, self.status_msg, self.f_sm,
                      getattr(self, "status_color", TXT), PAD, H - STS_H + 8)
        else:
            draw_text(self.screen, "ESPACIO: clic  |  clic sobre generadores/mejoras para comprar  |  ESC cierra modales",
                      self.f_sm, MUTED, PAD, H - STS_H + 8)

    # ─────────────────────────────────────────────────────────────────────────
    # Partículas flotantes
    # ─────────────────────────────────────────────────────────────────────────
    def _draw_particles(self):
        for p in self.particles:
            surf = self.f_part.render(p.text, True, p.color)
            surf.set_alpha(p.alpha)
            self.screen.blit(surf, (int(p.x - surf.get_width() // 2), int(p.y)))

    # ─────────────────────────────────────────────────────────────────────────
    # Modal minijuego
    # ─────────────────────────────────────────────────────────────────────────
    def _draw_minigame_modal(self, mx, my):
        # Overlay oscuro
        overlay = pygame.Surface((W, H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        self.screen.blit(overlay, (0, 0))

        mw, mh = 480, 300
        mx0 = (W - mw) // 2
        my0 = (H - mh) // 2
        modal_rect = pygame.Rect(mx0, my0, mw, mh)

        draw_panel(self.screen, modal_rect, color=(28, 20, 50), border=PURPLE, radius=12)
        pygame.draw.rect(self.screen, PURPLE, modal_rect, 2, border_radius=12)

        draw_text(self.screen, "M I N I J U E G O", self.f_title, PURPLE,
                  mx0 + mw // 2, my0 + 22, "center")
        draw_text(self.screen, "Adivina el número del  1  al  9", self.f_med, TXT,
                  mx0 + mw // 2, my0 + 55, "center")

        # Botones 1-9
        num_w, num_h = 44, 44
        gap = 10
        total_w = 9 * num_w + 8 * gap
        start_x = mx0 + (mw - total_w) // 2
        btn_y   = my0 + 105

        self._mini_num_rects = []
        result_shown = self.mini_selected != -1

        for i in range(9):
            bx   = start_x + i * (num_w + gap)
            brect = pygame.Rect(bx, btn_y, num_w, num_h)
            self._mini_num_rects.append(brect)

            n = i + 1
            if result_shown:
                if n == self.mini_answer:
                    bc = (30, 90, 40)
                    tc = GREEN
                elif n == self.mini_selected:
                    bc = RED_D
                    tc = RED
                else:
                    bc = BTN_D
                    tc = MUTED
            else:
                hov = brect.collidepoint(mx, my)
                bc  = (55, 40, 90) if hov else (38, 28, 65)
                tc  = TXT

            pygame.draw.rect(self.screen, bc, brect, border_radius=6)
            pygame.draw.rect(self.screen, PURPLE if not result_shown else tc, brect, 1, border_radius=6)
            draw_text(self.screen, str(n), self.f_click, tc, bx + num_w // 2, btn_y + num_h // 2, "center")

        # Mensaje resultado
        if result_shown:
            if self.mini_selected == self.mini_answer:
                msg = "¡CORRECTO!  Boost ×2 activo 30s"
                c   = GREEN
            else:
                msg = f"Fallaste.  Era el  {self.mini_answer}"
                c   = RED
            draw_text(self.screen, msg, self.f_med, c, mx0 + mw // 2, my0 + 205, "center")
        else:
            draw_text(self.screen, "ESC para cancelar", self.f_sm, MUTED,
                      mx0 + mw // 2, my0 + 270, "center")

    # ─────────────────────────────────────────────────────────────────────────
    # Overlay de victoria
    # ─────────────────────────────────────────────────────────────────────────
    def _draw_victory_overlay(self):
        if self.game.infinite_mode and time.time() - self.start_time < 5:
            return   # solo mostrar los primeros 5s; luego desaparece

        overlay = pygame.Surface((W, H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 210))
        self.screen.blit(overlay, (0, 0))

        vw, vh = 500, 320
        vx = (W - vw) // 2
        vy = (H - vh) // 2
        vr = pygame.Rect(vx, vy, vw, vh)

        draw_panel(self.screen, vr, color=(20, 30, 20), border=GOLD, radius=14)
        pygame.draw.rect(self.screen, GOLD, vr, 2, border_radius=14)

        draw_text(self.screen, "¡  V I C T O R I A  !", self.f_big, GOLD,
                  vx + vw // 2, vy + 30, "center")
        pygame.draw.line(self.screen, GOLD, (vx + 40, vy + 70), (vx + vw - 40, vy + 70), 1)

        lines = [
            ("Tiempo",      fmt_time(time.time() - self.start_time), TXT),
            ("Puntuación",  fmt(self.game.high_score),                GOLD),
            ("Reinicios",   f"{self.game.prestige_count} / 2",        ORANGE),
            ("Multiplicador", f"×{self.game.prestige_multiplier:.1f}", ACCENT),
        ]
        for j, (label, val, c) in enumerate(lines):
            ry = vy + 90 + j * 38
            draw_text(self.screen, label + ":", self.f_med, MUTED,   vx + 60,       ry)
            draw_text(self.screen, val,         self.f_med, c,        vx + vw - 60,  ry, "topright")

        draw_text(self.screen, "★  MODO INFINITO DESBLOQUEADO  ★", self.f_btn, GREEN,
                  vx + vw // 2, vy + 250, "center")
        draw_text(self.screen, "Haz clic en cualquier parte para continuar", self.f_sm, MUTED,
                  vx + vw // 2, vy + 284, "center")


# ═══════════════════════════════════════════════════════════════════════════════
# Punto de entrada
# ═══════════════════════════════════════════════════════════════════════════════
def main():
    ui = GameUI()
    ui.run()
