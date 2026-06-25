"""Overlays modales: pausa, victoria, vitrina de logros y selector de minijuego."""
import math
import time

import pygame

from src.fx import (
    BORDER, TXT, MUTED, ACCENT, GOLD, GREEN, ORANGE, PURPLE,
    lerp_color, scale_color, draw_text, shiny_button, striped_bar, draw_coin, clamp,
)
from src.ui.common import W, H, fmt, fmt_time
from src import achievements as ach
from src import sfx
from src.minigames import MINIGAMES


def _dim(cv, alpha=175):
    overlay = pygame.Surface((W, H), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, alpha))
    cv.blit(overlay, (0, 0))


# ═══════════════════════════════════════════════════════════════════════════════
# Pausa
# ═══════════════════════════════════════════════════════════════════════════════
class PauseOverlay:
    BUTTONS = [("CONTINUAR", "resume"), ("VER GRÁFICO", "stats_graph"),
               ("PANTALLA COMPLETA", "fullscreen"), ("MENÚ PRINCIPAL", "menu"),
               ("SALIR DEL JUEGO", "quit")]

    def __init__(self, ui):
        self.ui = ui
        self.rects: dict[str, pygame.Rect] = {}

    def click(self, mx, my) -> str | None:
        for key, r in self.rects.items():
            if r.collidepoint(mx, my):
                return key
        return None

    def draw(self, cv, mx, my):
        ui = self.ui
        _dim(cv)
        now = time.time()

        pw, ph = 380, 444
        px, py = (W - pw) // 2, (H - ph) // 2
        panel  = pygame.Rect(px, py, pw, ph)
        pygame.draw.rect(cv, (20, 24, 34), panel, border_radius=12)
        pygame.draw.rect(cv, BORDER, panel, 2, border_radius=12)

        cx = px + pw // 2
        draw_text(cv, "PAUSA", ui.F["big"], TXT, cx, py + 26, "center")
        pygame.draw.line(cv, BORDER, (px + 30, py + 62), (px + pw - 30, py + 62), 1)

        bx = cx - 60
        mvol = ui.music.get_volume() if ui.music else 0.0
        draw_text(cv, "Música:", ui.F["sm"], MUTED, bx - 64, py + 78)
        striped_bar(cv, pygame.Rect(bx, py + 78, 150, 13), mvol, ACCENT,
                    now=now, radius=5)
        draw_text(cv, f"{int(mvol*100)}%", ui.F["sm"], MUTED, bx + 158, py + 78)

        svol = sfx.get_volume()
        draw_text(cv, "Sonidos:", ui.F["sm"], MUTED, bx - 64, py + 102)
        striped_bar(cv, pygame.Rect(bx, py + 102, 150, 13), svol, PURPLE,
                    now=now, radius=5)
        draw_text(cv, f"{int(svol*100)}%", ui.F["sm"], MUTED, bx + 158, py + 102)

        draw_text(cv, "← → música    ↑ ↓ sonidos", ui.F["xs"], MUTED,
                  cx, py + 126, "center")

        y0 = py + 152
        self.rects = {}
        for label, key in self.BUTTONS:
            r   = pygame.Rect(cx - 125, y0, 250, 42)
            hov = r.collidepoint(mx, my)
            shiny_button(cv, r, (27, 34, 46), ACCENT if hov else BORDER,
                         hover=hov, now=now, radius=9)
            draw_text(cv, label, ui.F["btn"], (232, 241, 255) if hov else TXT,
                      r.centerx, r.centery, "center")
            self.rects[key] = r
            y0 += 52


# ═══════════════════════════════════════════════════════════════════════════════
# Victoria (con resumen estadístico de la partida)
# ═══════════════════════════════════════════════════════════════════════════════
class VictoryOverlay:
    def __init__(self, ui):
        self.ui = ui

    def draw(self, cv):
        ui = self.ui
        g  = ui.game
        st = g.stats
        _dim(cv, 210)
        now = time.time()

        vw, vh = 560, 470
        vx, vy = (W - vw) // 2, (H - vh) // 2
        vr = pygame.Rect(vx, vy, vw, vh)
        pygame.draw.rect(cv, (18, 28, 18), vr, border_radius=14)
        pulse = 0.5 + 0.5 * math.sin(now * 2.0)
        pygame.draw.rect(cv, lerp_color(GOLD, (255, 226, 110), pulse), vr, 2,
                         border_radius=14)

        draw_coin(cv, vx + 60, vy + 38, 18, now)
        draw_coin(cv, vx + vw - 60, vy + 38, 18, now + 0.9)
        draw_text(cv, "¡  V I C T O R I A  !", ui.F["big"],
                  lerp_color(GOLD, (255, 220, 80), pulse * 0.5),
                  vx + vw // 2, vy + 36, "center")
        pygame.draw.line(cv, GOLD, (vx + 40, vy + 72), (vx + vw - 40, vy + 72), 1)

        lines = [
            ("Tiempo",          fmt_time(now - ui.start_time),                TXT),
            ("Puntuación",      fmt(g.high_score),                            GOLD),
            ("Clics",           f"{st['clicks']:,}".replace(",", " "),        TXT),
            ("Críticos",        f"{st['crits']:,}".replace(",", " "),         ORANGE),
            ("Mejor combo",     f"×{st['best_combo']}",                       GREEN),
            ("Minijuegos",      f"{st['mini_won']} ganados / {st['mini_lost']} perdidos", PURPLE),
            ("Monedas doradas", str(st["golden"]),                            GOLD),
            ("QTE",             f"{st['qte_won']} completados",               ACCENT),
            ("Logros",          f"{ach.unlocked_count(g)} / {len(ach.ACHIEVEMENTS)}", GOLD),
        ]
        for j, (label, val, c) in enumerate(lines):
            ry = vy + 88 + j * 31
            draw_text(cv, label + ":", ui.F["md"], MUTED, vx + 60, ry)
            draw_text(cv, val, ui.F["md"], c, vx + vw - 60, ry, "topright")

        draw_text(cv, "★  MODO INFINITO DESBLOQUEADO  ★", ui.F["btn"], GREEN,
                  vx + vw // 2, vy + vh - 62, "center")
        draw_text(cv, "Haz clic para continuar", ui.F["sm"], MUTED,
                  vx + vw // 2, vy + vh - 30, "center",
                  alpha=int(128 + 127 * math.sin(now * 3.0)))


# ═══════════════════════════════════════════════════════════════════════════════
# Vitrina de logros
# ═══════════════════════════════════════════════════════════════════════════════
class AchievementsOverlay:
    def __init__(self, ui):
        self.ui = ui
        self.panel: pygame.Rect | None = None

    def click_outside(self, mx, my) -> bool:
        return self.panel is not None and not self.panel.collidepoint(mx, my)

    def draw(self, cv, mx, my):
        ui = self.ui
        _dim(cv, 190)
        now = time.time()

        pw, ph = 780, 560
        px, py = (W - pw) // 2, (H - ph) // 2
        self.panel = pygame.Rect(px, py, pw, ph)
        pygame.draw.rect(cv, (18, 22, 32), self.panel, border_radius=14)
        pygame.draw.rect(cv, GOLD, self.panel, 2, border_radius=14)

        n_un = ach.unlocked_count(ui.game)
        draw_text(cv, "LOGROS", ui.F["big"], GOLD, px + pw // 2, py + 28, "center")
        draw_text(cv, f"{n_un} / {len(ach.ACHIEVEMENTS)} desbloqueados",
                  ui.F["sm"], MUTED, px + pw // 2, py + 56, "center")
        pygame.draw.line(cv, BORDER, (px + 30, py + 72), (px + pw - 30, py + 72), 1)

        cols  = 2
        cw    = (pw - 30 * 2 - 16) // cols
        rh    = 56
        for i, a in enumerate(ach.ACHIEVEMENTS):
            col, row = i % cols, i // cols
            rx = px + 30 + col * (cw + 16)
            ry = py + 84 + row * rh
            r  = pygame.Rect(rx, ry, cw, rh - 8)
            unlocked = ui.game.achievements.get(a["id"], False)

            if unlocked:
                pygame.draw.rect(cv, (32, 30, 18), r, border_radius=9)
                pygame.draw.rect(cv, scale_color(GOLD, 0.8), r, 1, border_radius=9)
            else:
                pygame.draw.rect(cv, (16, 19, 27), r, border_radius=9)
                pygame.draw.rect(cv, (36, 42, 54), r, 1, border_radius=9)

            ic = pygame.Rect(r.x + 9, r.y + (r.height - 30) // 2, 30, 30)
            pygame.draw.rect(cv, (58, 46, 14) if unlocked else (26, 30, 40),
                             ic, border_radius=7)
            draw_text(cv, a["icon"] if unlocked else "?", ui.F["sm"],
                      GOLD if unlocked else (60, 68, 82),
                      ic.centerx, ic.centery, "center")

            tx = ic.right + 9
            draw_text(cv, a["name"], ui.F["btn"],
                      GOLD if unlocked else (90, 98, 112), tx, r.y + 7)
            draw_text(cv, a["desc"], ui.F["xs"],
                      TXT if unlocked else (62, 70, 84), tx, r.y + 27)
            if unlocked:
                draw_text(cv, "✓", ui.F["btn"], GREEN,
                          r.right - 16, r.centery, "center")

        draw_text(cv, "L o ESC para cerrar", ui.F["xs"], MUTED,
                  px + pw // 2, py + ph - 18, "center",
                  alpha=int(150 + 105 * math.sin(now * 2.5)))


# ═══════════════════════════════════════════════════════════════════════════════
# Selector de minijuego (se desbloquea tras MINI_SELECT_WINS victorias)
# ═══════════════════════════════════════════════════════════════════════════════
class MiniSelectOverlay:
    def __init__(self, ui):
        self.ui = ui
        self.rects: list = []      # [(rect, clase), ...]

    def click(self, mx, my):
        """Devuelve la clase de minijuego elegida, o None."""
        for r, cls in self.rects:
            if r.collidepoint(mx, my):
                return cls
        return None

    def draw(self, cv, mx, my):
        ui = self.ui
        _dim(cv, 185)
        now = time.time()

        pw, ph = 700, 470
        px, py = (W - pw) // 2, (H - ph) // 2
        panel  = pygame.Rect(px, py, pw, ph)
        pygame.draw.rect(cv, (20, 18, 34), panel, border_radius=14)
        pygame.draw.rect(cv, PURPLE, panel, 2, border_radius=14)

        draw_text(cv, "ELIGE TU MINIJUEGO", ui.F["big"], PURPLE,
                  px + pw // 2, py + 30, "center")
        draw_text(cv, "Tu experiencia te permite escoger", ui.F["xs"], MUTED,
                  px + pw // 2, py + 56, "center")

        mini_stats = ui.game.stats["mini"]
        cols = 2
        cw, rh = (pw - 30 * 2 - 16) // cols, 112
        self.rects = []
        for i, cls in enumerate(MINIGAMES):
            col, row = i % cols, i // cols
            rx = px + 30 + col * (cw + 16)
            ry = py + 78 + row * (rh + 10)
            r  = pygame.Rect(rx, ry, cw, rh)
            hov = r.collidepoint(mx, my)

            base = scale_color(cls.COLOR, 0.16 if not hov else 0.26)
            pygame.draw.rect(cv, base, r, border_radius=10)
            pygame.draw.rect(cv, cls.COLOR if hov else scale_color(cls.COLOR, 0.5),
                             r, 2, border_radius=10)
            draw_text(cv, cls.TITLE, ui.F["btn"], cls.COLOR,
                      r.x + 14, r.y + 12)
            draw_text(cv, cls.HINT, ui.F["xs"], MUTED, r.x + 14, r.y + 36)

            st = mini_stats.get(cls.KEY, {})
            won, lost = st.get("won", 0), st.get("lost", 0)
            best      = st.get("best", 0.0)
            stat_line = f"G: {won}   P: {lost}   mejor: {best:g}" if (won or lost) \
                        else "sin jugar"
            draw_text(cv, stat_line, ui.F["xs"],
                      GREEN if won else MUTED, r.x + 14, r.bottom - 24)
            if hov:
                draw_text(cv, "JUGAR →", ui.F["btn"], cls.COLOR,
                          r.right - 14, r.bottom - 22, "midright")
            self.rects.append((r, cls))

        draw_text(cv, "ESC para volver (no pierdes el minijuego)", ui.F["xs"],
                  MUTED, px + pw // 2, py + ph - 16, "center",
                  alpha=int(150 + 105 * math.sin(now * 2.5)))


# ═══════════════════════════════════════════════════════════════════════════════
# Gráfico Estadístico de Producción
# ═══════════════════════════════════════════════════════════════════════════════
class StatsGraphOverlay:
    def __init__(self, ui):
        self.ui = ui
        self.panel: pygame.Rect | None = None
        self.back_btn: pygame.Rect | None = None

    def click_outside(self, mx, my) -> bool:
        return self.panel is not None and not self.panel.collidepoint(mx, my)

    def click(self, mx, my) -> bool:
        if self.back_btn and self.back_btn.collidepoint(mx, my):
            return True
        return False

    def draw(self, cv, mx, my):
        ui = self.ui
        _dim(cv, 195)
        now = time.time()

        pw, ph = 780, 500
        px, py = (W - pw) // 2, (H - ph) // 2
        self.panel = pygame.Rect(px, py, pw, ph)
        pygame.draw.rect(cv, (18, 22, 32), self.panel, border_radius=14)
        pygame.draw.rect(cv, ACCENT, self.panel, 2, border_radius=14)

        draw_text(cv, "GRÁFICO DE PRODUCCIÓN HISTÓRICA", ui.F["big"], ACCENT,
                  px + pw // 2, py + 26, "center")
        draw_text(cv, "Evolución de tus puntos totales acumulados", ui.F["xs"], MUTED,
                  px + pw // 2, py + 52, "center")
        pygame.draw.line(cv, BORDER, (px + 30, py + 68), (px + pw - 30, py + 68), 1)

        # Área de dibujo del gráfico
        gx, gy, gw, gh = px + 60, py + 90, pw - 120, ph - 170
        pygame.draw.rect(cv, (12, 15, 23), (gx, gy, gw, gh), border_radius=6)
        pygame.draw.rect(cv, BORDER, (gx, gy, gw, gh), 1, border_radius=6)

        hist = ui.game.stats.get("history", [])
        if len(hist) >= 2:
            v_min = min(hist)
            v_max = max(hist)
            if v_max == v_min:
                v_max += 1.0

            # Líneas de cuadrícula e indicadores del eje Y
            for i in range(4):
                grid_y = gy + gh - i * (gh // 3)
                pygame.draw.line(cv, (30, 36, 50), (gx, grid_y), (gx + gw, grid_y), 1)
                val = v_min + i * ((v_max - v_min) / 3)
                draw_text(cv, fmt(val), ui.F["xs"], MUTED, gx - 8, grid_y, "midright")

            pts = []
            for idx, val in enumerate(hist):
                tx = gx + int(idx * (gw / (len(hist) - 1)))
                frac = (val - v_min) / (v_max - v_min)
                ty = gy + gh - int(frac * gh)
                pts.append((tx, ty))

            # Dibujar curva conectando los puntos
            if len(pts) >= 2:
                pygame.draw.lines(cv, ACCENT, False, pts, 3)

            # Dibujar puntos de datos individuales
            hovered_pt = None
            for idx, (tx, ty) in enumerate(pts):
                pygame.draw.circle(cv, ACCENT, (tx, ty), 4)
                if abs(mx - tx) <= 8 and abs(my - ty) <= 8:
                    hovered_pt = (tx, ty, hist[idx])

            # Mostrar tooltip si el mouse está sobre un punto
            if hovered_pt:
                tx, ty, val = hovered_pt
                pygame.draw.circle(cv, GOLD, (tx, ty), 6)
                tw, th = 120, 30
                tbx, tby = tx - tw // 2, ty - th - 8
                tbx = clamp(tbx, gx, gx + gw - tw)
                tby = clamp(tby, gy, gy + gh - th)
                pygame.draw.rect(cv, (24, 28, 40), (tbx, tby, tw, th), border_radius=6)
                pygame.draw.rect(cv, GOLD, (tbx, tby, tw, th), 1, border_radius=6)
                draw_text(cv, f"Total: {fmt(val)}", ui.F["xs"], TXT,
                          tbx + tw // 2, tby + th // 2, "center")
        else:
            draw_text(cv, "No hay suficientes datos históricos acumulados aún",
                      ui.F["md"], MUTED, gx + gw // 2, gy + gh // 2, "center")

        # Botón volver
        self.back_btn = pygame.Rect(px + pw // 2 - 90, py + ph - 60, 180, 42)
        hov = self.back_btn.collidepoint(mx, my)
        shiny_button(cv, self.back_btn, (28, 42, 64), ACCENT if hov else BORDER,
                     hover=hov, glow=0.8 if hov else 0.0, now=now, radius=10)
        draw_text(cv, "← VOLVER", ui.F["btn"], (235, 243, 255) if hov else TXT,
                  self.back_btn.centerx, self.back_btn.centery, "center")
