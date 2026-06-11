"""Minijuegos de la versión pre-release.

Cuatro minijuegos con habilidad real y recompensa proporcional al desempeño:

  - TargetRush  (Fiebre Dorada):  caza monedas que aparecen y encogen, evita bombas.
  - GoldRain    (Lluvia Dorada):  atrapa monedas/gemas con una cesta, esquiva bombas.
  - SimonPlus   (Simón Dice+):    secuencias progresivas (3→4→5), premio parcial.
  - PulseBar    (Pulso Perfecto): detén el marcador en la zona dorada, 3 rondas.

Interfaz común (la usa GameUI):
    mg = Clase(rect_modal, fx)
    mg.event(e, mx, my) / mg.update(now, dt) / mg.draw(surf, F, mx, my)
    mg.finished → True al resolver;  mg.reward → (mult, dur) | None
    mg.close_at → momento en que el modal debe cerrarse
"""
import math
import random
import time

import pygame

from src.fx import (
    BG, PANEL, PANEL2, BORDER, TXT, MUTED, ACCENT, GOLD, GOLD_D,
    GREEN, RED, ORANGE, PURPLE,
    clamp, lerp, lerp_color, scale_color, ease_out, draw_text, striped_bar,
)


# ═══════════════════════════════════════════════════════════════════════════════
# Base
# ═══════════════════════════════════════════════════════════════════════════════
class MinigameBase:
    TITLE    = ""
    HINT     = ""
    COLOR    = PURPLE
    MODAL    = (560, 440)
    DURATION = 10.0

    def __init__(self, rect: pygame.Rect, fx):
        self.rect = rect
        self.fx   = fx
        self.start    = time.time()
        self.finished = False
        self.reward   = None        # (mult, dur) | None
        self.result_msg   = ""
        self.result_color = TXT
        self.close_at     = 0.0

    # ── resolución ──────────────────────────────────────────────────────────
    def finish(self, reward, msg, color):
        if self.finished:
            return
        self.finished     = True
        self.reward       = reward
        self.result_msg   = msg
        self.result_color = color
        self.close_at     = time.time() + 1.9

    # ── API que sobreescribe cada juego ─────────────────────────────────────
    def event(self, e, mx, my): ...
    def update(self, now, dt): ...
    def draw(self, surf, F, mx, my): ...

    # ── helpers de dibujo comunes ────────────────────────────────────────────
    def draw_frame(self, surf, F):
        r = self.rect
        pygame.draw.rect(surf, (16, 20, 34), r, border_radius=14)
        sh = pygame.Surface((r.width - 8, r.height // 3), pygame.SRCALPHA)
        sh.fill((255, 255, 255, 9))
        surf.blit(sh, (r.x + 4, r.y + 3))
        pygame.draw.rect(surf, self.COLOR, r, 2, border_radius=14)
        draw_text(surf, self.TITLE, F["title"], self.COLOR,
                  r.centerx, r.y + 22, "center")
        if self.HINT and not self.finished:
            draw_text(surf, self.HINT, F["xs"], MUTED,
                      r.centerx, r.y + 44, "center")

    def draw_timer(self, surf, now):
        frac = clamp(1.0 - (now - self.start) / self.DURATION, 0.0, 1.0)
        bar  = pygame.Rect(self.rect.x + 24, self.rect.y + 58,
                           self.rect.width - 48, 9)
        fg = lerp_color(RED, GREEN, frac)
        striped_bar(surf, bar, frac, fg, now=now, radius=4)

    def draw_result(self, surf, F):
        if not self.finished:
            return
        r  = self.rect
        bw = r.width - 70
        box = pygame.Rect(r.centerx - bw // 2, r.centery - 34, bw, 68)
        bs  = pygame.Surface(box.size, pygame.SRCALPHA)
        pygame.draw.rect(bs, (12, 16, 28, 235), bs.get_rect(), border_radius=10)
        surf.blit(bs, box.topleft)
        pygame.draw.rect(surf, self.result_color, box, 2, border_radius=10)
        draw_text(surf, self.result_msg, F["md"], self.result_color,
                  box.centerx, box.centery, "center")

    def draw_esc_hint(self, surf, F):
        if not self.finished:
            draw_text(surf, "ESC para cancelar", F["xs"], MUTED,
                      self.rect.centerx, self.rect.bottom - 16, "center")


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Fiebre Dorada (whack-a-coin)
# ═══════════════════════════════════════════════════════════════════════════════
class TargetRush(MinigameBase):
    TITLE    = "FIEBRE  DORADA"
    HINT     = "Clic en las monedas — ¡evita las bombas!"
    COLOR    = GOLD
    MODAL    = (580, 440)
    DURATION = 10.0

    def __init__(self, rect, fx):
        super().__init__(rect, fx)
        self.area = pygame.Rect(rect.x + 22, rect.y + 86,
                                rect.width - 44, rect.height - 130)
        self.targets: list[dict] = []
        self.next_spawn = self.start + 0.45
        self.score = 0

    def _radius(self, tg, now):
        age  = now - tg["born"]
        grow = ease_out(min(1.0, age / 0.15))
        t    = clamp(age / tg["life"], 0.0, 1.0)
        return max(7, int(tg["r0"] * grow * (1.0 - 0.55 * t)))

    def event(self, e, mx, my):
        if self.finished:
            return
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            now = time.time()
            for tg in reversed(self.targets):
                r = self._radius(tg, now)
                if (mx - tg["x"]) ** 2 + (my - tg["y"]) ** 2 <= r * r:
                    self.targets.remove(tg)
                    if tg["kind"] == "gold":
                        self.score += 1
                        self.fx.sparks_burst(mx, my, GOLD, 10, 190)
                        self.fx.float_text(mx, my - 14, "+1", GOLD)
                    else:
                        self.score = max(0, self.score - 2)
                        self.fx.sparks_burst(mx, my, RED, 16, 260)
                        self.fx.float_text(mx, my - 14, "-2", RED)
                        self.fx.add_shake(0.3)
                    break

    def update(self, now, dt):
        if self.finished:
            return
        prog = clamp((now - self.start) / self.DURATION, 0.0, 1.0)
        if now - self.start >= self.DURATION:
            if self.score >= 3:
                mult = round(min(3.0, 1.2 + 0.18 * self.score), 2)
                self.finish((mult, 30.0),
                            f"¡{self.score} monedas!  Boost ×{mult:.1f} por 30s", GREEN)
            else:
                self.finish(None, f"Solo {self.score} monedas (mínimo 3)…", RED)
            return
        if now >= self.next_spawn:
            margin = 36
            kind   = "bomb" if random.random() < 0.22 else "gold"
            self.targets.append({
                "x": random.randint(self.area.x + margin, self.area.right - margin),
                "y": random.randint(self.area.y + margin, self.area.bottom - margin),
                "r0": random.randint(24, 33),
                "born": now,
                "life": lerp(1.5, 1.0, prog),
                "kind": kind,
            })
            self.next_spawn = now + lerp(0.7, 0.38, prog) * random.uniform(0.8, 1.2)
        self.targets = [t for t in self.targets if now - t["born"] < t["life"]]

    def draw(self, surf, F, mx, my):
        now = time.time()
        self.draw_frame(surf, F)
        self.draw_timer(surf, now)
        pygame.draw.rect(surf, (28, 34, 50), self.area, 1, border_radius=10)
        draw_text(surf, f"Monedas: {self.score}", F["btn"], GOLD,
                  self.rect.right - 26, self.rect.y + 22, "midright")

        for tg in self.targets:
            r = self._radius(tg, now)
            x, y = tg["x"], tg["y"]
            if tg["kind"] == "gold":
                pygame.draw.circle(surf, GOLD_D, (x, y), r)
                pygame.draw.circle(surf, GOLD, (x, y), max(2, r - 4))
                pygame.draw.circle(surf, (255, 235, 150), (x - r // 4, y - r // 4),
                                   max(1, r // 4))
                if r > 14:
                    draw_text(surf, "$", F["sm"], GOLD_D, x, y, "center")
            else:
                pygame.draw.circle(surf, (30, 30, 40), (x, y), r)
                pygame.draw.circle(surf, (60, 56, 70), (x, y), max(2, r - 4))
                spark = 0.5 + 0.5 * math.sin(now * 12 + tg["born"])
                pygame.draw.circle(surf, lerp_color(ORANGE, RED, spark),
                                   (x + r // 2, y - r // 2), 3)
                if r > 14:
                    draw_text(surf, "✖", F["sm"], RED, x, y, "center")

        self.draw_result(surf, F)
        self.draw_esc_hint(surf, F)


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Lluvia Dorada (catch)
# ═══════════════════════════════════════════════════════════════════════════════
class GoldRain(MinigameBase):
    TITLE    = "LLUVIA  DORADA"
    HINT     = "Mueve la cesta — monedas +1, gemas +3, bombas -3"
    COLOR    = ACCENT
    MODAL    = (580, 470)
    DURATION = 12.0
    BASKET_W = 96
    BASKET_H = 16

    def __init__(self, rect, fx):
        super().__init__(rect, fx)
        self.area = pygame.Rect(rect.x + 22, rect.y + 86,
                                rect.width - 44, rect.height - 130)
        self.objs: list[dict] = []
        self.next_spawn = self.start + 0.4
        self.score = 0
        self.bx    = rect.centerx

    def event(self, e, mx, my):
        if e.type == pygame.MOUSEMOTION:
            half = self.BASKET_W // 2
            self.bx = clamp(mx, self.area.x + half, self.area.right - half)

    def update(self, now, dt):
        if self.finished:
            return
        prog = clamp((now - self.start) / self.DURATION, 0.0, 1.0)
        if now - self.start >= self.DURATION:
            if self.score >= 6:
                mult = round(min(3.0, 1.2 + 0.13 * self.score), 2)
                self.finish((mult, 35.0),
                            f"¡{self.score} puntos!  Boost ×{mult:.1f} por 35s", GREEN)
            else:
                self.finish(None, f"Solo {self.score} puntos (mínimo 6)…", RED)
            return

        if now >= self.next_spawn:
            roll = random.random()
            kind = "gem" if roll < 0.10 else ("bomb" if roll < 0.32 else "coin")
            self.objs.append({
                "x": random.randint(self.area.x + 16, self.area.right - 16),
                "y": float(self.area.y + 6),
                "vy": lerp(150, 290, prog) * random.uniform(0.85, 1.2),
                "kind": kind,
                "ph": random.uniform(0, math.tau),
            })
            self.next_spawn = now + lerp(0.5, 0.28, prog) * random.uniform(0.8, 1.2)

        basket_y = self.area.bottom - 22
        half     = self.BASKET_W // 2
        for o in list(self.objs):
            o["y"] += o["vy"] * dt
            if basket_y - 8 <= o["y"] <= basket_y + 12 and abs(o["x"] - self.bx) <= half + 8:
                self.objs.remove(o)
                if o["kind"] == "coin":
                    self.score += 1
                    self.fx.sparks_burst(o["x"], basket_y, GOLD, 8, 160)
                    self.fx.float_text(o["x"], basket_y - 18, "+1", GOLD)
                elif o["kind"] == "gem":
                    self.score += 3
                    self.fx.sparks_burst(o["x"], basket_y, (120, 230, 255), 14, 220)
                    self.fx.float_text(o["x"], basket_y - 18, "+3", (120, 230, 255))
                else:
                    self.score = max(0, self.score - 3)
                    self.fx.sparks_burst(o["x"], basket_y, RED, 16, 260)
                    self.fx.float_text(o["x"], basket_y - 18, "-3", RED)
                    self.fx.add_shake(0.3)
            elif o["y"] > self.area.bottom + 14:
                self.objs.remove(o)

    def draw(self, surf, F, mx, my):
        now = time.time()
        half = self.BASKET_W // 2
        self.bx = clamp(mx, self.area.x + half, self.area.right - half)

        self.draw_frame(surf, F)
        self.draw_timer(surf, now)
        pygame.draw.rect(surf, (28, 34, 50), self.area, 1, border_radius=10)
        draw_text(surf, f"Puntos: {self.score}", F["btn"], ACCENT,
                  self.rect.right - 26, self.rect.y + 22, "midright")

        clip = surf.get_clip()
        surf.set_clip(self.area)
        for o in self.objs:
            x, y = int(o["x"]), int(o["y"])
            if o["kind"] == "coin":
                pygame.draw.circle(surf, GOLD_D, (x, y), 11)
                pygame.draw.circle(surf, GOLD, (x, y), 8)
                pygame.draw.circle(surf, (255, 235, 150), (x - 3, y - 3), 2)
            elif o["kind"] == "gem":
                shimmer = 0.5 + 0.5 * math.sin(now * 6 + o["ph"])
                c = lerp_color((80, 190, 230), (160, 245, 255), shimmer)
                pts = [(x, y - 12), (x + 10, y), (x, y + 12), (x - 10, y)]
                pygame.draw.polygon(surf, c, pts)
                pygame.draw.polygon(surf, (220, 250, 255), pts, 1)
            else:
                pygame.draw.circle(surf, (30, 30, 40), (x, y), 11)
                pygame.draw.circle(surf, (60, 56, 70), (x, y), 8)
                spark = 0.5 + 0.5 * math.sin(now * 12 + o["ph"])
                pygame.draw.circle(surf, lerp_color(ORANGE, RED, spark), (x + 6, y - 8), 3)
        surf.set_clip(clip)

        # Cesta
        basket_y = self.area.bottom - 22
        br = pygame.Rect(int(self.bx - half), basket_y, self.BASKET_W, self.BASKET_H)
        pygame.draw.rect(surf, (140, 96, 30), br, border_radius=5)
        pygame.draw.rect(surf, GOLD_D, br, 2, border_radius=5)
        pygame.draw.line(surf, GOLD_D, (br.x + 6, br.y + 5), (br.right - 6, br.y + 5), 1)
        pygame.draw.line(surf, GOLD_D, (br.x + 6, br.y + 10), (br.right - 6, br.y + 10), 1)

        self.draw_result(surf, F)
        self.draw_esc_hint(surf, F)


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Simón Dice+ (secuencias progresivas)
# ═══════════════════════════════════════════════════════════════════════════════
class SimonPlus(MinigameBase):
    TITLE   = "SIMÓN  DICE +"
    HINT    = "Memoriza y repite — 3 rondas, cada una más larga"
    COLOR   = PURPLE
    MODAL   = (540, 470)
    LENGTHS = [3, 4, 5]
    COLORS  = [RED, GREEN, ACCENT, GOLD]
    DIM     = [(92, 30, 28), (22, 66, 30), (28, 56, 96), (98, 76, 18)]
    NAMES   = ["ROJO", "VERDE", "AZUL", "ORO"]

    STEP    = 0.55   # cadencia de la fase "mostrar"
    LIT     = 0.36   # tiempo encendida cada caja

    def __init__(self, rect, fx):
        super().__init__(rect, fx)
        self.round  = 0
        self.phase  = "show"        # "show" | "input" | "gap"
        self.inputs: list[int] = []
        self.flash_box   = -1
        self.flash_until = 0.0
        self.gap_until   = 0.0
        self._start_round(time.time())

    def _start_round(self, now):
        self.seq = [random.randrange(4) for _ in range(self.LENGTHS[self.round])]
        self.phase      = "show"
        self.inputs     = []
        self.show_start = now + 0.7

    def _show_index(self, now):
        """Índice de la secuencia iluminado ahora (o -1)."""
        if now < self.show_start:
            return -1, False
        i = int((now - self.show_start) / self.STEP)
        if i >= len(self.seq):
            return -1, True          # terminó de mostrar
        lit = ((now - self.show_start) % self.STEP) < self.LIT
        return (i if lit else -1), False

    def _fail(self, now):
        r = self.round
        if r > 0:
            mult = round(1.4 + 0.4 * r, 2)
            self.finish((mult, 30.0 + 5 * r),
                        f"{r} ronda(s) — Boost ×{mult:.1f}", ORANGE)
        else:
            self.finish(None, "Secuencia incorrecta…", RED)

    def event(self, e, mx, my):
        if self.finished or self.phase != "input":
            return
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            now = time.time()
            for ci, br in enumerate(self._boxes()):
                if br.collidepoint(mx, my):
                    self.flash_box, self.flash_until = ci, now + 0.22
                    if ci == self.seq[len(self.inputs)]:
                        self.inputs.append(ci)
                        self.fx.sparks_burst(br.centerx, br.centery,
                                             self.COLORS[ci], 8, 150)
                        if len(self.inputs) == len(self.seq):
                            self.round += 1
                            if self.round >= len(self.LENGTHS):
                                self.finish((3.0, 45.0),
                                            "¡MEMORIA PERFECTA!  Boost ×3.0 por 45s",
                                            GREEN)
                            else:
                                self.phase     = "gap"
                                self.gap_until = now + 0.9
                    else:
                        self._fail(now)
                    break

    def update(self, now, dt):
        if self.finished:
            return
        if self.phase == "show":
            _, done = self._show_index(now)
            if done:
                self.phase = "input"
        elif self.phase == "gap" and now >= self.gap_until:
            self._start_round(now)

    def _boxes(self):
        cw, ch, gap = 116, 86, 14
        gx = self.rect.centerx - (cw * 2 + gap) // 2
        gy = self.rect.y + 116
        return [pygame.Rect(gx + (i % 2) * (cw + gap),
                            gy + (i // 2) * (ch + gap), cw, ch)
                for i in range(4)]

    def draw(self, surf, F, mx, my):
        now = time.time()
        self.draw_frame(surf, F)

        draw_text(surf, f"Ronda {min(self.round + 1, 3)}/3", F["btn"], PURPLE,
                  self.rect.right - 26, self.rect.y + 22, "midright")

        if self.phase == "show":
            idx, _ = self._show_index(now)
            label, lc = "Memoriza la secuencia…", TXT
        elif self.phase == "input":
            idx = -1
            rem = len(self.seq) - len(self.inputs)
            label, lc = f"¡Repite!  {rem} restante(s)", GOLD
        else:
            idx = -1
            label, lc = "¡Bien!  Siguiente ronda…", GREEN
        if not self.finished:
            draw_text(surf, label, F["sm"], lc, self.rect.centerx,
                      self.rect.y + 78, "center")

        lit_color = self.seq[idx] if (self.phase == "show" and idx >= 0) else -1
        for ci, br in enumerate(self._boxes()):
            highlight = (ci == lit_color)
            if self.phase == "input" and not self.finished:
                if ci == self.flash_box and now < self.flash_until:
                    highlight = True
                elif br.collidepoint(mx, my):
                    highlight = True
            c = self.COLORS[ci] if highlight else self.DIM[ci]
            pygame.draw.rect(surf, c, br, border_radius=10)
            if highlight:
                gs = pygame.Surface((br.width + 16, br.height + 16), pygame.SRCALPHA)
                pygame.draw.rect(gs, (*self.COLORS[ci], 60), gs.get_rect(),
                                 4, border_radius=14)
                surf.blit(gs, (br.x - 8, br.y - 8))
            pygame.draw.rect(surf, self.COLORS[ci], br, 2, border_radius=10)
            draw_text(surf, self.NAMES[ci], F["xs"], (230, 230, 235),
                      br.centerx, br.centery, "center")

        # Puntos de progreso de la ronda actual
        if not self.finished:
            n  = len(self.seq)
            dx = self.rect.centerx - (n * 22 - 8) // 2
            dy = self.rect.bottom - 56
            for pi in range(n):
                filled = pi < len(self.inputs)
                col = self.COLORS[self.seq[pi]] if (filled or self.phase == "show") \
                      else PANEL2
                if self.phase == "show" and not filled:
                    col = PANEL2
                pygame.draw.circle(surf, col if filled else PANEL2,
                                   (dx + pi * 22 + 7, dy + 7), 7)
                pygame.draw.circle(surf, BORDER, (dx + pi * 22 + 7, dy + 7), 7, 1)

        self.draw_result(surf, F)
        self.draw_esc_hint(surf, F)


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Pulso Perfecto (timing)
# ═══════════════════════════════════════════════════════════════════════════════
class PulseBar(MinigameBase):
    TITLE  = "PULSO  PERFECTO"
    HINT   = "CLIC o ESPACIO cuando el marcador pase por el centro"
    COLOR  = ORANGE
    MODAL  = (580, 400)
    ROUNDS = 3
    SPEEDS = [0.55, 0.8, 1.1]            # ciclos por segundo
    ZONES  = [(0.11, 0.045), (0.09, 0.038), (0.07, 0.03)]   # (buena, perfecta)
    ROUND_TIMEOUT = 6.0

    def __init__(self, rect, fx):
        super().__init__(rect, fx)
        self.round       = 0
        self.bonus       = 0.0
        self.state       = "run"        # "run" | "hit"
        self.round_start = self.start + 0.5
        self.wait_until  = 0.0
        self.hits: list[tuple[float, float]] = []   # (pos, gain)
        self.hit_msg     = ""
        self.hit_color   = TXT

    def _pos(self, now):
        t = max(0.0, now - self.round_start) * self.SPEEDS[self.round]
        return 1.0 - abs(1.0 - (t * 2.0) % 2.0)

    def _bar_rect(self):
        return pygame.Rect(self.rect.x + 50, self.rect.centery - 4,
                           self.rect.width - 100, 26)

    def _register(self, now, pos, gain):
        self.hits.append((pos, gain))
        self.bonus += gain
        self.state      = "hit"
        self.wait_until = now + 0.85
        bar = self._bar_rect()
        mxp = bar.x + int(bar.width * pos)
        if gain >= 0.6:
            self.hit_msg, self.hit_color = "¡PERFECTO!  +0.6", GOLD
            self.fx.sparks_burst(mxp, bar.centery, GOLD, 18, 260)
        elif gain > 0:
            self.hit_msg, self.hit_color = "¡Bien!  +0.3", GREEN
            self.fx.sparks_burst(mxp, bar.centery, GREEN, 10, 180)
        else:
            self.hit_msg, self.hit_color = "Fuera de zona", RED

    def _resolve(self):
        if self.bonus > 0:
            mult = round(min(3.0, 1.4 + self.bonus), 2)
            self.finish((mult, 40.0), f"Precisión total — Boost ×{mult:.1f} por 40s",
                        GREEN if self.bonus >= 1.2 else ORANGE)
        else:
            self.finish(None, "Ningún acierto…", RED)

    def event(self, e, mx, my):
        if self.finished or self.state != "run":
            return
        now = time.time()
        if now < self.round_start:
            return
        fired = (e.type == pygame.MOUSEBUTTONDOWN and e.button == 1) or \
                (e.type == pygame.KEYDOWN and e.key == pygame.K_SPACE)
        if fired:
            pos  = self._pos(now)
            d    = abs(pos - 0.5)
            good, perf = self.ZONES[self.round]
            gain = 0.6 if d <= perf else (0.3 if d <= good else 0.0)
            self._register(now, pos, gain)

    def update(self, now, dt):
        if self.finished:
            return
        if self.state == "run" and now - self.round_start > self.ROUND_TIMEOUT:
            self._register(now, self._pos(now), 0.0)
            self.hit_msg = "¡Tiempo agotado!"
        if self.state == "hit" and now >= self.wait_until:
            self.round += 1
            if self.round >= self.ROUNDS:
                self._resolve()
            else:
                self.state       = "run"
                self.round_start = now + 0.25
                self.hit_msg     = ""

    def draw(self, surf, F, mx, my):
        now = time.time()
        self.draw_frame(surf, F)
        draw_text(surf, f"Ronda {min(self.round + 1, 3)}/3", F["btn"], ORANGE,
                  self.rect.right - 26, self.rect.y + 22, "midright")
        draw_text(surf, f"Bono acumulado: +{self.bonus:.1f}", F["sm"], GOLD,
                  self.rect.centerx, self.rect.y + 80, "center")

        bar = self._bar_rect()
        ri  = min(self.round, self.ROUNDS - 1)
        good, perf = self.ZONES[ri]

        pygame.draw.rect(surf, PANEL2, bar, border_radius=8)
        gz = pygame.Rect(bar.x + int(bar.width * (0.5 - good)), bar.y,
                         max(4, int(bar.width * good * 2)), bar.height)
        pygame.draw.rect(surf, (26, 78, 38), gz, border_radius=6)
        pz = pygame.Rect(bar.x + int(bar.width * (0.5 - perf)), bar.y,
                         max(3, int(bar.width * perf * 2)), bar.height)
        pulse = 0.5 + 0.5 * math.sin(now * 6.0)
        pygame.draw.rect(surf, lerp_color(GOLD_D, GOLD, pulse), pz, border_radius=4)
        pygame.draw.rect(surf, BORDER, bar, 1, border_radius=8)

        # Marcador
        if not self.finished:
            pos = self._pos(now) if self.state == "run" else \
                  (self.hits[-1][0] if self.hits else 0.5)
            mxp = bar.x + int(bar.width * pos)
            mr  = pygame.Rect(mxp - 4, bar.y - 9, 8, bar.height + 18)
            gs  = pygame.Surface((mr.width + 14, mr.height + 14), pygame.SRCALPHA)
            pygame.draw.rect(gs, (*ORANGE, 70), gs.get_rect(), border_radius=8)
            surf.blit(gs, (mr.x - 7, mr.y - 7))
            pygame.draw.rect(surf, (250, 240, 225), mr, border_radius=4)
            pygame.draw.rect(surf, ORANGE, mr, 2, border_radius=4)

        if self.hit_msg and not self.finished:
            draw_text(surf, self.hit_msg, F["md"], self.hit_color,
                      self.rect.centerx, bar.bottom + 40, "center")

        # Resultado de cada ronda (estrellitas)
        for i in range(self.ROUNDS):
            cxp = self.rect.centerx + (i - 1) * 34
            cyp = self.rect.bottom - 58
            if i < len(self.hits):
                g = self.hits[i][1]
                c = GOLD if g >= 0.6 else (GREEN if g > 0 else RED_DOT)
            else:
                c = PANEL2
            pygame.draw.circle(surf, c, (cxp, cyp), 9)
            pygame.draw.circle(surf, BORDER, (cxp, cyp), 9, 1)

        self.draw_result(surf, F)
        self.draw_esc_hint(surf, F)


RED_DOT = (120, 40, 38)

MINIGAMES = [TargetRush, GoldRain, SimonPlus, PulseBar]
