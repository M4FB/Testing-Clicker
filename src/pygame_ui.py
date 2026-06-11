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
SPLIT   = 375
HDR_H   = 46
STS_H   = 30
PAD     = 14

# ═══════════════════════════════════════════════════════════════════════════════
# Paleta  (GitHub dark)
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

# ── Rutas a fuentes TTF con soporte Unicode completo ─────────────────────────
_FONT_REG  = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
_FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

def _f(size: int, bold: bool = False) -> pygame.font.Font:
    path = _FONT_BOLD if bold else _FONT_REG
    try:
        return pygame.font.Font(path, size)
    except Exception:
        return pygame.font.SysFont("sans", size, bold=bold)

# ═══════════════════════════════════════════════════════════════════════════════
# Utilidades de dibujo
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
    return f"{h}h {m:02d}m" if h else f"{m:02d}:{sec:02d}"


def lerp_color(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def draw_panel(surf, rect, color=PANEL, border=BORDER, radius=8):
    pygame.draw.rect(surf, color, rect, border_radius=radius)
    # Brillo sutil en el borde superior (efecto de iluminación)
    shine = pygame.Surface((rect.width - 4, 1), pygame.SRCALPHA)
    shine.fill((255, 255, 255, 14))
    surf.blit(shine, (rect.x + 2, rect.y + 2))
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
        # Brillo en el tercio superior de la barra
        shine_h = max(2, fill.height // 3)
        shine   = pygame.Surface((fill.width, shine_h), pygame.SRCALPHA)
        shine.fill((255, 255, 255, 30))
        surf.blit(shine, (fill.x, fill.y + 1))
    pygame.draw.rect(surf, BORDER, rect, 1, border_radius=radius)


# ═══════════════════════════════════════════════════════════════════════════════
# Estrella de fondo (starfield)
# ═══════════════════════════════════════════════════════════════════════════════
class _BGStar:
    def __init__(self, w: int = W, h: int = H, y: float | None = None):
        self._w = w
        self._h = h
        self._spawn(y)

    def _spawn(self, y: float | None = None):
        self.x     = random.randint(0, self._w)
        self.y     = float(y if y is not None else self._h)
        self.speed = random.uniform(0.03, 0.18)
        self.base  = random.randint(22, 95)
        self.size  = random.choice([1, 1, 1, 1, 2])
        self.phase = random.uniform(0, math.tau)
        self.freq  = random.uniform(0.4, 1.8)

    def update(self, dt: float):
        self.y     -= self.speed
        self.phase += self.freq * dt
        if self.y < 0:
            self._spawn()

    def draw(self, surf: pygame.Surface):
        b   = int(self.base * (0.6 + 0.4 * math.sin(self.phase)))
        col = (b, b, min(255, b + 15))
        ix, iy = int(self.x), int(self.y)
        if 0 <= ix < self._w and 0 <= iy < self._h:
            if self.size == 1:
                surf.set_at((ix, iy), col)
            else:
                pygame.draw.circle(surf, col, (ix, iy), self.size)


# ═══════════════════════════════════════════════════════════════════════════════
# Partícula flotante  (+X puntos al hacer clic)
# ═══════════════════════════════════════════════════════════════════════════════
class Particle:
    DURATION = 0.9

    def __init__(self, x: float, y: float, text: str, color=GREEN):
        self.x     = float(x)
        self.y     = float(y)
        self.text  = text
        self.color = color
        self.born  = time.time()
        self.vx    = random.uniform(-0.6, 0.6)
        self.vy    = random.uniform(-2.2, -1.4)

    @property
    def alive(self) -> bool:
        return (time.time() - self.born) < self.DURATION

    @property
    def alpha(self) -> int:
        t = (time.time() - self.born) / self.DURATION
        return int(max(0, 255 * (1 - t ** 1.4)))

    def update(self):
        self.x  += self.vx
        self.y  += self.vy
        self.vy += 0.06


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

        pygame.display.set_caption(f"Clicker Game  [{MODE.upper()}]")
        self.clock = pygame.time.Clock()
        self.music = music

        # ── Fuentes (DejaVu Sans — soporte Unicode completo) ─────────────────
        self.f_title = _f(20, bold=True)
        self.f_big   = _f(32, bold=True)
        self.f_med   = _f(17)
        self.f_sm    = _f(14)
        self.f_btn   = _f(15, bold=True)
        self.f_click = _f(26, bold=True)
        self.f_stat  = _f(16)
        self.f_part  = _f(15, bold=True)

        # ── Estado del juego ─────────────────────────────────────────────────
        self.game       = GameState()
        self.start_time = time.time()
        self.particles: list[Particle] = []

        # ── Starfield ────────────────────────────────────────────────────────
        self.stars = [_BGStar(W, H, random.randint(0, H)) for _ in range(90)]

        # ── Feedback de UI ───────────────────────────────────────────────────
        self.status_msg   = ""
        self.status_color = TXT
        self.status_end   = 0.0

        # ── Animación del botón clic ─────────────────────────────────────────
        self.click_anim     = 0.0
        self.click_anim_end = 0.0

        # ── Minijuego ────────────────────────────────────────────────────────
        self.next_minigame   = time.time() + MINIGAME_COOLDOWN
        self.mini_available  = False
        self.mini_open       = False
        self.mini_answer     = 0
        self.mini_selected   = -1
        self.mini_result_end = 0.0

        # ── Pausa / Victoria ─────────────────────────────────────────────────
        self.paused            = False
        self.victory_dismissed = False
        self._exit_to: str | None = None

        # Botones en el overlay de pausa (rect calculados en _draw_pause_overlay)
        self._pause_resume_rect:  pygame.Rect | None = None
        self._pause_menu_rect:    pygame.Rect | None = None
        self._pause_quit_rect:    pygame.Rect | None = None

        # ── Rects interactivos ────────────────────────────────────────────────
        self._click_rect:     pygame.Rect | None = None
        self._prestige_rect:  pygame.Rect | None = None
        self._mini_rect:      pygame.Rect | None = None
        self._gen_rects:      list[pygame.Rect | None] = [None] * len(GENERATORS)
        self._upg_rects:      list[pygame.Rect | None] = [None] * len(CLICK_UPGRADES)
        self._mini_num_rects: list[pygame.Rect] = []

        self._prev_time = time.time()

    # ─────────────────────────────────────────────────────────────────────────
    # Loop principal
    # ─────────────────────────────────────────────────────────────────────────
    def run(self) -> str:
        while True:
            events = pygame.event.get()
            self._handle_events(events)
            if self._exit_to:
                return self._exit_to
            if not self.paused:
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

            # ── Click para cerrar victoria ────────────────────────────────────
            if self.game.won and not self.victory_dismissed:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.victory_dismissed = True
                continue

            # ── Modal minijuego activo ────────────────────────────────────────
            if self.mini_open:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.mini_open = False
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.mini_selected == -1:
                        for i, rect in enumerate(self._mini_num_rects):
                            if rect.collidepoint(mx, my):
                                self._resolve_minigame(i + 1)
                continue

            # ── Overlay de pausa ─────────────────────────────────────────────
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
                        pygame.quit()
                        sys.exit()
                continue

            # ── Teclado ───────────────────────────────────────────────────────
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.paused = True
                elif event.key == pygame.K_SPACE:
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
        now = time.time()
        dt  = now - self._prev_time
        self._prev_time = now

        self.game.tick()
        self.game.check_victory()

        if not self.mini_available and now >= self.next_minigame:
            self.mini_available = True

        if self.mini_open and self.mini_selected != -1 and now >= self.mini_result_end:
            self.mini_open = False

        for p in self.particles:
            p.update()
        self.particles = [p for p in self.particles if p.alive]

        for s in self.stars:
            s.update(dt)

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
            self._set_status(f"★  Prestige {n} completado!  Multiplicador total: ×{mult:.1f}", GOLD, 4.0)
            self.particles.clear()

    def _open_minigame(self):
        if not self.mini_available:
            return
        self.mini_answer    = random.randint(1, 9)
        self.mini_selected  = -1
        self.mini_open      = True
        self.mini_available = False
        self.next_minigame  = time.time() + MINIGAME_COOLDOWN

    def _resolve_minigame(self, guess: int):
        self.mini_selected   = guess
        self.mini_result_end = time.time() + 1.8
        if guess == self.mini_answer:
            self.game.activate_minigame(multiplier=2.0, duration=30.0)
            self._set_status("¡CORRECTO! Boost ×2 activo durante 30s", PURPLE, 4.0)
        else:
            self._set_status(f"Fallaste (era {self.mini_answer}). Sin recompensa.", RED, 3.0)

    def _set_status(self, msg: str, color=TXT, duration: float = 2.5):
        self.status_msg   = msg
        self.status_color = color
        self.status_end   = time.time() + duration

    # ─────────────────────────────────────────────────────────────────────────
    # Dibujo principal
    # ─────────────────────────────────────────────────────────────────────────
    def _draw(self):
        self.screen.fill(BG)

        # Starfield (se dibuja antes que los paneles)
        for s in self.stars:
            s.draw(self.screen)

        mx, my = pygame.mouse.get_pos()

        self._draw_header()
        self._draw_left(mx, my)
        self._draw_right(mx, my)
        self._draw_divider()
        self._draw_status_bar()
        self._draw_particles()

        if self.mini_open:
            self._draw_minigame_modal(mx, my)

        if self.game.won and not self.victory_dismissed:
            self._draw_victory_overlay()

        if self.paused:
            self._draw_pause_overlay(mx, my)

        pygame.display.flip()

    # ─────────────────────────────────────────────────────────────────────────
    # Cabecera
    # ─────────────────────────────────────────────────────────────────────────
    def _draw_header(self):
        rect = pygame.Rect(0, 0, W, HDR_H)
        pygame.draw.rect(self.screen, PANEL, rect)
        # Línea de brillo superior
        shine = pygame.Surface((W, 1), pygame.SRCALPHA)
        shine.fill((255, 255, 255, 20))
        self.screen.blit(shine, (0, 0))
        pygame.draw.line(self.screen, BORDER, (0, HDR_H), (W, HDR_H), 1)

        tag_color = ORANGE if MODE == "demo" else ACCENT
        draw_text(self.screen, f"[{MODE.upper()}]", self.f_title, tag_color, PAD, HDR_H // 2, "midleft")
        draw_text(self.screen, "CLICKER  GAME", self.f_title, TXT, W // 2, HDR_H // 2, "center")

        elapsed = fmt_time(time.time() - self.start_time)
        draw_text(self.screen, f"t: {elapsed}", self.f_stat, MUTED, W - PAD, HDR_H // 2, "midright")

        if self.game.infinite_mode:
            draw_text(self.screen, "★ MODO INFINITO ★", self.f_sm, GOLD,
                      W // 2 + 130, HDR_H // 2, "midleft")

    # ─────────────────────────────────────────────────────────────────────────
    # Panel izquierdo
    # ─────────────────────────────────────────────────────────────────────────
    def _draw_left(self, mx, my):
        x0, y0 = PAD, HDR_H + PAD
        pw = SPLIT - PAD * 2

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
            ("Puntos",     fmt(g.points),                                           GOLD),
            ("PPS",        fmt(g.pps()) + "/s",                                     ACCENT),
            ("Por clic",   fmt(g.click_value * g.prestige_multiplier * g.minigame_multiplier), TXT),
            ("Acumulado",  fmt(g.total_points),                                     MUTED),
            ("× bonus",    f"×{g.prestige_multiplier:.1f}  ({g.prestige_count}/2 reinicios)", ORANGE),
        ]
        row_h = 22
        box_h = len(rows) * row_h + PAD * 2
        rect  = pygame.Rect(x, y, w, box_h)
        draw_panel(self.screen, rect)

        ry = y + PAD
        for label, value, color in rows:
            draw_text(self.screen, label + ":", self.f_stat, MUTED, x + PAD, ry)
            draw_text(self.screen, value,        self.f_stat, color, x + w - PAD, ry, "topright")
            ry += row_h
        return y + box_h

    def _draw_progress_section(self, x, y, w) -> int:
        g      = self.game
        pct    = g.prestige_progress_pct() / 100.0
        labels = ["PRESTIGE 1", "PRESTIGE 2", "VICTORIA"]
        label  = labels[min(g.prestige_count, 2)]
        color  = ORANGE if g.prestige_count < 2 else GOLD

        draw_text(self.screen, f"→ {label}", self.f_sm, color, x, y)
        bar_rect = pygame.Rect(x, y + 22, w, 12)
        draw_progress_bar(self.screen, bar_rect, pct, fg=color)
        draw_text(self.screen, f"{pct*100:.1f}%", self.f_sm, MUTED, x + w, y + 22, "topright")
        return y + 38

    def _draw_click_button(self, x, y, w, mx, my) -> int:
        btn_h = 84
        rect  = pygame.Rect(x, y, w, btn_h)
        self._click_rect = rect

        hov    = rect.collidepoint(mx, my)
        shrink = int(self.click_anim * 4)
        draw_r = rect.inflate(-shrink * 2, -shrink * 2)

        base_c = (28, 62, 38)
        hov_c  = (42, 88, 52)
        c      = hov_c if hov else base_c
        if self.click_anim > 0:
            c = lerp_color(c, (18, 42, 26), self.click_anim)

        pygame.draw.rect(self.screen, c,     draw_r, border_radius=10)
        pygame.draw.rect(self.screen, GREEN, draw_r, 2, border_radius=10)

        # Glow exterior en hover
        if hov:
            for r in range(4, 0, -1):
                gs = pygame.Surface((draw_r.width + r * 4, draw_r.height + r * 4), pygame.SRCALPHA)
                gs.fill((63, 185, 80, 12))
                self.screen.blit(gs, (draw_r.x - r * 2, draw_r.y - r * 2))

        draw_text(self.screen, "¡ C L I C !", self.f_click, GREEN,
                  draw_r.centerx, draw_r.centery, "center")
        hint = "[ESPACIO]" if not hov else "clic aquí"
        draw_text(self.screen, hint, self.f_sm, MUTED,
                  draw_r.centerx, draw_r.bottom - 14, "center")
        return y + btn_h

    def _draw_prestige_section(self, x, y, w, mx, my) -> int:
        g     = self.game
        btn_h = 40
        if g.can_prestige():
            rect = pygame.Rect(x, y, w, btn_h)
            self._prestige_rect = rect
            hov  = rect.collidepoint(mx, my)
            c    = (78, 52, 8) if not hov else (108, 78, 14)
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
                draw_text(self.screen, f"Faltan {fmt(remaining)} pts → Prestige {n}",
                          self.f_sm, MUTED, x, y + (btn_h - 14) // 2)
            else:
                draw_text(self.screen, "2 reinicios completados",
                          self.f_sm, MUTED, x, y + (btn_h - 14) // 2)
        return y + btn_h

    def _draw_minigame_section(self, x, y, w, mx, my) -> int:
        g   = self.game
        now = time.time()
        btn_h = 40

        if g.minigame_active:
            left  = g.minigame_seconds_left()
            bar_w = int(w * left / 30.0)
            bg_r  = pygame.Rect(x, y, w, btn_h)
            bar_r = pygame.Rect(x, y, bar_w, btn_h)
            pygame.draw.rect(self.screen, (38, 18, 58), bg_r,  border_radius=8)
            pygame.draw.rect(self.screen, (68, 38, 98), bar_r, border_radius=8)
            pygame.draw.rect(self.screen, PURPLE, bg_r, 2, border_radius=8)
            draw_text(self.screen, f"★ BOOST ×2  activo  {left:.0f}s",
                      self.f_btn, PURPLE, bg_r.centerx, bg_r.centery, "center")
            self._mini_rect = None

        elif self.mini_available:
            rect = pygame.Rect(x, y, w, btn_h)
            self._mini_rect = rect
            # Pulso de brillo para llamar la atención
            pulse = 0.5 + 0.5 * math.sin(now * 4.0)
            hov   = rect.collidepoint(mx, my)
            c     = lerp_color((42, 28, 68), (62, 44, 100), pulse if not hov else 1.0)
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
    # Divisor y panel derecho
    # ─────────────────────────────────────────────────────────────────────────
    def _draw_divider(self):
        pygame.draw.line(self.screen, BORDER, (SPLIT, HDR_H), (SPLIT, H - STS_H), 1)

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

        row_h = 68
        btn_w = 130
        btn_h = 30

        for i, gen in enumerate(GENERATORS):
            rect   = pygame.Rect(x, y, w, row_h - 4)
            locked = not self.game.generator_unlocked(gen["id"])

            if locked:
                draw_panel(self.screen, rect, color=(16, 20, 25))
                draw_text(self.screen, "???  bloqueado", self.f_med, MUTED,
                          x + PAD, y + (row_h - 4) // 2 - 9)
                self._gen_rects[i] = None
                y += row_h
                continue

            owned    = self.game.generators[gen["id"]]
            cost     = self.game.generator_cost(gen["id"])
            can_buy  = self.game.can_buy_generator(gen["id"])
            pps_each = gen["pps"] * self.game.prestige_multiplier

            bg_c = (24, 30, 40) if can_buy else PANEL
            draw_panel(self.screen, rect, color=bg_c)

            draw_text(self.screen, gen["name"], self.f_med, TXT, x + PAD, y + 10)
            count_c = ACCENT if owned > 0 else MUTED
            draw_text(self.screen, f"×{owned}", self.f_med, count_c, x + PAD + 130, y + 10)

            pps_each_real = pps_each * BOOST
            pps_tot_real  = pps_each_real * owned
            pps_str = f"+{fmt(pps_tot_real)}/s" if owned > 0 else f"{fmt(pps_each_real)}/s c/u"
            draw_text(self.screen, pps_str, self.f_sm, MUTED, x + PAD, y + 36)

            btn_rect = pygame.Rect(x + w - btn_w - PAD, y + (row_h - 4 - btn_h) // 2, btn_w, btn_h)
            self._gen_rects[i] = btn_rect
            hov  = btn_rect.collidepoint(mx, my)
            bc   = GREEN_D if can_buy else (30, 25, 25)
            bc   = lerp_color(bc, (50, 110, 60), 0.5) if (hov and can_buy) else bc
            pygame.draw.rect(self.screen, bc, btn_rect, border_radius=6)
            bord = GREEN if can_buy else RED
            pygame.draw.rect(self.screen, bord, btn_rect, 1, border_radius=6)
            draw_text(self.screen, fmt(cost), self.f_btn, GREEN if can_buy else RED,
                      btn_rect.centerx, btn_rect.centery, "center")
            y += row_h
        return y

    def _draw_upgrades(self, x, y, w, mx, my) -> int:
        draw_text(self.screen, "MEJORAS DE CLIC", self.f_med, TXT, x, y)
        y += 26

        row_h = 54
        btn_w = 130
        btn_h = 28

        for i, upg in enumerate(CLICK_UPGRADES):
            rect   = pygame.Rect(x, y, w, row_h - 4)
            locked = not self.game.click_upgrade_unlocked(upg["id"])
            bought = self.game.click_upgrades[upg["id"]]

            if locked:
                draw_panel(self.screen, rect, color=(16, 20, 25))
                draw_text(self.screen, "??? [bloqueado]", self.f_sm, MUTED,
                          x + PAD, y + (row_h - 4) // 2 - 7)
                self._upg_rects[i] = None
                y += row_h
                continue

            bg_c = (24, 30, 40) if (not bought and self.game.points >= self.game.click_upgrade_cost(upg["id"])) else PANEL
            draw_panel(self.screen, rect, color=bg_c)

            draw_text(self.screen, upg["name"], self.f_med, TXT, x + PAD, y + 10)
            draw_text(self.screen, f"+{upg['bonus'] * 100}/clic", self.f_sm, MUTED, x + PAD, y + 32)

            if bought:
                draw_text(self.screen, "✓ COMPRADO", self.f_btn, GREEN,
                          x + w - btn_w - PAD + 15, y + (row_h - 4) // 2 - 9)
                self._upg_rects[i] = None
            else:
                cost    = self.game.click_upgrade_cost(upg["id"])
                can_buy = self.game.points >= cost
                btn_r   = pygame.Rect(x + w - btn_w - PAD, y + (row_h - 4 - btn_h) // 2, btn_w, btn_h)
                self._upg_rects[i] = btn_r
                hov  = btn_r.collidepoint(mx, my)
                bc   = GREEN_D if can_buy else (30, 25, 25)
                bc   = lerp_color(bc, (50, 110, 60), 0.5) if (hov and can_buy) else bc
                pygame.draw.rect(self.screen, bc,  btn_r, border_radius=6)
                bord = GREEN if can_buy else RED
                pygame.draw.rect(self.screen, bord, btn_r, 1, border_radius=6)
                draw_text(self.screen, fmt(cost), self.f_btn, GREEN if can_buy else RED,
                          btn_r.centerx, btn_r.centery, "center")
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
                      self.status_color, PAD, H - STS_H + 8)
        else:
            draw_text(self.screen, "ESPACIO: clic  |  clic en generadores/mejoras para comprar  |  ESC: pausa",
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
        overlay = pygame.Surface((W, H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        self.screen.blit(overlay, (0, 0))

        mw, mh = 480, 300
        mx0    = (W - mw) // 2
        my0    = (H - mh) // 2
        modal  = pygame.Rect(mx0, my0, mw, mh)

        draw_panel(self.screen, modal, color=(26, 18, 48), border=PURPLE, radius=12)
        pygame.draw.rect(self.screen, PURPLE, modal, 2, border_radius=12)

        draw_text(self.screen, "M I N I J U E G O", self.f_title, PURPLE,
                  mx0 + mw // 2, my0 + 22, "center")
        draw_text(self.screen, "Adivina el número del  1  al  9", self.f_med, TXT,
                  mx0 + mw // 2, my0 + 55, "center")

        num_w, num_h = 44, 44
        gap     = 10
        total_w = 9 * num_w + 8 * gap
        start_x = mx0 + (mw - total_w) // 2
        btn_y   = my0 + 105

        self._mini_num_rects = []
        result_shown = self.mini_selected != -1

        for i in range(9):
            bx    = start_x + i * (num_w + gap)
            brect = pygame.Rect(bx, btn_y, num_w, num_h)
            self._mini_num_rects.append(brect)

            n = i + 1
            if result_shown:
                if n == self.mini_answer:
                    bc, tc = (28, 88, 38), GREEN
                elif n == self.mini_selected:
                    bc, tc = RED_D, RED
                else:
                    bc, tc = BTN_D, MUTED
            else:
                hov = brect.collidepoint(mx, my)
                bc  = (55, 38, 88) if hov else (36, 26, 62)
                tc  = TXT

            pygame.draw.rect(self.screen, bc, brect, border_radius=6)
            pygame.draw.rect(self.screen, PURPLE if not result_shown else tc, brect, 1, border_radius=6)
            draw_text(self.screen, str(n), self.f_click, tc, bx + num_w // 2, btn_y + num_h // 2, "center")

        if result_shown:
            if self.mini_selected == self.mini_answer:
                draw_text(self.screen, "¡CORRECTO!  Boost ×2 activo 30s", self.f_med, GREEN,
                          mx0 + mw // 2, my0 + 205, "center")
            else:
                draw_text(self.screen, f"Fallaste.  Era el  {self.mini_answer}", self.f_med, RED,
                          mx0 + mw // 2, my0 + 205, "center")
        else:
            draw_text(self.screen, "ESC para cancelar", self.f_sm, MUTED,
                      mx0 + mw // 2, my0 + 270, "center")

    # ─────────────────────────────────────────────────────────────────────────
    # Overlay de victoria  (se cierra al hacer clic)
    # ─────────────────────────────────────────────────────────────────────────
    def _draw_victory_overlay(self):
        overlay = pygame.Surface((W, H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 210))
        self.screen.blit(overlay, (0, 0))

        vw, vh = 500, 320
        vx = (W - vw) // 2
        vy = (H - vh) // 2
        vr = pygame.Rect(vx, vy, vw, vh)

        draw_panel(self.screen, vr, color=(18, 28, 18), border=GOLD, radius=14)
        pygame.draw.rect(self.screen, GOLD, vr, 2, border_radius=14)

        # Pulso de título
        pulse = 0.5 + 0.5 * math.sin(time.time() * 2.0)
        title_c = lerp_color(GOLD, (255, 220, 80), pulse * 0.5)
        draw_text(self.screen, "¡  V I C T O R I A  !", self.f_big, title_c,
                  vx + vw // 2, vy + 30, "center")
        pygame.draw.line(self.screen, GOLD, (vx + 40, vy + 70), (vx + vw - 40, vy + 70), 1)

        lines = [
            ("Tiempo",       fmt_time(time.time() - self.start_time), TXT),
            ("Puntuación",   fmt(self.game.high_score),               GOLD),
            ("Reinicios",    f"{self.game.prestige_count} / 2",       ORANGE),
            ("Multiplicador", f"×{self.game.prestige_multiplier:.1f}", ACCENT),
        ]
        for j, (label, val, c) in enumerate(lines):
            ry = vy + 90 + j * 38
            draw_text(self.screen, label + ":", self.f_med, MUTED, vx + 60, ry)
            draw_text(self.screen, val,          self.f_med, c,    vx + vw - 60, ry, "topright")

        draw_text(self.screen, "★  MODO INFINITO DESBLOQUEADO  ★", self.f_btn, GREEN,
                  vx + vw // 2, vy + 250, "center")
        # Parpadeo del hint
        hint_alpha = int(128 + 127 * math.sin(time.time() * 3.0))
        hint_s = self.f_sm.render("Haz clic para continuar", True, MUTED)
        hint_s.set_alpha(hint_alpha)
        self.screen.blit(hint_s, hint_s.get_rect(center=(vx + vw // 2, vy + 286)))

    # ─────────────────────────────────────────────────────────────────────────
    # Overlay de pausa
    # ─────────────────────────────────────────────────────────────────────────
    def _draw_pause_overlay(self, mx: int, my: int):
        overlay = pygame.Surface((W, H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 175))
        self.screen.blit(overlay, (0, 0))

        pw, ph = 360, 280
        px = (W - pw) // 2
        py = (H - ph) // 2
        panel = pygame.Rect(px, py, pw, ph)

        draw_panel(self.screen, panel, color=(20, 24, 32), border=BORDER, radius=12)
        pygame.draw.rect(self.screen, BORDER, panel, 2, border_radius=12)

        cx = px + pw // 2
        draw_text(self.screen, "PAUSA", self.f_big, TXT, cx, py + 24, "center")
        pygame.draw.line(self.screen, BORDER, (px + 30, py + 62), (px + pw - 30, py + 62), 1)

        # Volumen
        vol = self.music.get_volume() if self.music else 0.0
        bar_total = 160
        bar_filled = int(bar_total * vol)
        bx = cx - bar_total // 2
        draw_text(self.screen, "Vol:", self.f_sm, MUTED, bx - 36, py + 80)
        vol_bg = pygame.Rect(bx, py + 80, bar_total, 12)
        pygame.draw.rect(self.screen, PANEL2, vol_bg, border_radius=4)
        if bar_filled > 0:
            vol_fill = pygame.Rect(bx, py + 80, bar_filled, 12)
            pygame.draw.rect(self.screen, ACCENT, vol_fill, border_radius=4)
        pygame.draw.rect(self.screen, BORDER, vol_bg, 1, border_radius=4)
        draw_text(self.screen, f"{int(vol*100)}%", self.f_sm, MUTED,
                  bx + bar_total + 8, py + 80)
        draw_text(self.screen, "← → para ajustar", self.f_sm, MUTED, cx, py + 100, "center")

        # Botones de pausa
        btn_w, btn_h = 240, 44
        gap = 10
        y0  = py + 130

        rects = {}
        for label, key in [("CONTINUAR", "resume"), ("MENU PRINCIPAL", "menu"), ("SALIR DEL JUEGO", "quit")]:
            r   = pygame.Rect(cx - btn_w // 2, y0, btn_w, btn_h)
            hov = r.collidepoint(mx, my)
            bc  = lerp_color((28, 34, 42), ACCENT, 0.12) if hov else (26, 32, 40)
            bord = ACCENT if hov else BORDER
            pygame.draw.rect(self.screen, bc,   r, border_radius=8)
            pygame.draw.rect(self.screen, bord, r, 2, border_radius=8)
            tc  = (230, 240, 255) if hov else TXT
            draw_text(self.screen, label, self.f_btn, tc, r.centerx, r.centery, "center")
            rects[key] = r
            y0 += btn_h + gap

        self._pause_resume_rect = rects.get("resume")
        self._pause_menu_rect   = rects.get("menu")
        self._pause_quit_rect   = rects.get("quit")


# ═══════════════════════════════════════════════════════════════════════════════
# Punto de entrada (standalone — sin menú)
# ═══════════════════════════════════════════════════════════════════════════════
def main():
    pygame.init()
    ui = GameUI()
    ui.run()
