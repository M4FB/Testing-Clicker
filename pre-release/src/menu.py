"""Menú principal pre-release: gradiente, nebulosas, parallax, título animado."""
import math
import random
import sys
import time

import pygame

from src.config import MODE
from src.fx import (
    BG, BG2, BORDER, TXT, MUTED, ACCENT, GOLD, GREEN, ORANGE, PURPLE,
    lerp_color, ease_out, draw_text, vgradient,
    Nebula, StarField, shiny_button, draw_coin,
)

FONT_REG  = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


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
        self._alpha = random.randint(50, 110)
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

    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.clock  = pygame.time.Clock()
        self.W      = screen.get_width()
        self.H      = screen.get_height()

        self.f_title = _font(56, bold=True)
        self.f_sub   = _font(17)
        self.f_btn   = _font(20, bold=True)
        self.f_float = _font(13)
        self.f_hint  = _font(12)
        self.f_badge = _font(13, bold=True)

        self.bg_grad  = vgradient(self.W, self.H, BG, BG2)
        self.nebulas  = [Nebula(self.W, self.H) for _ in range(4)]
        self.stars    = StarField(self.W, self.H, 130)
        self.floats: list[_FloatText] = []
        self._next_float = time.time()

        btn_w, btn_h = 320, 56
        cx, cy0, gap = self.W // 2, self.H // 2 + 36, 72
        self.buttons = [
            {"label": "NUEVA PARTIDA", "action": "new",  "en": True,
             "rect": pygame.Rect(cx - btn_w // 2, cy0,           btn_w, btn_h)},
            {"label": "CONTINUAR",     "action": "cont", "en": False,
             "rect": pygame.Rect(cx - btn_w // 2, cy0 + gap,     btn_w, btn_h)},
            {"label": "SALIR",         "action": "quit", "en": True,
             "rect": pygame.Rect(cx - btn_w // 2, cy0 + gap * 2, btn_w, btn_h)},
        ]
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

        cx      = self.W // 2
        elapsed = now - self._t0
        cy_t    = self.H // 2 - 116

        # ── Monedas girando a los lados del título ─────────────────────────
        tw = self.f_title.size(self.TITLE)[0]
        draw_coin(self.screen, cx - tw // 2 - 56, cy_t, 24, now, speed=1.2)
        draw_coin(self.screen, cx + tw // 2 + 56, cy_t, 24, now + 1.3, speed=1.2)

        # ── Título: letras que ondulan con glow ────────────────────────────
        pulse     = 0.5 + 0.5 * math.sin(elapsed * 1.4)
        base_col  = lerp_color(ACCENT, (170, 215, 255), pulse * 0.5)
        x = cx - tw // 2
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
                self.screen.blit(glow, (x + dx, cy_t - glyph.get_height() // 2 + bob + dy))
            self.screen.blit(glyph, (x, cy_t - glyph.get_height() // 2 + bob))
            x += glyph.get_width()

        # ── Badge PRE-RELEASE + modo ────────────────────────────────────────
        badge = self.f_badge.render("PRE-RELEASE", True, (16, 20, 30))
        bw, bh = badge.get_width() + 22, 24
        br = pygame.Rect(cx - bw // 2, cy_t + 46, bw, bh)
        pygame.draw.rect(self.screen, lerp_color(GOLD, ORANGE, pulse * 0.5), br,
                         border_radius=12)
        self.screen.blit(badge, badge.get_rect(center=br.center))

        mode_col = ORANGE if MODE == "demo" else ACCENT
        draw_text(self.screen, f"[ {MODE.upper()} ]", self.f_sub, mode_col,
                  cx, cy_t + 90, "center")
        draw_text(self.screen, "Laboratorio de Testing de Software", self.f_sub,
                  MUTED, cx, cy_t + 114, "center")
        pygame.draw.line(self.screen, BORDER,
                         (cx - 200, cy_t + 136), (cx + 200, cy_t + 136), 1)

        # ── Botones ──────────────────────────────────────────────────────────
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

        draw_text(self.screen, "ENTER: nueva partida   |   ESC: salir",
                  self.f_hint, MUTED, cx, self.H - 18, "center")
        pygame.display.flip()
