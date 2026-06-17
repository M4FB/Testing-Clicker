"""Pantalla de menú principal con starfield y partículas flotantes."""
import pygame
import sys
import time
import random
import math

from src.config import MODE

# ── Paleta (misma que pygame_ui para coherencia) ─────────────────────────────
BG      = ( 13,  17,  23)
PANEL   = ( 22,  27,  34)
BORDER  = ( 48,  54,  61)
TXT     = (201, 209, 217)
MUTED   = (110, 118, 129)
ACCENT  = ( 88, 166, 255)
GOLD    = (210, 153,  34)
GREEN   = ( 63, 185,  80)
ORANGE  = (255, 166,  87)
PURPLE  = (188, 140, 255)

FONT_REG  = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def _lerp(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


# ── Estrella de fondo ─────────────────────────────────────────────────────────
class _Star:
    def __init__(self, w: int, h: int, y: float | None = None):
        self.w = w
        self.h = h
        self._spawn(y)

    def _spawn(self, y: float | None = None):
        self.x     = random.randint(0, self.w)
        self.y     = float(y if y is not None else self.h)
        self.speed = random.uniform(0.04, 0.35)
        self.base  = random.randint(35, 160)
        self.size  = random.choice([1, 1, 1, 1, 2])
        self.phase = random.uniform(0, math.tau)
        self.freq  = random.uniform(0.6, 2.2)

    def update(self, dt: float):
        self.y     -= self.speed
        self.phase += self.freq * dt
        if self.y < 0:
            self._spawn()

    def draw(self, surf: pygame.Surface):
        b   = int(self.base * (0.65 + 0.35 * math.sin(self.phase)))
        col = (b, b, min(255, b + 20))
        ix, iy = int(self.x), int(self.y)
        if self.size == 1:
            try:
                surf.set_at((ix, iy), col)
            except IndexError:
                pass
        else:
            pygame.draw.circle(surf, col, (ix, iy), self.size)


# ── Texto flotante (+X) ───────────────────────────────────────────────────────
class _FloatText:
    _VALUES = ["+1", "+5", "+10", "+50", "+100", "+500", "+1K"]
    _COLORS = [ACCENT, GOLD, GREEN, PURPLE, (200, 220, 255)]

    def __init__(self, w: int, h: int):
        self.x        = random.randint(w // 6, w * 5 // 6)
        self.y        = float(h + random.randint(10, 60))
        self.speed    = random.uniform(0.25, 0.65)
        self.text     = random.choice(self._VALUES)
        self.color    = random.choice(self._COLORS)
        self._alpha   = random.randint(50, 110)
        self._born    = time.time()
        self._life    = random.uniform(5.0, 9.0)

    @property
    def alive(self) -> bool:
        return (time.time() - self._born) < self._life

    def update(self):
        self.y -= self.speed

    def draw(self, surf: pygame.Surface, font: pygame.font.Font):
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
    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.clock  = pygame.time.Clock()
        self.W      = screen.get_width()
        self.H      = screen.get_height()

        # Fuentes
        try:
            self.f_title = pygame.font.Font(FONT_BOLD, 54)
            self.f_sub   = pygame.font.Font(FONT_REG, 17)
            self.f_btn   = pygame.font.Font(FONT_BOLD, 20)
            self.f_float = pygame.font.Font(FONT_REG, 13)
            self.f_hint  = pygame.font.Font(FONT_REG, 12)
        except Exception:
            self.f_title = pygame.font.SysFont("sans", 54, bold=True)
            self.f_sub   = pygame.font.SysFont("sans", 17)
            self.f_btn   = pygame.font.SysFont("sans", 20, bold=True)
            self.f_float = pygame.font.SysFont("sans", 13)
            self.f_hint  = pygame.font.SysFont("sans", 12)

        # Estrellas de fondo (distribuidas desde el inicio en posiciones aleatorias)
        self.stars = [_Star(self.W, self.H, random.randint(0, self.H))
                      for _ in range(110)]

        # Textos flotantes
        self.floats: list[_FloatText] = []
        self._next_float = time.time()

        # Botones
        btn_w, btn_h = 310, 56
        cx      = self.W // 2
        cy_base = self.H // 2 + 28
        gap     = 72
        self.buttons = [
            {"label": "NUEVA PARTIDA", "action": "new",  "en": True,
             "rect": pygame.Rect(cx - btn_w // 2, cy_base,          btn_w, btn_h)},
            {"label": "CONTINUAR",     "action": "cont", "en": False,
             "rect": pygame.Rect(cx - btn_w // 2, cy_base + gap,     btn_w, btn_h)},
            {"label": "SALIR",         "action": "quit", "en": True,
             "rect": pygame.Rect(cx - btn_w // 2, cy_base + gap * 2, btn_w, btn_h)},
        ]
        self._t0 = time.time()

    # ── Loop principal ────────────────────────────────────────────────────────
    def run(self) -> str:
        """Bloquea hasta que el usuario elige.  Devuelve 'new', 'cont' o 'quit'."""
        prev = time.time()
        while True:
            now = time.time()
            dt  = now - prev
            prev = now

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        return "quit"
                    if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        return "new"
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for btn in self.buttons:
                        if btn["en"] and btn["rect"].collidepoint(event.pos):
                            return btn["action"]

            # Spawnar textos flotantes
            if now >= self._next_float:
                self.floats.append(_FloatText(self.W, self.H))
                self._next_float = now + random.uniform(0.5, 1.4)
            self.floats = [f for f in self.floats if f.alive]

            for s in self.stars:
                s.update(dt)
            for f in self.floats:
                f.update()

            mx, my = pygame.mouse.get_pos()
            self._draw(mx, my, now)
            self.clock.tick(60)

    # ── Dibujo ────────────────────────────────────────────────────────────────
    def _draw(self, mx: int, my: int, now: float):
        self.screen.fill(BG)

        # Estrellas
        for s in self.stars:
            s.draw(self.screen)

        # Textos flotantes
        for f in self.floats:
            f.draw(self.screen, self.f_float)

        cx = self.W // 2
        elapsed = now - self._t0

        # ── Título con resplandor ─────────────────────────────────────────
        pulse      = 0.5 + 0.5 * math.sin(elapsed * 1.4)
        title_col  = _lerp(ACCENT, (160, 210, 255), pulse * 0.45)
        title_text = "CLICKER  GAME"

        glow_surf = self.f_title.render(title_text, True, title_col)
        glow_a    = int(18 + 32 * pulse)
        cy_title  = self.H // 2 - 106
        for r in range(6, 0, -1):
            g = glow_surf.copy()
            g.set_alpha(glow_a // r)
            for dx, dy in ((-r, 0), (r, 0), (0, -r), (0, r)):
                self.screen.blit(g, g.get_rect(center=(cx + dx, cy_title + dy)))

        main_s = self.f_title.render(title_text, True, title_col)
        self.screen.blit(main_s, main_s.get_rect(center=(cx, cy_title)))

        # Modo y subtítulo
        mode_col = ORANGE if MODE == "demo" else ACCENT
        self._blit_center(self.f_sub, f"[ {MODE.upper()} ]", mode_col, cx, cy_title + 52)
        self._blit_center(self.f_sub, "Laboratorio de Testing de Software", MUTED, cx, cy_title + 78)

        # Separador
        pygame.draw.line(self.screen, BORDER,
                         (cx - 190, cy_title + 100), (cx + 190, cy_title + 100), 1)

        # ── Botones ───────────────────────────────────────────────────────
        for btn in self.buttons:
            rect = btn["rect"]
            hov  = btn["en"] and rect.collidepoint(mx, my)

            if not btn["en"]:
                bc, tc, bord = (18, 22, 28), (48, 54, 65), (30, 36, 46)
            elif hov:
                bc   = _lerp((28, 40, 62), ACCENT, 0.18)
                tc   = (230, 240, 255)
                bord = ACCENT
            else:
                bc, tc, bord = (26, 32, 42), TXT, BORDER

            pygame.draw.rect(self.screen, bc,   rect, border_radius=10)
            pygame.draw.rect(self.screen, bord, rect, 2, border_radius=10)

            # Brillo superior en hover
            if hov:
                shine = pygame.Surface((rect.width - 4, 2), pygame.SRCALPHA)
                shine.fill((*ACCENT, 60))
                self.screen.blit(shine, (rect.x + 2, rect.y + 2))

            ls = self.f_btn.render(btn["label"], True, tc)
            self.screen.blit(ls, ls.get_rect(center=rect.center))

        # ── Pista de teclas ───────────────────────────────────────────────
        self._blit_center(self.f_hint,
                          "ENTER: nueva partida   |   ESC: salir",
                          MUTED, cx, self.H - 20)

        pygame.display.flip()

    def _blit_center(self, font, text, color, cx, cy):
        s = font.render(text, True, color)
        self.screen.blit(s, s.get_rect(center=(cx, cy)))
