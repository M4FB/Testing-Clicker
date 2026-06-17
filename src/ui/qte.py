"""QTE: estado y panel de dibujo."""
import math
import time
from dataclasses import dataclass, field

import pygame

from src.fx import (
    BORDER, MUTED, GREEN, RED, ORANGE,
    lerp_color, draw_text, striped_bar,
)
from src.ui.common import W, HDR_H

QTE_KEY_SET = set("ASDFGHJKLZXCVBN")


@dataclass
class QTE:
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


def draw_qte_panel(ui, cv):
    qte = ui.qte
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
        draw_text(cv, "✗ QTE FALLADO", ui.F["btn"], RED,
                  qx + qw // 2, qy + qh // 2, "center")
        return

    draw_text(cv, "¡ QTE !  ×3 por 60s", ui.F["xs"], ORANGE, qx + 12, qy + 7)

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
        draw_text(cv, k, ui.F["xs"], c_txt, krect.centerx, krect.centery, "center")

    frac = qte.time_left / qte.duration
    striped_bar(cv, pygame.Rect(qx + 12, qy + qh - 16, qw - 24, 8),
                frac, lerp_color(RED, GREEN, frac), now=now, radius=3)
