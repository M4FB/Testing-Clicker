"""Menú principal.

Distribución a dos columnas:
  • Izquierda  → título animado, identidad del proyecto y botones (alineados).
  • Derecha    → tarjeta animada con las estadísticas de la última partida.
Abajo, los créditos de autoría. Fondo procedural (gradiente, nebulosas,
parallax de estrellas y textos flotantes de ambiente) heredado de fx.py.
"""
import math
import random
import sys
import time

import pygame

from src.config import MODE, VICTORY_THRESHOLD
from src.save import has_compatible_save, save_info
from src.fx import (
    BG, BG2, BORDER, PANEL, TXT, MUTED, ACCENT, GOLD, GREEN, ORANGE, PURPLE,
    lerp_color, scale_color, draw_text, vgradient,
    Nebula, StarField, shiny_button, striped_bar, draw_coin, Roll,
)
from src.ui.common import fmt, fmt_time, draw_panel

FONT_REG  = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

CREDITS = ("Realizado por:  2023800251 - Avendaño Marcelo (G02)"
           "     ·     2023602171 - Lipa Luis (G01)")


def _font(size, bold=False):
    try:
        return pygame.font.Font(FONT_BOLD if bold else FONT_REG, size)
    except Exception:
        return pygame.font.SysFont("sans", size, bold=bold)


# ── Texto flotante de ambiente (+X) ──────────────────────────────────────────
class _FloatText:
    _VALUES = ["+1", "+5", "+10", "+50", "+100", "+500", "+1K", "+1M"]
    _COLORS = [ACCENT, GOLD, GREEN, PURPLE, (200, 220, 255)]

    def __init__(self, w, h):
        self.x      = random.randint(w // 6, w * 5 // 6)
        self.y      = float(h + random.randint(10, 60))
        self.speed  = random.uniform(16, 42)
        self.text   = random.choice(self._VALUES)
        self.color  = random.choice(self._COLORS)
        self._alpha = random.randint(40, 90)
        self._born  = time.time()
        self._life  = random.uniform(5.0, 9.0)

    @property
    def alive(self):
        return (time.time() - self._born) < self._life

    def update(self, dt):
        self.y -= self.speed * dt

    def draw(self, surf, font):
        t = (time.time() - self._born) / self._life
        if t < 0.12:
            a = int(self._alpha * t / 0.12)
        elif t > 0.72:
            a = int(self._alpha * (1.0 - t) / 0.28)
        else:
            a = self._alpha
        s = font.render(self.text, True, self.color)
        s.set_alpha(max(0, a))
        surf.blit(s, (int(self.x - s.get_width() // 2), int(self.y)))


# ── Menú principal ────────────────────────────────────────────────────────────
class MainMenu:
    TITLE = "CLICKER GAME"

    # Geometría de las columnas
    LX   = 70                      # margen izquierdo
    PANEL = pygame.Rect(566, 96, 394, 474)   # tarjeta de estadísticas (derecha)

    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.clock  = pygame.time.Clock()
        self.W      = screen.get_width()
        self.H      = screen.get_height()

        self.f_title = _font(50, bold=True)
        self.f_sub   = _font(16)
        self.f_btn   = _font(20, bold=True)
        self.f_float = _font(13)
        self.f_hint  = _font(12)
        self.f_badge = _font(13, bold=True)
        self.f_card  = _font(15, bold=True)   # cabecera tarjeta
        self.f_big   = _font(34, bold=True)   # número grande (acumulado)
        self.f_lbl   = _font(12)              # etiquetas pequeñas
        self.f_val   = _font(18, bold=True)   # valores
        self.f_cred  = _font(13)

        self.bg_grad = vgradient(self.W, self.H, BG, BG2)
        self.nebulas = [Nebula(self.W, self.H) for _ in range(4)]
        self.stars   = StarField(self.W, self.H, 130)
        self.floats: list[_FloatText] = []
        self._next_float = time.time()

        # ── Botones, alineados a la izquierda (mismo borde, misma anchura) ──
        btn_w, btn_h, gap = 300, 56, 74
        cy0 = 318
        self.buttons = [
            {"label": "NUEVA PARTIDA", "action": "new",  "en": True,
             "rect": pygame.Rect(self.LX, cy0,           btn_w, btn_h)},
            {"label": "CONTINUAR",     "action": "cont", "en": has_compatible_save(),
             "rect": pygame.Rect(self.LX, cy0 + gap,     btn_w, btn_h)},
            {"label": "SALIR",         "action": "quit", "en": True,
             "rect": pygame.Rect(self.LX, cy0 + gap * 2, btn_w, btn_h)},
        ]

        # ── Datos de la última partida + números rodantes (animación) ──────
        self.save   = save_info()
        self.r_total = Roll(0.0)
        self.r_high  = Roll(0.0)
        self.r_prog  = Roll(0.0)
        self._t0 = time.time()

    # ── Loop ──────────────────────────────────────────────────────────────────
    def run(self) -> str:
        prev = time.time()
        while True:
            now  = time.time()
            dt   = min(0.05, now - prev)
            prev = now

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        return "quit"
                    if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        return "new"
                    if event.key == pygame.K_F11:
                        try:
                            pygame.display.toggle_fullscreen()
                        except pygame.error:
                            pass
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for btn in self.buttons:
                        if btn["en"] and btn["rect"].collidepoint(event.pos):
                            return btn["action"]

            if now >= self._next_float:
                self.floats.append(_FloatText(self.W, self.H))
                self._next_float = now + random.uniform(0.5, 1.3)
            self.floats = [f for f in self.floats if f.alive]
            for f in self.floats:
                f.update(dt)
            for n in self.nebulas:
                n.update(dt)
            self.stars.update(dt)

            # Animación de los contadores de la tarjeta
            if self.save:
                self.r_total.tick(float(self.save.get("total_points", 0.0)), dt)
                self.r_high.tick(float(self.save.get("high_score", 0.0)), dt)
                prog = min(1.0, float(self.save.get("total_points", 0.0)) /
                           max(1.0, VICTORY_THRESHOLD))
                self.r_prog.tick(prog, dt)

            mx, my = pygame.mouse.get_pos()
            self._draw(mx, my, now)
            self.clock.tick(60)

    # ── Dibujo ────────────────────────────────────────────────────────────────
    def _draw(self, mx, my, now):
        self.screen.blit(self.bg_grad, (0, 0))
        for n in self.nebulas:
            n.draw(self.screen)
        self.stars.draw(self.screen)
        for f in self.floats:
            f.draw(self.screen, self.f_float)

        self._draw_left(now)
        self._draw_panel(now)
        self._draw_buttons(mx, my, now)

        # ── Pie: créditos de autoría + atajos ──────────────────────────────
        draw_text(self.screen, "ENTER: nueva partida   |   F11: pantalla completa   |   ESC: salir",
                  self.f_hint, MUTED, self.W // 2, self.H - 40, "center")
        cred = self.f_cred.render(CREDITS, True, (150, 162, 182))
        bar  = pygame.Rect(0, self.H - 24, self.W, 24)
        strip = pygame.Surface(bar.size, pygame.SRCALPHA)
        strip.fill((10, 13, 22, 150))
        self.screen.blit(strip, bar.topleft)
        self.screen.blit(cred, cred.get_rect(center=(self.W // 2, self.H - 12)))
        pygame.display.flip()

    # ── Columna izquierda: título + identidad ──────────────────────────────
    def _draw_left(self, now):
        elapsed = now - self._t0
        cx      = self.LX
        base_y  = 120

        # Monedas girando flanqueando el título
        draw_coin(self.screen, cx - 18, base_y, 18, now, speed=1.2)

        # Título: letras que ondulan con glow, alineadas a la izquierda
        pulse    = 0.5 + 0.5 * math.sin(elapsed * 1.4)
        base_col = lerp_color(ACCENT, (170, 215, 255), pulse * 0.5)
        x = cx + 20
        for i, ch in enumerate(self.TITLE):
            if ch == " ":
                x += self.f_title.size(" ")[0]
                continue
            bob   = math.sin(elapsed * 2.1 + i * 0.45) * 4
            col   = lerp_color(base_col, GOLD, 0.25 + 0.25 * math.sin(elapsed + i * 0.6))
            glyph = self.f_title.render(ch, True, col)
            glow  = glyph.copy()
            glow.set_alpha(int(26 + 30 * pulse))
            for dx, dy in ((-3, 0), (3, 0), (0, -3), (0, 3)):
                self.screen.blit(glow, (x + dx, base_y - glyph.get_height() // 2 + bob + dy))
            self.screen.blit(glyph, (x, base_y - glyph.get_height() // 2 + bob))
            x += glyph.get_width()

        # Badge de versión + modo + subtítulo
        badge = self.f_badge.render("v1.0", True, (16, 20, 30))
        bw, bh = badge.get_width() + 22, 24
        br = pygame.Rect(cx, base_y + 40, bw, bh)
        pygame.draw.rect(self.screen, lerp_color(GOLD, ORANGE, pulse * 0.5), br,
                         border_radius=12)
        self.screen.blit(badge, badge.get_rect(center=br.center))

        mode_col = ORANGE if MODE == "demo" else ACCENT
        draw_text(self.screen, f"[ {MODE.upper()} ]", self.f_sub, mode_col,
                  br.right + 14, br.centery, "midleft")
        draw_text(self.screen, "Laboratorio de Testing de Software", self.f_sub,
                  MUTED, cx, base_y + 86, "midleft")
        pygame.draw.line(self.screen, BORDER,
                         (cx, base_y + 112), (cx + 300, base_y + 112), 1)

    # ── Botones ────────────────────────────────────────────────────────────
    def _draw_buttons(self, mx, my, now):
        for bi, btn in enumerate(self.buttons):
            rect = btn["rect"]
            hov  = btn["en"] and rect.collidepoint(mx, my)
            if not btn["en"]:
                pygame.draw.rect(self.screen, (17, 21, 29), rect, border_radius=10)
                pygame.draw.rect(self.screen, (30, 36, 46), rect, 1, border_radius=10)
                tc = (48, 54, 65)
            else:
                primary = btn["action"] == "new"
                base    = (28, 42, 64) if primary else (26, 32, 44)
                border  = ACCENT if (hov or primary) else BORDER
                glow    = (0.4 + 0.6 * (0.5 + 0.5 * math.sin(now * 2.2))) if primary else \
                          (0.8 if hov else 0.0)
                shiny_button(self.screen, rect, base, border, hover=hov,
                             glow=glow, shine=primary, now=now + bi * 0.7, radius=10)
                tc = (235, 243, 255) if hov else TXT
            draw_text(self.screen, btn["label"], self.f_btn, tc,
                      rect.centerx, rect.centery, "center")

    # ── Tarjeta de estadísticas (derecha) ──────────────────────────────────
    def _draw_panel(self, now):
        p = self.PANEL
        pulse = 0.5 + 0.5 * math.sin(now * 1.6)

        # Glow del borde (animación)
        gs = pygame.Surface((p.width + 24, p.height + 24), pygame.SRCALPHA)
        pygame.draw.rect(gs, (*ACCENT, int(28 + 26 * pulse)),
                         gs.get_rect().inflate(-6, -6), 2, border_radius=16)
        self.screen.blit(gs, (p.x - 12, p.y - 12))
        draw_panel(self.screen, p, color=(18, 22, 33), border=BORDER, radius=14)

        pad = 18
        x0, y = p.x + pad, p.y + pad

        # Cabecera: título + moneda girando + badge de modo
        draw_text(self.screen, "ÚLTIMA PARTIDA", self.f_card, TXT, x0, y, "topleft")
        draw_coin(self.screen, p.right - pad - 14, y + 8, 13, now, speed=1.4)
        save = self.save

        if not save:
            draw_text(self.screen, "Sin partida guardada", self.f_val, MUTED,
                      p.centerx, p.centery - 24, "center")
            draw_text(self.screen, "Pulsa NUEVA PARTIDA para empezar", self.f_lbl,
                      (96, 106, 124), p.centerx, p.centery + 4, "center")
            draw_coin(self.screen, p.centerx, p.centery - 70, 26, now, speed=1.1)
            return

        smode = str(save.get("mode", "?")).upper()
        mcol  = ORANGE if smode == "DEMO" else ACCENT
        mbw   = self.f_lbl.size(smode)[0] + 16
        mbr   = pygame.Rect(p.right - pad - 34 - mbw, y - 2, mbw, 18)
        # (el badge de modo va a la izquierda de la moneda)
        mbr.right = p.right - pad - 30
        pygame.draw.rect(self.screen, (28, 34, 48), mbr, border_radius=9)
        pygame.draw.rect(self.screen, mcol, mbr, 1, border_radius=9)
        draw_text(self.screen, smode, self.f_lbl, mcol, mbr.centerx, mbr.centery, "center")

        pygame.draw.line(self.screen, BORDER, (x0, y + 30), (p.right - pad, y + 30), 1)
        y += 44

        # Número grande: total acumulado (rodante)
        draw_text(self.screen, "TOTAL ACUMULADO", self.f_lbl, MUTED, x0, y, "topleft")
        draw_text(self.screen, fmt(self.r_total.v), self.f_big, GOLD, x0, y + 16, "topleft")
        if save.get("won"):
            draw_text(self.screen, "★ ¡VICTORIA!", self.f_lbl, GREEN,
                      p.right - pad, y + 26, "topright")
        y += 64

        # Barra de progreso hacia la victoria (rayas animadas)
        draw_text(self.screen, "Progreso a la victoria", self.f_lbl, MUTED, x0, y, "topleft")
        bar = pygame.Rect(x0, y + 18, p.width - pad * 2, 14)
        striped_bar(self.screen, bar, self.r_prog.v, GREEN, now=now)
        draw_text(self.screen, f"{self.r_prog.v * 100:.1f}%", self.f_lbl, TXT,
                  bar.right, y - 1, "topright")
        y += 46

        # Récord
        draw_text(self.screen, "RÉCORD (puntos a la vez)", self.f_lbl, MUTED, x0, y, "topleft")
        draw_text(self.screen, fmt(self.r_high.v), self.f_val, ACCENT,
                  p.right - pad, y - 2, "topright")
        y += 28
        pygame.draw.line(self.screen, BORDER, (x0, y), (p.right - pad, y), 1)
        y += 12

        # Rejilla de estadísticas (2 columnas)
        st = save.get("stats", {}) or {}
        rows = [
            ("Clics",       f"{st.get('clicks', 0):,}".replace(",", " "),
             "Críticos",    f"{st.get('crits', 0):,}".replace(",", " ")),
            ("Doradas",     str(st.get("golden", 0)),
             "Minijuegos",  f"{st.get('mini_won', 0)}/"
                            f"{st.get('mini_won', 0) + st.get('mini_lost', 0)}"),
            ("Prestigios",  str(save.get("prestige_count", 0)),
             "Puntos PP",   str(save.get("prestige_points", 0))),
        ]
        colw = (p.width - pad * 2) // 2
        for l1, v1, l2, v2 in rows:
            self._stat_cell(x0,         y, colw, l1, v1)
            self._stat_cell(x0 + colw,  y, colw, l2, v2)
            y += 40

        # Pie de la tarjeta: tiempo jugado + fecha de guardado
        y = p.bottom - pad - 16
        pygame.draw.line(self.screen, BORDER, (x0, y - 8), (p.right - pad, y - 8), 1)
        draw_text(self.screen, f"Tiempo jugado:  {fmt_time(save.get('elapsed', 0.0))}",
                  self.f_lbl, MUTED, x0, y, "topleft")
        ts = save.get("saved_at")
        if ts:
            when = time.strftime("%d/%m/%Y %H:%M", time.localtime(ts))
            draw_text(self.screen, when, self.f_lbl, MUTED,
                      p.right - pad, y, "topright")

    def _stat_cell(self, x, y, w, label, value):
        draw_text(self.screen, label, self.f_lbl, MUTED, x + 4, y, "topleft")
        draw_text(self.screen, value, self.f_val, TXT, x + 4, y + 14, "topleft")
