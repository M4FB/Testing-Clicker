"""Eventos aleatorios: la moneda dorada.

Cada GOLDEN_MIN..GOLDEN_MAX segundos (modulado por la mejora de prestigio
"Imán Dorado") cruza la pantalla una moneda dorada clicable. Atraparla da
un bono aleatorio que aplica la UI:

    "rafaga" → puntos instantáneos (lo mayor entre 60s de PPS y 75 clics)
    "fiebre" → fiebre dorada ×7 durante 15s
    "mini"   → un minijuego disponible al instante
"""
import math
import random
import time

import pygame

from src.config import GOLDEN_MIN, GOLDEN_MAX
from src.fx import GOLD, GOLD_D, Trail, draw_coin, scale_color


OUTCOMES = ["rafaga", "fiebre", "mini"]


def roll_outcome() -> str:
    return random.choice(OUTCOMES)


class GoldenCoin:
    R = 17          # radio visual; el clic acepta un margen extra

    def __init__(self, w, h):
        self.w = w
        side       = random.choice([1, -1])
        self.x     = -36.0 if side == 1 else w + 36.0
        self.vx    = side * random.uniform(105, 165)
        self.base_y = random.uniform(h * 0.22, h * 0.72)
        self.amp   = random.uniform(22, 58)
        self.freq  = random.uniform(1.1, 2.0)
        self.born  = time.time()
        self.y     = self.base_y
        self.trail = Trail(GOLD, life=0.55, max_r=5.0)

    @property
    def alive(self) -> bool:
        return -40 <= self.x <= self.w + 40

    def update(self, dt):
        self.x += self.vx * dt
        t = time.time() - self.born
        self.y = self.base_y + math.sin(t * self.freq * math.tau / 2) * self.amp
        self.trail.add(self.x, self.y)
        self.trail.update(dt)

    def hit(self, mx, my) -> bool:
        return (mx - self.x) ** 2 + (my - self.y) ** 2 <= (self.R + 11) ** 2

    def draw(self, surf):
        now = time.time()
        self.trail.draw(surf)
        # Halo pulsante
        pulse = 0.5 + 0.5 * math.sin(now * 6)
        glow  = pygame.Surface((self.R * 5, self.R * 5), pygame.SRCALPHA)
        for rad, a in ((self.R * 2.4, 18), (self.R * 1.8, 30), (self.R * 1.3, 46)):
            pygame.draw.circle(glow, (*GOLD, int(a * (0.6 + 0.4 * pulse))),
                               (self.R * 5 // 2, self.R * 5 // 2), int(rad))
        surf.blit(glow, (int(self.x) - self.R * 5 // 2,
                         int(self.y) - self.R * 5 // 2))
        draw_coin(surf, self.x, self.y, self.R, now, speed=2.6)
        # Destello en cruz
        s = 3 + int(3 * pulse)
        cx, cy = int(self.x) - self.R, int(self.y) - self.R // 2
        col = scale_color((255, 245, 200), 0.6 + 0.4 * pulse)
        pygame.draw.line(surf, col, (cx - s, cy), (cx + s, cy), 1)
        pygame.draw.line(surf, col, (cx, cy - s), (cx, cy + s), 1)


class GoldenEvents:
    """Programa y gestiona la moneda dorada activa (máx. una a la vez)."""

    def __init__(self, w, h):
        self.w, self.h = w, h
        self.coin: GoldenCoin | None = None
        self._next = time.time() + random.uniform(GOLDEN_MIN, GOLDEN_MAX)

    def schedule_next(self, freq_factor: float = 1.0):
        self._next = time.time() + random.uniform(GOLDEN_MIN, GOLDEN_MAX) * freq_factor

    def update(self, now, dt, freq_factor: float = 1.0, blocked: bool = False):
        if self.coin:
            self.coin.update(dt)
            if not self.coin.alive:
                self.coin = None
                self.schedule_next(freq_factor)
        elif now >= self._next and not blocked:
            self.coin = GoldenCoin(self.w, self.h)

    def try_click(self, mx, my) -> bool:
        """True si el clic atrapó la moneda (y la consume)."""
        if self.coin and self.coin.hit(mx, my):
            self.coin = None
            return True
        return False

    def draw(self, surf):
        if self.coin:
            self.coin.draw(surf)
