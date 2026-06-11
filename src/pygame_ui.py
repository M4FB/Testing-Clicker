"""Interfaz pygame del Clicker Game."""

import pygame
import sys
import time
import random
import math
from dataclasses import dataclass, field

from src.game import GameState
from src.config import (
    GENERATORS, CLICK_UPGRADES, GEN_UPGRADES,
    MODE, MINIGAME_COOLDOWN, QTE_COOLDOWN, BOOST,
)

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
# Paleta
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
BTN_D   = ( 18,  22,  27)

SEQ_COLORS = [RED, GREEN, ACCENT, GOLD]   # colores para el minijuego de secuencia
SEQ_DIM    = [(100, 30, 28), (22, 65, 30), (30, 58, 100), (80, 58, 12)]

_QTE_KEY_SET = set("ASDFGHJKLZXCVBN")

# ── Fuentes TTF (soporte Unicode) ────────────────────────────────────────────
_FONT_REG  = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
_FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

def _f(size: int, bold: bool = False) -> pygame.font.Font:
    try:
        return pygame.font.Font(_FONT_BOLD if bold else _FONT_REG, size)
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
        sh = pygame.Surface((fill.width, max(2, fill.height // 3)), pygame.SRCALPHA)
        sh.fill((255, 255, 255, 28))
        surf.blit(sh, (fill.x, fill.y + 1))
    pygame.draw.rect(surf, BORDER, rect, 1, border_radius=radius)

# ═══════════════════════════════════════════════════════════════════════════════
# Estrella de fondo
# ═══════════════════════════════════════════════════════════════════════════════
class _BGStar:
    def __init__(self, w: int = W, h: int = H, y: float | None = None):
        self._w, self._h = w, h
        self._spawn(y)
    def _spawn(self, y=None):
        self.x     = random.randint(0, self._w)
        self.y     = float(y if y is not None else self._h)
        self.speed = random.uniform(0.03, 0.18)
        self.base  = random.randint(22, 95)
        self.size  = random.choice([1, 1, 1, 1, 2])
        self.phase = random.uniform(0, math.tau)
        self.freq  = random.uniform(0.4, 1.8)
    def update(self, dt):
        self.y    -= self.speed
        self.phase += self.freq * dt
        if self.y < 0:
            self._spawn()
    def draw(self, surf):
        b   = int(self.base * (0.6 + 0.4 * math.sin(self.phase)))
        col = (b, b, min(255, b + 15))
        ix, iy = int(self.x), int(self.y)
        if 0 <= ix < self._w and 0 <= iy < self._h:
            if self.size == 1:
                surf.set_at((ix, iy), col)
            else:
                pygame.draw.circle(surf, col, (ix, iy), self.size)

# ═══════════════════════════════════════════════════════════════════════════════
# Partícula flotante
# ═══════════════════════════════════════════════════════════════════════════════
class Particle:
    DURATION = 0.9
    def __init__(self, x, y, text, color=GREEN):
        self.x, self.y = float(x), float(y)
        self.text  = text
        self.color = color
        self.born  = time.time()
        self.vx    = random.uniform(-0.6, 0.6)
        self.vy    = random.uniform(-2.2, -1.4)
    @property
    def alive(self): return (time.time() - self.born) < self.DURATION
    @property
    def alpha(self):
        t = (time.time() - self.born) / self.DURATION
        return int(max(0, 255 * (1 - t ** 1.4)))
    def update(self):
        self.x += self.vx; self.y += self.vy; self.vy += 0.06

# ═══════════════════════════════════════════════════════════════════════════════
# QTE Event
# ═══════════════════════════════════════════════════════════════════════════════
@dataclass
class _QTE:
    sequence:       list
    current:        int   = 0
    start:          float = field(default_factory=time.time)
    duration:       float = 10.0
    failed:         bool  = False
    fail_until:     float = 0.0

    @property
    def done(self):    return self.current >= len(self.sequence)
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
        pygame.display.set_caption(f"Clicker Game  [{MODE.upper()}]")
        self.clock = pygame.time.Clock()
        self.music = music

        # ── Fuentes ──────────────────────────────────────────────────────────
        self.f_title = _f(20, bold=True)
        self.f_big   = _f(32, bold=True)
        self.f_med   = _f(17)
        self.f_sm    = _f(14)
        self.f_xs    = _f(12)
        self.f_btn   = _f(14, bold=True)
        self.f_click = _f(26, bold=True)
        self.f_stat  = _f(16)
        self.f_part  = _f(15, bold=True)

        # ── Juego ─────────────────────────────────────────────────────────────
        self.game       = GameState()
        self.start_time = time.time()
        self.particles: list[Particle] = []

        # ── Starfield ────────────────────────────────────────────────────────
        self.stars = [_BGStar(W, H, random.randint(0, H)) for _ in range(90)]

        # ── UI state ─────────────────────────────────────────────────────────
        self.status_msg   = ""
        self.status_color = TXT
        self.status_end   = 0.0

        self.click_anim     = 0.0
        self.click_anim_end = 0.0

        # ── Minijuego base ────────────────────────────────────────────────────
        self.next_minigame = time.time() + MINIGAME_COOLDOWN
        self.mini_available = False
        self.mini_open      = False
        self.mini_type      = ""       # "guess" | "react" | "seq"

        # Estado: GUESS
        self.mini_answer   = 0
        self.mini_selected = -1
        self.mini_result_end = 0.0

        # Estado: REACT
        self.react_pos      = (0, 0)
        self.react_start    = 0.0
        self.react_duration = 5.0
        self.react_rect: pygame.Rect | None = None

        # Estado: SEQ
        self.seq_colors:      list[int] = []
        self.seq_phase:       str       = "show"   # "show" | "input" | "result"
        self.seq_show_idx:    int       = -1
        self.seq_show_until:  float     = 0.0
        self.seq_input:       list[int] = []
        self.seq_result:      str       = ""       # "win" | "fail"
        self.seq_result_end:  float     = 0.0
        self.seq_box_rects:   list      = [None] * 4

        # ── QTE ───────────────────────────────────────────────────────────────
        self._qte: _QTE | None = None
        self._next_qte         = time.time() + QTE_COOLDOWN

        # ── Pausa / Victoria ─────────────────────────────────────────────────
        self.paused            = False
        self.victory_dismissed = False
        self._exit_to: str | None = None

        self._pause_resume_rect: pygame.Rect | None = None
        self._pause_menu_rect:   pygame.Rect | None = None
        self._pause_quit_rect:   pygame.Rect | None = None

        # ── Scroll panel derecho ─────────────────────────────────────────────
        self._right_scroll    = 0
        self._right_max_scroll = 0

        # ── Rects interactivos ────────────────────────────────────────────────
        self._click_rect:    pygame.Rect | None = None
        self._prestige_rect: pygame.Rect | None = None
        self._mini_rect:     pygame.Rect | None = None
        self._gen_rects:     list = [None] * len(GENERATORS)
        self._gu_rects:      list = [None] * len(GEN_UPGRADES)
        self._upg_rects:     list = [None] * len(CLICK_UPGRADES)
        self._mini_num_rects: list = []

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

            # Modal minijuego (GUESS / SEQ) bloquea input
            if self.mini_open and self.mini_type in ("guess", "seq"):
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.mini_open = False
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.mini_type == "guess" and self.mini_selected == -1:
                        for i, r in enumerate(self._mini_num_rects):
                            if r and r.collidepoint(mx, my):
                                self._resolve_guess(i + 1)
                    elif self.mini_type == "seq" and self.seq_phase == "input":
                        for i, r in enumerate(self.seq_box_rects):
                            if r and r.collidepoint(mx, my):
                                self._handle_seq_click(i)
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

            # QTE: intercepta teclas de letra (no bloquea mouse)
            if self._qte and not self._qte.done and not self._qte.expired and not self._qte.failed:
                if event.type == pygame.KEYDOWN:
                    kn = pygame.key.name(event.key).upper()
                    if len(kn) == 1 and kn in _QTE_KEY_SET:
                        self._handle_qte_key(kn)
                        continue   # tecla consumida por QTE

            # React: clic en target (no bloquea, sigue procesando)
            if self.mini_open and self.mini_type == "react":
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.react_rect and self.react_rect.collidepoint(mx, my):
                        self._resolve_react()

            # Scroll panel derecho
            if event.type == pygame.MOUSEWHEEL and mx > SPLIT:
                self._right_scroll = max(0, min(
                    self._right_scroll - event.y * 28,
                    self._right_max_scroll
                ))

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
        dt  = now - self._prev_time
        self._prev_time = now

        self.game.tick()
        self.game.check_victory()

        # Minijuego disponible
        if not self.mini_available and now >= self.next_minigame:
            self.mini_available = True

        # Cerrar GUESS tras mostrar resultado
        if self.mini_open and self.mini_type == "guess" and self.mini_selected != -1:
            if now >= self.mini_result_end:
                self.mini_open = False

        # React: timeout
        if self.mini_open and self.mini_type == "react":
            if now >= self.react_start + self.react_duration:
                self._set_status("¡Demasiado lento! Sin recompensa.", RED, 3.0)
                self.mini_open = False

        # Seq: avanzar fase SHOW
        if self.mini_open and self.mini_type == "seq" and self.seq_phase == "show":
            if self.seq_show_idx == -1 and now >= self.seq_show_until:
                self.seq_show_idx   = 0
                self.seq_show_until = now + 0.75
            elif self.seq_show_idx >= 0 and now >= self.seq_show_until:
                self.seq_show_idx += 1
                if self.seq_show_idx >= 4:
                    self.seq_phase    = "input"
                    self.seq_show_idx = -1
                else:
                    self.seq_show_until = now + 0.75

        # Seq: cerrar resultado
        if self.mini_open and self.mini_type == "seq" and self.seq_phase == "result":
            if now >= self.seq_result_end:
                self.mini_open = False

        # QTE: limpiar expirado/fallado
        if self._qte:
            if self._qte.expired or (self._qte.failed and now >= self._qte.fail_until):
                if self._qte.expired and not self._qte.failed:
                    self._set_status("QTE expirado. ¡Más rápido!", MUTED, 2.0)
                self._qte      = None
                self._next_qte = now + QTE_COOLDOWN

        # QTE: spawn
        if self._qte is None and now >= self._next_qte:
            self._spawn_qte()

        # Partículas y animaciones
        for p in self.particles: p.update()
        self.particles = [p for p in self.particles if p.alive]
        for s in self.stars: s.update(dt)

        if now < self.click_anim_end:
            self.click_anim = min(1.0, (self.click_anim_end - now) / 0.12)
        else:
            self.click_anim = 0.0

    # ─────────────────────────────────────────────────────────────────────────
    # Acciones de juego
    # ─────────────────────────────────────────────────────────────────────────
    def _do_click(self, mx, my):
        earned = self.game.click()
        cx = (mx if self._click_rect and self._click_rect.collidepoint(mx, my)
              else (self._click_rect.centerx if self._click_rect else mx))
        cy = (my if self._click_rect and self._click_rect.collidepoint(mx, my)
              else (self._click_rect.centery if self._click_rect else my))
        self.particles.append(Particle(cx, cy - 10, f"+{fmt(earned)}", GOLD))
        self.click_anim_end = time.time() + 0.12

    def _buy_generator(self, idx: int):
        gen = GENERATORS[idx]
        if self.game.buy_generator(gen["id"]):
            n = self.game.generators[gen["id"]]
            self._set_status(f"✓ {gen['name']} comprado (×{n})", GREEN)
        elif not self.game.generator_unlocked(gen["id"]):
            self._set_status(f"{gen['name']}: bloqueado", RED)
        else:
            self._set_status(f"Faltan {fmt(self.game.generator_cost(gen['id']) - self.game.points)} pts", RED)

    def _buy_gen_upgrade(self, idx: int):
        gu = GEN_UPGRADES[idx]
        if self.game.buy_gen_upgrade(gu["id"]):
            target_name = next((g["name"] for g in GENERATORS if g["id"] == gu["target"]), "todos")
            self._set_status(f"✓ {gu['name']} — ×{gu['mult']} {target_name}", ORANGE)
        elif self.game.gen_upgrades.get(gu["id"]):
            self._set_status("Ya activo.", MUTED)
        else:
            self._set_status(f"Faltan {fmt(self.game.gen_upgrade_cost(gu['id']) - self.game.points)} pts", RED)

    def _buy_upgrade(self, idx: int):
        upg = CLICK_UPGRADES[idx]
        if self.game.buy_click_upgrade(upg["id"]):
            bonus = upg.get("bonus", 0)
            mult  = upg.get("mult", 1.0)
            parts = []
            if bonus: parts.append(f"+{fmt(bonus*BOOST)}/clic")
            if mult != 1.0: parts.append(f"×{mult:.1f}")
            self._set_status(f"✓ {upg['name']}  {' '.join(parts)}", GREEN)
        elif self.game.click_upgrades[upg["id"]]:
            self._set_status("Ya tienes esa mejora.", MUTED)
        elif not self.game.click_upgrade_unlocked(upg["id"]):
            self._set_status(f"{upg['name']}: bloqueado", RED)
        else:
            self._set_status(f"Faltan {fmt(self.game.click_upgrade_cost(upg['id']) - self.game.points)} pts", RED)

    def _do_prestige(self):
        if self.game.can_prestige():
            n = self.game.prestige_count + 1
            self.game.prestige()
            self._set_status(f"★  Prestige {n}!  Mult total: ×{self.game.prestige_multiplier:.1f}", GOLD, 4.0)
            self.particles.clear()

    # ─────────────────────────────────────────────────────────────────────────
    # Minijuego: apertura y tipos
    # ─────────────────────────────────────────────────────────────────────────
    def _open_minigame(self):
        if not self.mini_available:
            return
        self.mini_available = False
        self.next_minigame  = time.time() + MINIGAME_COOLDOWN
        self.mini_type      = random.choice(["guess", "react", "seq"])
        self.mini_selected  = -1

        if self.mini_type == "guess":
            self.mini_answer = random.randint(1, 9)
            self.mini_open   = True

        elif self.mini_type == "react":
            margin = 60
            self.react_pos   = (
                random.randint(margin, SPLIT - margin),
                random.randint(HDR_H + margin, H - STS_H - margin),
            )
            self.react_start = time.time()
            self.react_rect  = None
            self.mini_open   = True

        elif self.mini_type == "seq":
            cols = list(range(4)); random.shuffle(cols)
            self.seq_colors     = cols
            self.seq_phase      = "show"
            self.seq_show_idx   = -1
            self.seq_show_until = time.time() + 0.5   # pausa inicial
            self.seq_input      = []
            self.seq_result     = ""
            self.seq_box_rects  = [None] * 4
            self.mini_open      = True

    def _resolve_guess(self, guess: int):
        self.mini_selected   = guess
        self.mini_result_end = time.time() + 1.8
        if guess == self.mini_answer:
            self.game.activate_minigame(2.0, 30.0)
            self._set_status("¡CORRECTO! Boost ×2 por 30s", PURPLE, 4.0)
        else:
            self._set_status(f"Fallaste (era {self.mini_answer}). Sin recompensa.", RED, 3.0)

    def _resolve_react(self):
        elapsed = time.time() - self.react_start
        mult    = 3.0 if elapsed < 1.0 else (2.5 if elapsed < 2.0 else (2.0 if elapsed < 3.0 else 1.5))
        self.game.activate_minigame(mult, 30.0)
        self._set_status(f"¡{elapsed:.2f}s!  Boost ×{mult:.1f} por 30s", PURPLE, 4.0)
        self.mini_open = False

    def _handle_seq_click(self, box_idx: int):
        if self.seq_phase != "input":
            return
        expected = self.seq_colors[len(self.seq_input)]
        if box_idx == expected:
            self.seq_input.append(box_idx)
            if len(self.seq_input) == 4:
                self.game.activate_minigame(2.5, 45.0)
                self.seq_phase      = "result"
                self.seq_result     = "win"
                self.seq_result_end = time.time() + 2.0
                self._set_status("¡SECUENCIA PERFECTA! Boost ×2.5 por 45s", GREEN, 4.0)
        else:
            self.seq_phase      = "result"
            self.seq_result     = "fail"
            self.seq_result_end = time.time() + 2.0
            self._set_status("Secuencia incorrecta. Sin recompensa.", RED, 3.0)

    # ─────────────────────────────────────────────────────────────────────────
    # QTE
    # ─────────────────────────────────────────────────────────────────────────
    def _spawn_qte(self):
        keys = list(_QTE_KEY_SET)
        random.shuffle(keys)
        self._qte = _QTE(sequence=keys[:8])

    def _handle_qte_key(self, key: str):
        if not self._qte or self._qte.done or self._qte.expired:
            return
        if key == self._qte.sequence[self._qte.current]:
            self._qte.current += 1
            if self._qte.done:
                self.game.activate_qte_bonus(3.0, 60.0)
                self._set_status("¡QTE COMPLETADO!  Bonus ×3 por 60s", PURPLE, 5.0)
                self._qte      = None
                self._next_qte = time.time() + QTE_COOLDOWN
        else:
            self._qte.failed     = True
            self._qte.fail_until = time.time() + 1.5
            self._set_status("QTE fallado.", RED, 2.0)

    def _set_status(self, msg: str, color=TXT, duration: float = 2.5):
        self.status_msg   = msg
        self.status_color = color
        self.status_end   = time.time() + duration

    # ─────────────────────────────────────────────────────────────────────────
    # Dibujo principal
    # ─────────────────────────────────────────────────────────────────────────
    def _draw(self):
        self.screen.fill(BG)
        for s in self.stars: s.draw(self.screen)

        mx, my = pygame.mouse.get_pos()
        self._draw_header()
        self._draw_left(mx, my)
        self._draw_right(mx, my)
        self._draw_divider()
        self._draw_status_bar()
        self._draw_particles()

        # React: target flotante (fuera del modal)
        if self.mini_open and self.mini_type == "react":
            self._draw_react_target()

        # Modal: guess o seq
        if self.mini_open and self.mini_type in ("guess", "seq"):
            self._draw_minigame_modal(mx, my)

        # QTE overlay
        if self._qte:
            self._draw_qte_panel()

        if self.game.won and not self.victory_dismissed:
            self._draw_victory_overlay()

        if self.paused:
            self._draw_pause_overlay(mx, my)

        pygame.display.flip()

    # ─────────────────────────────────────────────────────────────────────────
    # Header
    # ─────────────────────────────────────────────────────────────────────────
    def _draw_header(self):
        rect = pygame.Rect(0, 0, W, HDR_H)
        pygame.draw.rect(self.screen, PANEL, rect)
        sh = pygame.Surface((W, 1), pygame.SRCALPHA)
        sh.fill((255, 255, 255, 20))
        self.screen.blit(sh, (0, 0))
        pygame.draw.line(self.screen, BORDER, (0, HDR_H), (W, HDR_H), 1)

        tag_c = ORANGE if MODE == "demo" else ACCENT
        draw_text(self.screen, f"[{MODE.upper()}]", self.f_title, tag_c, PAD, HDR_H // 2, "midleft")
        draw_text(self.screen, "CLICKER  GAME", self.f_title, TXT, W // 2, HDR_H // 2, "center")
        draw_text(self.screen, f"t: {fmt_time(time.time()-self.start_time)}", self.f_stat, MUTED,
                  W - PAD, HDR_H // 2, "midright")
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
        y = self._draw_stats_box(x0, y, pw) + PAD
        y = self._draw_progress_section(x0, y, pw) + PAD
        y = self._draw_click_button(x0, y, pw, mx, my) + PAD
        y = self._draw_prestige_section(x0, y, pw, mx, my) + PAD
        y = self._draw_minigame_section(x0, y, pw, mx, my) + PAD
        self._draw_booster_bars(x0, y, pw)

    def _draw_stats_box(self, x, y, w) -> int:
        g = self.game
        eff_click = g.click_value * g.click_mult * g.prestige_multiplier * g.minigame_multiplier * g.qte_bonus_mult
        rows = [
            ("Puntos",     fmt(g.points),           GOLD),
            ("PPS",        fmt(g.pps()) + "/s",      ACCENT),
            ("Por clic",   fmt(eff_click),            TXT),
            ("Acumulado",  fmt(g.total_points),       MUTED),
            ("× bonus",    f"×{g.prestige_multiplier:.1f}  ×{g.click_mult:.1f}clic", ORANGE),
        ]
        row_h = 22
        box_h = len(rows) * row_h + PAD * 2
        draw_panel(self.screen, pygame.Rect(x, y, w, box_h))
        ry = y + PAD
        for label, value, color in rows:
            draw_text(self.screen, label + ":", self.f_stat, MUTED, x + PAD, ry)
            draw_text(self.screen, value, self.f_stat, color, x + w - PAD, ry, "topright")
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
        btn_h = 80
        rect  = pygame.Rect(x, y, w, btn_h)
        self._click_rect = rect
        hov    = rect.collidepoint(mx, my)
        shrink = int(self.click_anim * 4)
        draw_r = rect.inflate(-shrink * 2, -shrink * 2)
        c = lerp_color((28, 62, 38) if not hov else (42, 88, 52), (18, 42, 26), self.click_anim)
        pygame.draw.rect(self.screen, c, draw_r, border_radius=10)
        pygame.draw.rect(self.screen, GREEN, draw_r, 2, border_radius=10)
        if hov:
            for r in range(4, 0, -1):
                gs = pygame.Surface((draw_r.width + r*4, draw_r.height + r*4), pygame.SRCALPHA)
                gs.fill((63, 185, 80, 10))
                self.screen.blit(gs, (draw_r.x - r*2, draw_r.y - r*2))
        draw_text(self.screen, "¡ C L I C !", self.f_click, GREEN, draw_r.centerx, draw_r.centery, "center")
        hint = "[ESPACIO]" if not hov else "clic aquí"
        draw_text(self.screen, hint, self.f_sm, MUTED, draw_r.centerx, draw_r.bottom - 14, "center")
        return y + btn_h

    def _draw_prestige_section(self, x, y, w, mx, my) -> int:
        g = self.game; btn_h = 38
        if g.can_prestige():
            rect = pygame.Rect(x, y, w, btn_h)
            self._prestige_rect = rect
            hov  = rect.collidepoint(mx, my)
            pygame.draw.rect(self.screen, (78, 52, 8) if not hov else (108, 78, 14), rect, border_radius=8)
            pygame.draw.rect(self.screen, GOLD, rect, 2, border_radius=8)
            draw_text(self.screen, f"★  PRESTIGE {g.prestige_count+1}  ({'×1.5' if g.prestige_count==0 else '×2.0'})",
                      self.f_btn, GOLD, rect.centerx, rect.centery, "center")
        else:
            self._prestige_rect = None
            n = g.prestige_count + 1
            if n <= 2:
                draw_text(self.screen, f"Faltan {fmt(g.prestige_threshold()-g.total_points)} pts → Prestige {n}",
                          self.f_sm, MUTED, x, y + 12)
            else:
                draw_text(self.screen, "2 reinicios completados", self.f_sm, MUTED, x, y + 12)
        return y + btn_h

    def _draw_minigame_section(self, x, y, w, mx, my) -> int:
        g   = self.game
        now = time.time()
        btn_h = 38

        if g.minigame_active:
            left  = g.minigame_seconds_left()
            bg_r  = pygame.Rect(x, y, w, btn_h)
            bar_r = pygame.Rect(x, y, int(w * left / 30.0), btn_h)
            pygame.draw.rect(self.screen, (38, 18, 58), bg_r,  border_radius=8)
            pygame.draw.rect(self.screen, (68, 38, 98), bar_r, border_radius=8)
            pygame.draw.rect(self.screen, PURPLE, bg_r, 2, border_radius=8)
            draw_text(self.screen, f"★ BOOST ×{g.minigame_multiplier:.1f}  {left:.0f}s",
                      self.f_btn, PURPLE, bg_r.centerx, bg_r.centery, "center")
            self._mini_rect = None
        elif self.mini_available:
            rect = pygame.Rect(x, y, w, btn_h)
            self._mini_rect = rect
            pulse = 0.5 + 0.5 * math.sin(now * 4.0)
            hov   = rect.collidepoint(mx, my)
            c = lerp_color((42, 28, 68), (62, 44, 100), pulse if not hov else 1.0)
            pygame.draw.rect(self.screen, c, rect, border_radius=8)
            pygame.draw.rect(self.screen, PURPLE, rect, 2, border_radius=8)
            draw_text(self.screen, "★  MINIJUEGO DISPONIBLE  ★",
                      self.f_btn, PURPLE, rect.centerx, rect.centery, "center")
        else:
            self._mini_rect = None
            cd = max(0.0, self.next_minigame - now)
            draw_text(self.screen, f"Minijuego en: {fmt_time(cd)}", self.f_sm, MUTED, x, y + 12)
        return y + btn_h

    def _draw_booster_bars(self, x, y, w):
        """Muestra barras de bono QTE si activo."""
        g = self.game
        if not g.qte_bonus_active:
            return
        left = g.qte_bonus_seconds_left()
        bar_r = pygame.Rect(x, y, w, 28)
        fill_r = pygame.Rect(x, y, int(w * left / 60.0), 28)
        pygame.draw.rect(self.screen, (25, 15, 45), bar_r,  border_radius=6)
        pygame.draw.rect(self.screen, (60, 35, 110), fill_r, border_radius=6)
        pygame.draw.rect(self.screen, PURPLE, bar_r, 2, border_radius=6)
        draw_text(self.screen, f"QTE ×3  {left:.0f}s",
                  self.f_xs, PURPLE, bar_r.centerx, bar_r.centery, "center")

    # ─────────────────────────────────────────────────────────────────────────
    # Panel derecho (scrollable)
    # ─────────────────────────────────────────────────────────────────────────
    def _sy(self, vy: int) -> int:
        """Virtual y → screen y en el panel derecho."""
        return HDR_H + PAD + vy - self._right_scroll

    def _row_visible(self, vy: int, rh: int) -> bool:
        sy = self._sy(vy)
        return sy + rh > HDR_H and sy < H - STS_H

    def _draw_divider(self):
        pygame.draw.line(self.screen, BORDER, (SPLIT, HDR_H), (SPLIT, H - STS_H), 1)

    def _draw_right(self, mx, my):
        x0 = SPLIT + PAD
        pw = W - SPLIT - PAD * 2

        clip = pygame.Rect(SPLIT + 1, HDR_H + 1, W - SPLIT - 2, H - HDR_H - STS_H - 2)
        self.screen.set_clip(clip)

        vy = 0
        vy = self._draw_generators_right(x0, vy, pw, mx, my)
        vy += PAD
        sep_sy = self._sy(vy)
        if HDR_H < sep_sy < H - STS_H:
            pygame.draw.line(self.screen, BORDER, (x0, sep_sy), (x0 + pw, sep_sy), 1)
        vy += PAD + 1
        vy = self._draw_gen_upgrades_right(x0, vy, pw, mx, my)
        vy += PAD
        sep_sy = self._sy(vy)
        if HDR_H < sep_sy < H - STS_H:
            pygame.draw.line(self.screen, BORDER, (x0, sep_sy), (x0 + pw, sep_sy), 1)
        vy += PAD + 1
        vy = self._draw_click_upgrades_right(x0, vy, pw, mx, my)
        vy += PAD * 2

        self.screen.set_clip(None)

        visible_h = H - HDR_H - STS_H - PAD * 2
        self._right_max_scroll = max(0, vy - visible_h)
        self._right_scroll     = min(self._right_scroll, self._right_max_scroll)

        # Scrollbar
        if self._right_max_scroll > 0:
            panel_h = H - HDR_H - STS_H
            bar_h   = max(18, panel_h * panel_h // max(1, vy))
            bar_y   = HDR_H + int(self._right_scroll / self._right_max_scroll * (panel_h - bar_h))
            pygame.draw.rect(self.screen, MUTED, (W - 6, bar_y, 3, bar_h), border_radius=1)

    def _draw_generators_right(self, x, vy, w, mx, my) -> int:
        if self._row_visible(vy, 24):
            draw_text(self.screen, "GENERADORES", self.f_med, TXT, x, self._sy(vy))
        vy += 26
        row_h = 68; btn_w = 130; btn_h = 30

        for i, gen in enumerate(GENERATORS):
            if not self._row_visible(vy, row_h):
                self._gen_rects[i] = None
                vy += row_h; continue
            sy     = self._sy(vy)
            rect   = pygame.Rect(x, sy, w, row_h - 4)
            locked = not self.game.generator_unlocked(gen["id"])
            if locked:
                draw_panel(self.screen, rect, color=(16, 20, 25))
                draw_text(self.screen, "???  bloqueado", self.f_med, MUTED, x + PAD, sy + (row_h-4)//2 - 9)
                self._gen_rects[i] = None
            else:
                owned   = self.game.generators[gen["id"]]
                cost    = self.game.generator_cost(gen["id"])
                can_buy = self.game.can_buy_generator(gen["id"])
                pps_r   = gen["pps"] * self.game.prestige_multiplier * BOOST * self.game.gen_mult.get(gen["id"], 1.0) * self.game.gen_mult.get("all", 1.0)
                draw_panel(self.screen, rect, color=(24, 30, 40) if can_buy else PANEL)
                draw_text(self.screen, gen["name"], self.f_med, TXT, x + PAD, sy + 10)
                draw_text(self.screen, f"×{owned}", self.f_med, ACCENT if owned > 0 else MUTED, x + PAD + 130, sy + 10)
                pps_str = f"+{fmt(pps_r * owned)}/s" if owned > 0 else f"{fmt(pps_r)}/s c/u"
                draw_text(self.screen, pps_str, self.f_xs, MUTED, x + PAD, sy + 36)
                btn_r = pygame.Rect(x + w - btn_w - PAD, sy + (row_h - 4 - btn_h) // 2, btn_w, btn_h)
                self._gen_rects[i] = btn_r
                hov = btn_r.collidepoint(mx, my)
                bc  = lerp_color(GREEN_D if can_buy else (30, 25, 25), (50, 110, 60), 0.5) if (hov and can_buy) else (GREEN_D if can_buy else (30, 25, 25))
                pygame.draw.rect(self.screen, bc, btn_r, border_radius=6)
                pygame.draw.rect(self.screen, GREEN if can_buy else RED, btn_r, 1, border_radius=6)
                draw_text(self.screen, fmt(cost), self.f_btn, GREEN if can_buy else RED,
                          btn_r.centerx, btn_r.centery, "center")
            vy += row_h
        return vy

    def _draw_gen_upgrades_right(self, x, vy, w, mx, my) -> int:
        if self._row_visible(vy, 24):
            draw_text(self.screen, "POTENCIADORES", self.f_med, TXT, x, self._sy(vy))
        vy += 26
        row_h = 46; btn_w = 110; btn_h = 28; icon_s = 26

        # Solo mostrar desbloqueados (comprados o disponibles)
        visible_indices = [
            i for i, gu in enumerate(GEN_UPGRADES)
            if self.game.gen_upgrades.get(gu["id"]) or self.game.gen_upgrade_unlocked(gu["id"])
        ]
        if not visible_indices:
            if self._row_visible(vy, 22):
                draw_text(self.screen, "Compra generadores para desbloquear", self.f_xs, MUTED, x + PAD, self._sy(vy))
            return vy + 22

        for i in range(len(GEN_UPGRADES)):
            self._gu_rects[i] = None  # reset all

        for idx in visible_indices:
            gu     = GEN_UPGRADES[idx]
            bought = self.game.gen_upgrades.get(gu["id"], False)
            if not self._row_visible(vy, row_h):
                vy += row_h; continue

            sy = self._sy(vy)
            rect = pygame.Rect(x, sy, w, row_h - 3)
            cost = self.game.gen_upgrade_cost(gu["id"])
            can  = self.game.can_buy_gen_upgrade(gu["id"])

            bg_c = (16, 20, 25) if bought else ((24, 30, 40) if can else PANEL)
            draw_panel(self.screen, rect, color=bg_c)

            # Icono
            icon_c = (60, 44, 14) if bought else ((50, 36, 8) if gu["target"] == "all" else (28, 44, 68))
            ix = x + PAD
            iy = sy + (row_h - 3 - icon_s) // 2
            pygame.draw.rect(self.screen, icon_c, (ix, iy, icon_s, icon_s), border_radius=5)
            draw_text(self.screen, gu["icon"], self.f_sm, (220, 220, 220), ix + icon_s // 2, iy + icon_s // 2, "center")

            tx = ix + icon_s + 6
            name_c = MUTED if bought else TXT
            draw_text(self.screen, gu["name"], self.f_btn, name_c, tx, sy + 8)
            tgt_name = next((g["name"] for g in GENERATORS if g["id"] == gu["target"]), "Todos")
            draw_text(self.screen, f"×{gu['mult']:.1f}  {tgt_name}", self.f_xs, MUTED, tx, sy + 28)

            if bought:
                draw_text(self.screen, "✓", self.f_btn, GREEN, x + w - PAD - 20, sy + (row_h-3)//2 - 7)
            else:
                btn_r = pygame.Rect(x + w - btn_w - PAD, sy + (row_h - 3 - btn_h) // 2, btn_w, btn_h)
                self._gu_rects[idx] = btn_r
                hov = btn_r.collidepoint(mx, my)
                bc  = lerp_color(GREEN_D if can else (30, 25, 25), (50, 110, 60), 0.5) if (hov and can) else (GREEN_D if can else (30, 25, 25))
                pygame.draw.rect(self.screen, bc, btn_r, border_radius=6)
                pygame.draw.rect(self.screen, ORANGE if can else RED, btn_r, 1, border_radius=6)
                draw_text(self.screen, fmt(cost), self.f_xs, ORANGE if can else RED,
                          btn_r.centerx, btn_r.centery, "center")
            vy += row_h
        return vy

    def _draw_click_upgrades_right(self, x, vy, w, mx, my) -> int:
        if self._row_visible(vy, 24):
            draw_text(self.screen, "MEJORAS DE CLIC", self.f_med, TXT, x, self._sy(vy))
        vy += 26
        row_h = 46; btn_w = 110; btn_h = 28; icon_s = 26

        for i in range(len(CLICK_UPGRADES)):
            self._upg_rects[i] = None

        for i, upg in enumerate(CLICK_UPGRADES):
            unlocked = self.game.click_upgrade_unlocked(upg["id"])
            if not unlocked:
                continue   # no mostrar bloqueados
            bought = self.game.click_upgrades[upg["id"]]
            if not self._row_visible(vy, row_h):
                vy += row_h; continue

            sy   = self._sy(vy)
            rect = pygame.Rect(x, sy, w, row_h - 3)
            cost = self.game.click_upgrade_cost(upg["id"])
            can  = not bought and self.game.points >= cost

            bg_c = (16, 20, 25) if bought else ((24, 30, 40) if can else PANEL)
            draw_panel(self.screen, rect, color=bg_c)

            # Icono
            has_mult = upg.get("mult", 1.0) != 1.0
            icon_c   = (28, 44, 68) if not has_mult else (60, 44, 14)
            ix = x + PAD
            iy = sy + (row_h - 3 - icon_s) // 2
            pygame.draw.rect(self.screen, icon_c, (ix, iy, icon_s, icon_s), border_radius=5)
            draw_text(self.screen, upg["icon"], self.f_sm, (220, 220, 220), ix + icon_s // 2, iy + icon_s // 2, "center")

            tx = ix + icon_s + 6
            name_c = MUTED if bought else TXT
            draw_text(self.screen, upg["name"], self.f_btn, name_c, tx, sy + 8)

            bonus = upg.get("bonus", 0)
            mult  = upg.get("mult", 1.0)
            parts = []
            if bonus: parts.append(f"+{fmt(bonus*BOOST)}")
            if mult != 1.0: parts.append(f"×{mult:.1f} clic")
            draw_text(self.screen, "  ".join(parts) or "—", self.f_xs, MUTED, tx, sy + 28)

            if bought:
                draw_text(self.screen, "✓", self.f_btn, GREEN, x + w - PAD - 20, sy + (row_h-3)//2 - 7)
            else:
                btn_r = pygame.Rect(x + w - btn_w - PAD, sy + (row_h - 3 - btn_h) // 2, btn_w, btn_h)
                self._upg_rects[i] = btn_r
                hov = btn_r.collidepoint(mx, my)
                bc  = lerp_color(GREEN_D if can else (30, 25, 25), (50, 110, 60), 0.5) if (hov and can) else (GREEN_D if can else (30, 25, 25))
                pygame.draw.rect(self.screen, bc, btn_r, border_radius=6)
                pygame.draw.rect(self.screen, GREEN if can else RED, btn_r, 1, border_radius=6)
                draw_text(self.screen, fmt(cost), self.f_xs, GREEN if can else RED,
                          btn_r.centerx, btn_r.centery, "center")
            vy += row_h
        return vy

    # ─────────────────────────────────────────────────────────────────────────
    # Status bar
    # ─────────────────────────────────────────────────────────────────────────
    def _draw_status_bar(self):
        rect = pygame.Rect(0, H - STS_H, W, STS_H)
        pygame.draw.rect(self.screen, PANEL, rect)
        pygame.draw.line(self.screen, BORDER, (0, H - STS_H), (W, H - STS_H), 1)
        now = time.time()
        if self.status_msg and now < self.status_end:
            draw_text(self.screen, self.status_msg, self.f_sm, self.status_color, PAD, H - STS_H + 8)
        else:
            draw_text(self.screen, "ESPACIO: clic  |  clic en generadores/mejoras  |  ESC: pausa  |  scroll: más upgrades",
                      self.f_sm, MUTED, PAD, H - STS_H + 8)

    # ─────────────────────────────────────────────────────────────────────────
    # Partículas
    # ─────────────────────────────────────────────────────────────────────────
    def _draw_particles(self):
        for p in self.particles:
            s = self.f_part.render(p.text, True, p.color)
            s.set_alpha(p.alpha)
            self.screen.blit(s, (int(p.x - s.get_width() // 2), int(p.y)))

    # ─────────────────────────────────────────────────────────────────────────
    # Minijuego: react target (sin modal)
    # ─────────────────────────────────────────────────────────────────────────
    def _draw_react_target(self):
        elapsed  = time.time() - self.react_start
        progress = min(1.0, elapsed / self.react_duration)
        radius   = max(20, int(55 - 35 * progress))
        rx, ry   = self.react_pos

        # Anillo exterior pulsante
        pulse = 0.5 + 0.5 * math.sin(time.time() * 8.0)
        outer = radius + int(8 + 5 * pulse)
        ring_surf = pygame.Surface((outer*2+4, outer*2+4), pygame.SRCALPHA)
        alpha = int(80 + 80 * pulse)
        pygame.draw.circle(ring_surf, (*ORANGE, alpha), (outer+2, outer+2), outer, 3)
        self.screen.blit(ring_surf, (rx - outer - 2, ry - outer - 2))

        # Círculo principal
        pygame.draw.circle(self.screen, (200, 80, 30), (rx, ry), radius)
        inner_c = lerp_color((255, 140, 80), (255, 80, 40), progress)
        pygame.draw.circle(self.screen, inner_c, (rx, ry), max(8, radius - 10))

        # Texto "¡CLIC!"
        if radius > 28:
            draw_text(self.screen, "¡CLIC!", self.f_xs, (255, 255, 220), rx, ry, "center")

        # Timer bar debajo del target
        bar_w = 100
        bar_r = pygame.Rect(rx - bar_w//2, ry + radius + 6, bar_w, 6)
        pygame.draw.rect(self.screen, PANEL2, bar_r, border_radius=3)
        fill_r = pygame.Rect(bar_r.x, bar_r.y, int(bar_w * (1 - progress)), 6)
        fc = lerp_color(GREEN, RED, progress)
        if fill_r.width > 0:
            pygame.draw.rect(self.screen, fc, fill_r, border_radius=3)

        # Rect para detección de clic
        self.react_rect = pygame.Rect(rx - radius, ry - radius, radius * 2, radius * 2)

    # ─────────────────────────────────────────────────────────────────────────
    # Minijuego: modal GUESS / SEQ
    # ─────────────────────────────────────────────────────────────────────────
    def _draw_minigame_modal(self, mx, my):
        overlay = pygame.Surface((W, H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 165))
        self.screen.blit(overlay, (0, 0))

        if self.mini_type == "guess":
            self._draw_guess_modal(mx, my)
        elif self.mini_type == "seq":
            self._draw_seq_modal(mx, my)

    def _draw_guess_modal(self, mx, my):
        mw, mh = 480, 300
        mx0, my0 = (W-mw)//2, (H-mh)//2
        modal = pygame.Rect(mx0, my0, mw, mh)
        draw_panel(self.screen, modal, color=(26, 18, 48), border=PURPLE, radius=12)
        pygame.draw.rect(self.screen, PURPLE, modal, 2, border_radius=12)
        draw_text(self.screen, "M I N I J U E G O  —  A D I V I N A", self.f_title, PURPLE,
                  mx0 + mw//2, my0 + 22, "center")
        draw_text(self.screen, "¿Qué número estoy pensando?  (1 – 9)", self.f_sm, TXT,
                  mx0 + mw//2, my0 + 52, "center")
        draw_text(self.screen, "Premio: ×2 PPS por 30s", self.f_xs, MUTED, mx0 + mw//2, my0 + 72, "center")

        nw, nh = 44, 44; gap = 10
        tw = 9*nw + 8*gap; sx = mx0 + (mw-tw)//2; by = my0 + 105
        self._mini_num_rects = []
        rs = self.mini_selected != -1
        for i in range(9):
            bx = sx + i*(nw+gap)
            br = pygame.Rect(bx, by, nw, nh)
            self._mini_num_rects.append(br)
            n = i + 1
            if rs:
                bc, tc = ((28,88,38), GREEN) if n==self.mini_answer else ((RED_D,RED) if n==self.mini_selected else ((BTN_D,MUTED)))
            else:
                hov = br.collidepoint(mx, my)
                bc, tc = ((55, 38, 88) if hov else (36, 26, 62)), TXT
            pygame.draw.rect(self.screen, bc, br, border_radius=6)
            pygame.draw.rect(self.screen, PURPLE if not rs else tc, br, 1, border_radius=6)
            draw_text(self.screen, str(n), self.f_click, tc, bx+nw//2, by+nh//2, "center")

        if rs:
            msg, c = ("¡CORRECTO! ×2 PPS activo 30s", GREEN) if self.mini_selected==self.mini_answer else (f"Fallaste.  Era el  {self.mini_answer}", RED)
            draw_text(self.screen, msg, self.f_med, c, mx0+mw//2, my0+205, "center")
        else:
            draw_text(self.screen, "ESC para cancelar", self.f_xs, MUTED, mx0+mw//2, my0+265, "center")

    def _draw_seq_modal(self, mx, my):
        mw, mh = 480, 340
        mx0, my0 = (W-mw)//2, (H-mh)//2
        modal = pygame.Rect(mx0, my0, mw, mh)
        draw_panel(self.screen, modal, color=(18, 26, 30), border=ACCENT, radius=12)
        pygame.draw.rect(self.screen, ACCENT, modal, 2, border_radius=12)

        draw_text(self.screen, "M I N I J U E G O  —  S E C U E N C I A", self.f_title, ACCENT,
                  mx0+mw//2, my0+22, "center")

        if self.seq_phase == "show":
            draw_text(self.screen, "Memoriza la secuencia...", self.f_sm, TXT, mx0+mw//2, my0+55, "center")
        elif self.seq_phase == "input":
            remaining = 4 - len(self.seq_input)
            draw_text(self.screen, f"¡Repite!  {remaining} restante(s)", self.f_sm, GOLD, mx0+mw//2, my0+55, "center")
        else:
            msg, c = ("¡PERFECTO! ×2.5 PPS 45s", GREEN) if self.seq_result == "win" else ("Orden incorrecto.", RED)
            draw_text(self.screen, msg, self.f_med, c, mx0+mw//2, my0+55, "center")

        # 4 cajas de color 2×2
        cw, ch = 100, 70; gap = 12
        grid_w = 2*(cw+gap)-gap; grid_h = 2*(ch+gap)-gap
        gx = mx0 + (mw - grid_w)//2
        gy = my0 + 90
        color_names = ["ROJO", "VERDE", "AZUL", "ORO"]

        self.seq_box_rects = []
        for ci in range(4):
            col = ci % 2; row = ci // 2
            bx = gx + col*(cw+gap)
            by = gy + row*(ch+gap)
            br = pygame.Rect(bx, by, cw, ch)
            self.seq_box_rects.append(br)

            # Resaltar según fase
            highlight = False
            if self.seq_phase == "show":
                highlight = (ci == self.seq_show_idx) and self.seq_show_idx >= 0
                # show_idx indica qué color de la SECUENCIA está mostrando;
                # la caja a iluminar es la que tiene el color seq_colors[show_idx]
                highlight = (ci == self.seq_colors[self.seq_show_idx]) if (0 <= self.seq_show_idx < 4) else False
            elif self.seq_phase == "input":
                highlight = br.collidepoint(mx, my)

            base_c = SEQ_COLORS[ci]
            dim_c  = SEQ_DIM[ci]
            c = base_c if highlight else dim_c
            pygame.draw.rect(self.screen, c, br, border_radius=8)
            pygame.draw.rect(self.screen, base_c, br, 2, border_radius=8)
            draw_text(self.screen, color_names[ci], self.f_xs, (220,220,220), bx+cw//2, by+ch//2, "center")

        # Barra de progreso de input
        if self.seq_phase == "input":
            for pi, inp in enumerate(self.seq_input):
                dot_x = mx0 + (mw - (4*20 + 3*8))//2 + pi*(20+8)
                dot_y = my0 + 265
                pygame.draw.circle(self.screen, SEQ_COLORS[inp], (dot_x+10, dot_y+10), 8)

        draw_text(self.screen, "Premio: ×2.5 PPS por 45s", self.f_xs, MUTED, mx0+mw//2, my0+300, "center")
        draw_text(self.screen, "ESC para cancelar", self.f_xs, MUTED, mx0+mw//2, my0+322, "center")

    # ─────────────────────────────────────────────────────────────────────────
    # QTE Panel
    # ─────────────────────────────────────────────────────────────────────────
    def _draw_qte_panel(self):
        if not self._qte:
            return
        qw, qh = 520, 80
        qx = (W - qw) // 2
        qy = HDR_H + 6

        now    = time.time()
        pulse  = 0.5 + 0.5 * math.sin(now * 5.0)
        border_c = lerp_color(RED, ORANGE, pulse)

        surf = pygame.Surface((qw, qh), pygame.SRCALPHA)
        surf.fill((22, 14, 38, 215))
        self.screen.blit(surf, (qx, qy))
        pygame.draw.rect(self.screen, border_c, (qx, qy, qw, qh), 2, border_radius=8)

        if self._qte.failed:
            draw_text(self.screen, "✗ QTE FALLADO", self.f_btn, RED, qx + qw//2, qy + qh//2, "center")
            return

        # Título
        draw_text(self.screen, "¡ QTE !  ×3 por 60s", self.f_xs, ORANGE, qx + 10, qy + 6)

        # Teclas
        key_w = 30
        seq   = self._qte.sequence
        cur   = self._qte.current
        total_w = len(seq) * key_w + (len(seq)-1) * 5
        kx = qx + (qw - total_w) // 2
        ky = qy + 22
        for j, k in enumerate(seq):
            krect = pygame.Rect(kx + j*(key_w+5), ky, key_w, 26)
            if j < cur:
                c_bg, c_txt, c_brd = (22, 80, 35), GREEN, GREEN
            elif j == cur:
                c_bg = lerp_color((60, 40, 80), (80, 55, 110), pulse)
                c_txt, c_brd = (255, 230, 100), ORANGE
            else:
                c_bg, c_txt, c_brd = (30, 25, 45), MUTED, BORDER
            pygame.draw.rect(self.screen, c_bg, krect, border_radius=5)
            pygame.draw.rect(self.screen, c_brd, krect, 1, border_radius=5)
            draw_text(self.screen, k, self.f_xs, c_txt, krect.centerx, krect.centery, "center")

        # Timer bar
        left = self._qte.time_left
        bar  = pygame.Rect(qx + 10, qy + qh - 14, qw - 20, 7)
        pygame.draw.rect(self.screen, PANEL2, bar, border_radius=3)
        fill_w = int((qw - 20) * left / self._qte.duration)
        if fill_w > 0:
            fc = lerp_color(GREEN, RED, 1.0 - left / self._qte.duration)
            pygame.draw.rect(self.screen, fc, pygame.Rect(bar.x, bar.y, fill_w, 7), border_radius=3)

    # ─────────────────────────────────────────────────────────────────────────
    # Overlay de victoria
    # ─────────────────────────────────────────────────────────────────────────
    def _draw_victory_overlay(self):
        overlay = pygame.Surface((W, H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 210))
        self.screen.blit(overlay, (0, 0))

        vw, vh = 500, 320
        vx, vy = (W-vw)//2, (H-vh)//2
        vr = pygame.Rect(vx, vy, vw, vh)
        draw_panel(self.screen, vr, color=(18, 28, 18), border=GOLD, radius=14)
        pygame.draw.rect(self.screen, GOLD, vr, 2, border_radius=14)

        pulse = 0.5 + 0.5 * math.sin(time.time() * 2.0)
        draw_text(self.screen, "¡  V I C T O R I A  !", self.f_big,
                  lerp_color(GOLD, (255, 220, 80), pulse * 0.5),
                  vx + vw//2, vy + 30, "center")
        pygame.draw.line(self.screen, GOLD, (vx+40, vy+70), (vx+vw-40, vy+70), 1)

        lines = [
            ("Tiempo",       fmt_time(time.time()-self.start_time), TXT),
            ("Puntuación",   fmt(self.game.high_score),             GOLD),
            ("Reinicios",    f"{self.game.prestige_count} / 2",     ORANGE),
            ("Mult click",   f"×{self.game.click_mult:.1f}",        ACCENT),
        ]
        for j, (label, val, c) in enumerate(lines):
            ry = vy + 90 + j*38
            draw_text(self.screen, label+":", self.f_med, MUTED, vx+60, ry)
            draw_text(self.screen, val, self.f_med, c, vx+vw-60, ry, "topright")

        draw_text(self.screen, "★  MODO INFINITO DESBLOQUEADO  ★", self.f_btn, GREEN,
                  vx+vw//2, vy+250, "center")
        ha = int(128 + 127 * math.sin(time.time() * 3.0))
        hs = self.f_sm.render("Haz clic para continuar", True, MUTED)
        hs.set_alpha(ha)
        self.screen.blit(hs, hs.get_rect(center=(vx+vw//2, vy+286)))

    # ─────────────────────────────────────────────────────────────────────────
    # Overlay de pausa
    # ─────────────────────────────────────────────────────────────────────────
    def _draw_pause_overlay(self, mx: int, my: int):
        overlay = pygame.Surface((W, H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 175))
        self.screen.blit(overlay, (0, 0))

        pw, ph = 360, 280
        px, py = (W-pw)//2, (H-ph)//2
        panel  = pygame.Rect(px, py, pw, ph)
        draw_panel(self.screen, panel, color=(20, 24, 32), border=BORDER, radius=12)
        pygame.draw.rect(self.screen, BORDER, panel, 2, border_radius=12)

        cx = px + pw//2
        draw_text(self.screen, "PAUSA", self.f_big, TXT, cx, py+24, "center")
        pygame.draw.line(self.screen, BORDER, (px+30, py+62), (px+pw-30, py+62), 1)

        vol = self.music.get_volume() if self.music else 0.0
        bx  = cx - 80
        draw_text(self.screen, "Vol:", self.f_sm, MUTED, bx-36, py+80)
        vbar = pygame.Rect(bx, py+80, 160, 12)
        pygame.draw.rect(self.screen, PANEL2, vbar, border_radius=4)
        if vol > 0:
            pygame.draw.rect(self.screen, ACCENT, pygame.Rect(bx, py+80, int(160*vol), 12), border_radius=4)
        pygame.draw.rect(self.screen, BORDER, vbar, 1, border_radius=4)
        draw_text(self.screen, f"{int(vol*100)}%", self.f_sm, MUTED, bx+168, py+80)
        draw_text(self.screen, "← → para ajustar", self.f_xs, MUTED, cx, py+100, "center")

        y0 = py + 128
        rects = {}
        for label, key in [("CONTINUAR", "resume"), ("MENÚ PRINCIPAL", "menu"), ("SALIR DEL JUEGO", "quit")]:
            r   = pygame.Rect(cx-120, y0, 240, 42)
            hov = r.collidepoint(mx, my)
            pygame.draw.rect(self.screen, lerp_color((28,34,42), ACCENT, 0.12) if hov else (26,32,40), r, border_radius=8)
            pygame.draw.rect(self.screen, ACCENT if hov else BORDER, r, 2, border_radius=8)
            draw_text(self.screen, label, self.f_btn, (230,240,255) if hov else TXT, r.centerx, r.centery, "center")
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
