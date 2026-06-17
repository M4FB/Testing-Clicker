"""Cabecera (modo, título, logros, pantalla completa, tiempo) y barra de estado."""
import math
import time

import pygame

from src.config import MODE
from src.fx import (
    PANEL, BORDER, TXT, MUTED, ACCENT, GOLD, GOLD_D, ORANGE,
    lerp_color, draw_text, draw_coin,
)
from src.ui.common import W, H, HDR_H, STS_H, PAD, fmt, fmt_time
from src import achievements as ach


def _draw_medal(cv, cx, cy, r=8):
    pygame.draw.polygon(cv, (160, 40, 50),
                        [(cx - r + 2, cy - r - 2), (cx - 1, cy),
                         (cx - r - 3, cy + 2)])
    pygame.draw.polygon(cv, (40, 70, 160),
                        [(cx + r - 2, cy - r - 2), (cx + 1, cy),
                         (cx + r + 3, cy + 2)])
    pygame.draw.circle(cv, GOLD_D, (cx, cy + 2), r)
    pygame.draw.circle(cv, GOLD, (cx, cy + 2), r - 2)
    pygame.draw.circle(cv, (255, 235, 150), (cx - 2, cy), 2)


class HeaderBar:
    def __init__(self, ui):
        self.ui = ui
        self.ach_rect: pygame.Rect | None = None
        self.fs_rect:  pygame.Rect | None = None

    def click(self, mx, my) -> bool:
        if self.ach_rect and self.ach_rect.collidepoint(mx, my):
            self.ui.toggle_achievements()
            return True
        if self.fs_rect and self.fs_rect.collidepoint(mx, my):
            self.ui.toggle_fullscreen()
            return True
        return False

    def draw(self, cv, mx, my):
        ui  = self.ui
        now = time.time()
        pygame.draw.rect(cv, PANEL, pygame.Rect(0, 0, W, HDR_H))
        sh = pygame.Surface((W, 1), pygame.SRCALPHA)
        sh.fill((255, 255, 255, 22))
        cv.blit(sh, (0, 0))
        pygame.draw.line(cv, BORDER, (0, HDR_H), (W, HDR_H), 1)

        tag_c = ORANGE if MODE == "demo" else ACCENT
        draw_text(cv, f"[{MODE.upper()}]", ui.F["title"], tag_c,
                  PAD, HDR_H // 2, "midleft")

        pulse   = 0.5 + 0.5 * math.sin(now * 1.4)
        title_c = lerp_color(TXT, (235, 242, 255), pulse * 0.5)
        draw_coin(cv, W // 2 - 118, HDR_H // 2, 13, now, speed=1.1)
        draw_text(cv, "CLICKER  GAME", ui.F["title"], title_c,
                  W // 2, HDR_H // 2, "center")
        draw_text(cv, "v1.0", ui.F["xs"], GOLD,
                  W // 2 + 110, HDR_H // 2 + 1, "midleft")

        # ── Botón de logros (medalla + n/total) ──────────────────────────────
        n_un  = ach.unlocked_count(ui.game)
        label = f"{n_un}/{len(ach.ACHIEVEMENTS)}"
        bw    = (34 + ui.F["xs"].size("LOGROS")[0] + 10
                 + ui.F["xs"].size(label)[0] + 10)
        r     = pygame.Rect(W - PAD - 235, (HDR_H - 28) // 2, bw, 28)
        hov   = r.collidepoint(mx, my)
        pygame.draw.rect(cv, (30, 36, 52) if hov else (24, 29, 42), r,
                         border_radius=8)
        pygame.draw.rect(cv, GOLD if hov else BORDER, r, 1, border_radius=8)
        _draw_medal(cv, r.x + 16, r.centery - 1)
        draw_text(cv, "LOGROS", ui.F["xs"], GOLD if hov else MUTED,
                  r.x + 30, r.centery, "midleft")
        draw_text(cv, label, ui.F["xs"], TXT, r.right - 8, r.centery, "midright")
        self.ach_rect = r

        # ── Botón de pantalla completa (esquinas) ────────────────────────────
        fr  = pygame.Rect(r.right + 8, (HDR_H - 28) // 2, 30, 28)
        hov = fr.collidepoint(mx, my)
        pygame.draw.rect(cv, (30, 36, 52) if hov else (24, 29, 42), fr,
                         border_radius=8)
        pygame.draw.rect(cv, ACCENT if hov else BORDER, fr, 1, border_radius=8)
        c   = ACCENT if hov else MUTED
        bx, by, s = fr.centerx, fr.centery, 5
        for sx, sy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
            px, py = bx + sx * 7, by + sy * 6
            pygame.draw.line(cv, c, (px, py), (px - sx * s, py), 2)
            pygame.draw.line(cv, c, (px, py), (px, py - sy * s), 2)
        self.fs_rect = fr

        draw_text(cv, f"t: {fmt_time(now - ui.start_time)}", ui.F["stat"], MUTED,
                  W - PAD, HDR_H // 2, "midright")
        if ui.game.infinite_mode:
            draw_text(cv, "★ INFINITO", ui.F["xs"], GOLD,
                      W - PAD, HDR_H - 8, "midright")


def draw_status_bar(ui, cv):
    pygame.draw.rect(cv, PANEL, pygame.Rect(0, H - STS_H, W, STS_H))
    pygame.draw.line(cv, BORDER, (0, H - STS_H), (W, H - STS_H), 1)
    draw_text(cv, "ESPACIO: clic  |  P: prestige  |  L: logros  |  "
                  "F11: pantalla completa  |  ESC: pausa",
              ui.F["sm"], MUTED, PAD, H - STS_H + 8)
    draw_text(cv, f"récord: {fmt(ui.game.high_score)}", ui.F["xs"], MUTED,
              W - PAD, H - STS_H + 9, "topright")
