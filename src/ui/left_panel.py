"""Panel izquierdo: stats, progreso, botón de clic, prestige, minijuego y boosts."""
import math
import time

import pygame

from src.config import MINIGAME_COOLDOWN
from src.fx import (
    PANEL2, TXT, MUTED, ACCENT, GOLD, GOLD_D, GREEN, RED, ORANGE, PURPLE,
    clamp, lerp_color, ease_out, draw_text,
    shiny_button, striped_bar, draw_coin,
)
from src.ui.common import HDR_H, PAD, SPLIT, fmt, fmt_time, draw_panel


class LeftPanel:
    def __init__(self, ui):
        self.ui = ui
        self.click_rect:    pygame.Rect | None = None
        self.prestige_rect: pygame.Rect | None = None
        self.mini_rect:     pygame.Rect | None = None

    def draw(self, cv, mx, my):
        x0, y0 = PAD, HDR_H + PAD
        pw = SPLIT - PAD * 2
        y = y0
        y = self._stats_box(cv, x0, y, pw) + PAD
        y = self._progress(cv, x0, y, pw) + PAD
        y = self._click_button(cv, x0, y, pw, mx, my) + PAD
        y = self._prestige(cv, x0, y, pw, mx, my) + PAD
        y = self._minigame(cv, x0, y, pw, mx, my) + PAD
        self._booster_bars(cv, x0, y, pw)

    # ── Stats ────────────────────────────────────────────────────────────────
    def _stats_box(self, cv, x, y, w) -> int:
        ui, g = self.ui, self.ui.game
        now = time.time()
        rows = [
            ("Puntos",    fmt(ui.roll_points.v),        GOLD),
            ("PPS",       fmt(ui.roll_pps.v) + "/s",    ACCENT),
            ("Por clic",  fmt(g.effective_click()),     TXT),
            ("Crítico",   f"{g.crit_chance*100:.0f}% (×10)", ORANGE),
            ("Acumulado", fmt(g.total_points),          MUTED),
        ]
        if g.prestige_points > 0 or g.prestige_count > 0:
            rows.append(("PP", f"{g.prestige_points} ★", PURPLE))
        row_h = 24
        box_h = len(rows) * row_h + PAD * 2
        draw_panel(cv, pygame.Rect(x, y, w, box_h))
        draw_coin(cv, x + PAD + 8, y + PAD + 10, 9, now)
        ry = y + PAD
        for i, (label, value, color) in enumerate(rows):
            lx = x + PAD + (24 if i == 0 else 0)
            draw_text(cv, label + ":", ui.F["stat"], MUTED, lx, ry)
            draw_text(cv, value, ui.F["stat"], color, x + w - PAD, ry, "topright")
            ry += row_h
        return y + box_h

    # ── Progreso a prestige/victoria ─────────────────────────────────────────
    def _progress(self, cv, x, y, w) -> int:
        ui, g  = self.ui, self.ui.game
        now    = time.time()
        pct    = g.prestige_progress_pct() / 100.0
        labels = ["PRESTIGE 1", "PRESTIGE 2", "VICTORIA"]
        label  = labels[min(g.prestige_count, 2)]
        color  = ORANGE if g.prestige_count < 2 else GOLD
        draw_text(cv, f"→ {label}", ui.F["sm"], color, x, y)
        draw_text(cv, f"{pct*100:.1f}%", ui.F["sm"], MUTED, x + w, y, "topright")
        striped_bar(cv, pygame.Rect(x, y + 22, w, 14), pct, color, now=now, radius=6)
        return y + 40

    # ── Botón de clic ────────────────────────────────────────────────────────
    def _click_button(self, cv, x, y, w, mx, my) -> int:
        ui  = self.ui
        now = time.time()
        btn_h = 112
        rect  = pygame.Rect(x, y, w, btn_h)
        self.click_rect = rect
        hov    = rect.collidepoint(mx, my)
        shrink = int(ui.click_anim * 4)
        draw_r = rect.inflate(-shrink * 2, -shrink * 2)

        # El borde "se calienta" con el combo
        heat   = clamp((ui.combo - 5) / 40.0, 0, 1) \
                 if now - ui.last_click <= 0.9 else 0.0
        border = lerp_color(GREEN, ORANGE, heat)
        base   = (26, 56, 36) if not hov else (36, 76, 46)
        body   = lerp_color(base, (16, 38, 24), ui.click_anim)

        glow = 0.35 + 0.3 * math.sin(now * 2.4) + (0.5 if hov else 0.0) + heat * 0.4
        gs = pygame.Surface((draw_r.width + 28, draw_r.height + 28), pygame.SRCALPHA)
        for rad, a in ((10, 12), (6, 20), (3, 30)):
            pygame.draw.rect(gs, (*border, int(clamp(glow, 0, 1) * a)),
                             pygame.Rect(14 - rad, 14 - rad,
                                         draw_r.width + rad * 2, draw_r.height + rad * 2),
                             3, border_radius=14 + rad)
        cv.blit(gs, (draw_r.x - 14, draw_r.y - 14))

        pygame.draw.rect(cv, body, draw_r, border_radius=14)
        sh = pygame.Surface((max(1, draw_r.width - 8), draw_r.height // 2 - 4),
                            pygame.SRCALPHA)
        sh.fill((255, 255, 255, 18))
        cv.blit(sh, (draw_r.x + 4, draw_r.y + 3))
        pygame.draw.rect(cv, border, draw_r, 2, border_radius=14)

        # Ondas de clic
        clip = cv.get_clip()
        cv.set_clip(draw_r)
        for rp in ui.ripples:
            t = (now - rp["born"]) / 0.5
            if t >= 1:
                continue
            rr  = int(8 + ease_out(t) * 110)
            col = lerp_color(border, body, t)
            pygame.draw.circle(cv, col, (rp["x"], rp["y"]), rr, 2)
        cv.set_clip(clip)

        draw_coin(cv, draw_r.x + 52, draw_r.centery, 30, now, speed=2.0)
        bounce = math.sin(now * 3.2) * 2 + ui.click_anim * 3
        draw_text(cv, "¡ C L I C !", ui.F["click"], lerp_color(GREEN, GOLD, heat),
                  draw_r.centerx + 26, draw_r.centery - 10 + bounce, "center")
        draw_text(cv, f"+{fmt(ui.game.effective_click())} por clic   [ESPACIO]",
                  ui.F["xs"], MUTED,
                  draw_r.centerx + 26, draw_r.centery + 22, "center")

        if ui.combo >= 5 and now - ui.last_click <= 0.9:
            cc  = lerp_color(GREEN, RED, heat)
            wob = 1.0 + 0.08 * math.sin(now * 14)
            cs  = ui.F["btn"].render(f"COMBO ×{ui.combo}", True, cc)
            cs  = pygame.transform.rotozoom(cs, math.sin(now * 9) * 3, wob)
            cv.blit(cs, cs.get_rect(center=(draw_r.right - 64, draw_r.y + 18)))
        return y + btn_h

    # ── Prestige ─────────────────────────────────────────────────────────────
    def _prestige(self, cv, x, y, w, mx, my) -> int:
        ui, g = self.ui, self.ui.game
        now = time.time()
        btn_h = 40
        if g.can_prestige():
            rect = pygame.Rect(x, y, w, btn_h)
            self.prestige_rect = rect
            hov  = rect.collidepoint(mx, my)
            glow = 0.5 + 0.5 * math.sin(now * 3.0)
            shiny_button(cv, rect, (84, 58, 10), GOLD, hover=hov,
                         glow=glow, shine=True, now=now, radius=9)
            draw_text(cv, f"★  PRESTIGE {g.prestige_count+1}  "
                          f"(+{g.prestige_points_earned()} PP, "
                          f"{'×1.5' if g.prestige_count == 0 else '×2.0'})",
                      ui.F["btn"], GOLD, rect.centerx, rect.centery, "center")
        else:
            self.prestige_rect = None
            n = g.prestige_count + 1
            if n <= 2:
                draw_text(cv, f"Faltan {fmt(g.prestige_threshold()-g.total_points)} pts "
                              f"→ Prestige {n}", ui.F["sm"], MUTED, x, y + 12)
            else:
                draw_text(cv, "2 reinicios completados", ui.F["sm"], MUTED, x, y + 12)
        return y + btn_h

    # ── Minijuego ────────────────────────────────────────────────────────────
    def _minigame(self, cv, x, y, w, mx, my) -> int:
        ui, g = self.ui, self.ui.game
        now   = time.time()
        btn_h = 40

        if g.minigame_active:
            self.mini_rect = None
            left = g.minigame_seconds_left()
            bar  = pygame.Rect(x, y, w, btn_h)
            striped_bar(cv, bar, left / max(1.0, ui._boost_total),
                        (88, 48, 130), bg=(30, 18, 48), now=now, radius=9)
            pygame.draw.rect(cv, PURPLE, bar, 2, border_radius=9)
            draw_text(cv, f"★ BOOST ×{g.minigame_multiplier:.1f}  {left:.0f}s",
                      ui.F["btn"], (235, 220, 255), bar.centerx, bar.centery, "center")
        elif ui.mini_available:
            rect = pygame.Rect(x, y, w, btn_h)
            self.mini_rect = rect
            hov   = rect.collidepoint(mx, my)
            pulse = 0.5 + 0.5 * math.sin(now * 4.0)
            shiny_button(cv, rect, lerp_color((44, 30, 72), (60, 42, 98), pulse),
                         PURPLE, hover=hov, glow=pulse, shine=True, now=now, radius=9)
            label = "★  ELIGE TU MINIJUEGO  ★" if ui.can_select_minigame() \
                    else "★  MINIJUEGO DISPONIBLE  ★"
            draw_text(cv, label, ui.F["btn"], (230, 214, 255),
                      rect.centerx, rect.centery, "center")
        else:
            self.mini_rect = None
            cd   = max(0.0, ui.next_minigame - now)
            frac = 1.0 - cd / max(1.0, MINIGAME_COOLDOWN)
            draw_text(cv, f"Minijuego en {fmt_time(cd)}", ui.F["sm"], MUTED, x, y + 4)
            striped_bar(cv, pygame.Rect(x, y + 24, w, 9), frac, (70, 52, 110),
                        now=now, radius=4)
        return y + btn_h

    # ── Barras de boost extra (QTE / fiebre dorada) ─────────────────────────
    def _booster_bars(self, cv, x, y, w):
        ui, g = self.ui, self.ui.game
        now = time.time()
        if g.qte_bonus_active:
            left = g.qte_bonus_seconds_left()
            bar  = pygame.Rect(x, y, w, 30)
            striped_bar(cv, bar, left / max(1.0, ui._qte_total),
                        (70, 40, 120), bg=(24, 16, 44), now=now, radius=7)
            pygame.draw.rect(cv, PURPLE, bar, 2, border_radius=7)
            draw_text(cv, f"QTE ×3  {left:.0f}s", ui.F["xs"], (230, 214, 255),
                      bar.centerx, bar.centery, "center")
            y += 38
        if g.golden_active:
            left = g.golden_seconds_left()
            bar  = pygame.Rect(x, y, w, 30)
            striped_bar(cv, bar, left / max(1.0, ui._golden_total),
                        GOLD_D, bg=(40, 28, 8), now=now, radius=7)
            pygame.draw.rect(cv, GOLD, bar, 2, border_radius=7)
            draw_text(cv, f"☀ FIEBRE DORADA ×{g.golden_mult:.0f}  {left:.0f}s",
                      ui.F["xs"], (255, 240, 190),
                      bar.centerx, bar.centery, "center")
