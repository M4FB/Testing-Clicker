"""Constantes de pantalla, fuentes y helpers compartidos por la UI."""
import time

import pygame

from src.fx import BORDER, PANEL

# ─── Layout ──────────────────────────────────────────────────────────────────
W, H   = 1024, 680
FPS    = 60
SPLIT  = 400
HDR_H  = 50
STS_H  = 30
PAD    = 14

# ─── Fuentes (rutas centralizadas; única fuente de verdad de toda la app) ────
_FONT_REG  = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
_FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
_font_cache: dict = {}


def font(size, bold=False):
    """Devuelve una fuente cacheada; cae a la del sistema si falta DejaVu."""
    key = (size, bold)
    f = _font_cache.get(key)
    if f is None:
        try:
            f = pygame.font.Font(_FONT_BOLD if bold else _FONT_REG, size)
        except Exception:
            try:
                path = pygame.font.match_font("dejavusans", bold=bold) \
                       or pygame.font.get_default_font()
                f = pygame.font.Font(path, size)
            except Exception:
                f = pygame.font.SysFont("sans", size, bold=bold)
        _font_cache[key] = f
    return f


def make_fonts() -> dict:
    """Diccionario único de fuentes; las claves cortas las usan los minijuegos."""
    return {
        "title": font(20, bold=True),
        "big":   font(32, bold=True),
        "md":    font(17),
        "sm":    font(14),
        "xs":    font(12),
        "btn":   font(14, bold=True),
        "click": font(28, bold=True),
        "stat":  font(16),
        "part":  font(15, bold=True),
        "part2": font(20, bold=True),
    }


# ─── Formato ─────────────────────────────────────────────────────────────────
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


def draw_panel(surf, rect, color=PANEL, border=BORDER, radius=9):
    pygame.draw.rect(surf, color, rect, border_radius=radius)
    shine = pygame.Surface((max(1, rect.width - 4), 1), pygame.SRCALPHA)
    shine.fill((255, 255, 255, 16))
    surf.blit(shine, (rect.x + 2, rect.y + 2))
    pygame.draw.rect(surf, border, rect, 1, border_radius=radius)


# ─── Transiciones (fundido a negro entre pantallas) ──────────────────────────
def fade_out(screen, clock=None, dur: float = 0.30) -> None:
    """Funde a negro el frame ya dibujado en `screen` (bloqueante, ~dur s)."""
    snap = screen.copy()
    blk  = pygame.Surface(screen.get_size())
    blk.fill((0, 0, 0))
    clock = clock or pygame.time.Clock()
    t0 = time.time()
    while True:
        t = (time.time() - t0) / dur
        if t >= 1.0:
            break
        screen.blit(snap, (0, 0))
        blk.set_alpha(int(255 * t))
        screen.blit(blk, (0, 0))
        pygame.display.flip()
        clock.tick(FPS)
    screen.fill((0, 0, 0))
    pygame.display.flip()


def fade_in_alpha(start: float, dur: float = 0.30) -> int:
    """Alpha (255→0) de un velo negro para fundir DESDE negro al entrar.

    Devuelve 0 una vez superada la ventana de tiempo (sin velo)."""
    t = (time.time() - start) / dur
    if t >= 1.0:
        return 0
    return int(255 * (1.0 - max(0.0, t)))


# ─── Pantalla completa ───────────────────────────────────────────────────────
def is_fullscreen() -> bool:
    surf = pygame.display.get_surface()
    return bool(surf and surf.get_flags() & pygame.FULLSCREEN)


def toggle_fullscreen() -> bool:
    """Alterna ventana/pantalla completa (requiere display con SCALED)."""
    try:
        pygame.display.toggle_fullscreen()
    except pygame.error:
        pass
    return is_fullscreen()
