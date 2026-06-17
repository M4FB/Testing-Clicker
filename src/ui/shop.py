"""Panel derecho scrollable: prestigio, generadores, potenciadores y mejoras."""
import math
import time

import pygame

from src.config import GENERATORS, CLICK_UPGRADES, GEN_UPGRADES, PRESTIGE_UPGRADES, BOOST
from src.fx import (
    PANEL, PANEL2, BORDER, TXT, MUTED, ACCENT, GOLD, GOLD_D, GREEN, RED,
    ORANGE, PURPLE,
    clamp, scale_color, draw_text, shiny_button,
)
from src.ui.common import W, H, HDR_H, STS_H, PAD, SPLIT, fmt, draw_panel


class ShopPanel:
    def __init__(self, ui):
        self.ui = ui
        self.scroll        = 0.0
        self.scroll_target = 0.0
        self.max_scroll    = 0

        self.qty_rects: list = []                       # [(rect, valor), ...]
        self.gen_rects:  list = [None] * len(GENERATORS)
        self.gu_rects:   list = [None] * len(GEN_UPGRADES)
        self.upg_rects:  list = [None] * len(CLICK_UPGRADES)
        self.pp_rects:   list = [None] * len(PRESTIGE_UPGRADES)

    # ── Input ────────────────────────────────────────────────────────────────
    def wheel(self, dy):
        self.scroll_target = clamp(self.scroll_target - dy * 42,
                                   0, self.max_scroll)

    def update(self, dt):
        self.scroll += (self.scroll_target - self.scroll) * clamp(dt * 14, 0, 1)

    def click(self, mx, my) -> bool:
        ui = self.ui
        for r, val in self.qty_rects:
            if r.collidepoint(mx, my):
                ui.set_buy_qty(val)
                return True
        for i, r in enumerate(self.pp_rects):
            if r and r.collidepoint(mx, my):
                ui.buy_prestige_upgrade(i)
                return True
        for i, r in enumerate(self.gen_rects):
            if r and r.collidepoint(mx, my):
                ui.buy_generator(i)
                return True
        for i, r in enumerate(self.gu_rects):
            if r and r.collidepoint(mx, my):
                ui.buy_gen_upgrade(i)
                return True
        for i, r in enumerate(self.upg_rects):
            if r and r.collidepoint(mx, my):
                ui.buy_upgrade(i)
                return True
        return False

    # ── Helpers de coordenadas con scroll ────────────────────────────────────
    def _sy(self, vy):
        return HDR_H + PAD + vy - int(self.scroll)

    def _row_visible(self, vy, rh):
        sy = self._sy(vy)
        return sy + rh > HDR_H and sy < H - STS_H

    def _separator(self, cv, x, pw, vy) -> int:
        vy += PAD
        sep = self._sy(vy)
        if HDR_H < sep < H - STS_H:
            pygame.draw.line(cv, BORDER, (x, sep), (x + pw, sep), 1)
        return vy + PAD + 1

    # ── Dibujo ───────────────────────────────────────────────────────────────
    def draw(self, cv, mx, my):
        x0 = SPLIT + PAD
        pw = W - SPLIT - PAD * 2

        clip = pygame.Rect(SPLIT + 1, HDR_H + 1, W - SPLIT - 2, H - HDR_H - STS_H - 2)
        cv.set_clip(clip)

        vy = 0
        if self._prestige_visible():
            vy = self._draw_prestige(cv, x0, vy, pw, mx, my)
            vy = self._separator(cv, x0, pw, vy)
        else:
            for i in range(len(PRESTIGE_UPGRADES)):
                self.pp_rects[i] = None
        vy = self._draw_generators(cv, x0, vy, pw, mx, my)
        vy = self._separator(cv, x0, pw, vy)
        vy = self._draw_gen_upgrades(cv, x0, vy, pw, mx, my)
        vy = self._separator(cv, x0, pw, vy)
        vy = self._draw_click_upgrades(cv, x0, vy, pw, mx, my)
        vy += PAD * 2

        cv.set_clip(None)

        visible_h = H - HDR_H - STS_H - PAD * 2
        self.max_scroll    = max(0, vy - visible_h)
        self.scroll_target = clamp(self.scroll_target, 0, self.max_scroll)

        if self.max_scroll > 0:
            panel_h = H - HDR_H - STS_H
            bar_h   = max(18, panel_h * panel_h // max(1, vy))
            bar_y   = HDR_H + int(self.scroll / self.max_scroll
                                  * (panel_h - bar_h))
            pygame.draw.rect(cv, MUTED, (W - 6, bar_y, 3, bar_h), border_radius=1)

    def _cost_button(self, cv, btn_r, label, can, mx, my, accent=GREEN):
        now = time.time()
        hov = btn_r.collidepoint(mx, my)
        base = (24, 64, 34) if can else (32, 24, 26)
        shiny_button(cv, btn_r, base, accent if can else RED,
                     hover=hov and can, shine=can, now=now, radius=7)
        draw_text(cv, label, self.ui.F["btn"], accent if can else RED,
                  btn_r.centerx, btn_r.centery, "center")

    # ── Sección: mejoras de prestigio ────────────────────────────────────────
    def _prestige_visible(self) -> bool:
        g = self.ui.game
        return g.prestige_count > 0 or g.prestige_points > 0 \
            or any(g.prestige_upgrades.values())

    def _draw_prestige(self, cv, x, vy, pw, mx, my) -> int:
        g = self.ui.game
        if self._row_visible(vy, 24):
            sy = self._sy(vy)
            draw_text(cv, "PRESTIGIO", self.ui.F["md"], PURPLE, x, sy)
            draw_text(cv, f"{g.prestige_points} PP ★", self.ui.F["btn"], PURPLE,
                      x + pw, sy, "topright")
        vy += 26
        row_h = 52; btn_w = 84; btn_h = 30; icon_s = 28

        for i, pu in enumerate(PRESTIGE_UPGRADES):
            self.pp_rects[i] = None
            bought = g.prestige_upgrades.get(pu["id"], False)
            if not self._row_visible(vy, row_h):
                vy += row_h
                continue
            sy   = self._sy(vy)
            rect = pygame.Rect(x, sy, pw, row_h - 3)
            can  = g.can_buy_prestige_upgrade(pu["id"])

            bg_c = (24, 18, 36) if bought else ((34, 26, 52) if can else PANEL)
            draw_panel(cv, rect, color=bg_c,
                       border=scale_color(PURPLE, 0.7) if can else BORDER)

            ix, iy = x + PAD, sy + (row_h - 3 - icon_s) // 2
            pygame.draw.rect(cv, (52, 36, 78) if not bought else (38, 28, 56),
                             (ix, iy, icon_s, icon_s), border_radius=6)
            draw_text(cv, pu["icon"], self.ui.F["sm"], (228, 215, 255),
                      ix + icon_s // 2, iy + icon_s // 2, "center")

            tx = ix + icon_s + 8
            draw_text(cv, pu["name"], self.ui.F["btn"],
                      MUTED if bought else TXT, tx, sy + 8)
            draw_text(cv, pu["desc"], self.ui.F["xs"], MUTED, tx, sy + 28)

            if bought:
                draw_text(cv, "✓", self.ui.F["btn"], PURPLE, x + pw - PAD - 20,
                          sy + (row_h - 3) // 2, "midleft")
            else:
                btn_r = pygame.Rect(x + pw - btn_w - PAD,
                                    sy + (row_h - 3 - btn_h) // 2, btn_w, btn_h)
                self.pp_rects[i] = btn_r
                self._cost_button(cv, btn_r, f"{pu['cost']} PP", can, mx, my,
                                  accent=PURPLE)
            vy += row_h
        return vy

    # ── Sección: generadores ─────────────────────────────────────────────────
    def _draw_generators(self, cv, x, vy, pw, mx, my) -> int:
        ui = self.ui
        self.qty_rects = []
        if self._row_visible(vy, 24):
            sy = self._sy(vy)
            draw_text(cv, "GENERADORES", ui.F["md"], TXT, x, sy)
            bw, bh, gap = 46, 22, 6
            bx0 = x + pw - 3 * bw - 2 * gap
            for j, (lab, val) in enumerate([("×1", 1), ("×10", 10), ("MAX", "max")]):
                r      = pygame.Rect(bx0 + j * (bw + gap), sy - 1, bw, bh)
                active = ui.buy_qty == val
                hov    = r.collidepoint(mx, my)
                base   = (38, 52, 76) if active else ((28, 34, 48) if hov else (22, 27, 38))
                pygame.draw.rect(cv, base, r, border_radius=6)
                pygame.draw.rect(cv, ACCENT if active else BORDER, r,
                                 2 if active else 1, border_radius=6)
                draw_text(cv, lab, ui.F["xs"], ACCENT if active else MUTED,
                          r.centerx, r.centery, "center")
                self.qty_rects.append((r, val))
        vy += 26
        row_h = 70; btn_w = 130; btn_h = 32

        for i, gen in enumerate(GENERATORS):
            if not self._row_visible(vy, row_h):
                self.gen_rects[i] = None
                vy += row_h
                continue
            sy     = self._sy(vy)
            rect   = pygame.Rect(x, sy, pw, row_h - 4)
            locked = not ui.game.generator_unlocked(gen["id"])
            if locked:
                draw_panel(cv, rect, color=(15, 19, 28))
                # Candado dibujado (la fuente del sistema no trae emoji)
                lx, ly = x + PAD + 7, sy + 16
                pygame.draw.arc(cv, MUTED, (lx - 5, ly - 2, 10, 12), 0, math.pi, 2)
                pygame.draw.rect(cv, MUTED, (lx - 7, ly + 4, 14, 11), border_radius=3)
                draw_text(cv, "???", ui.F["md"], MUTED, lx + 14, sy + 12)
                draw_text(cv, f"Desbloquea a {fmt(gen['unlock'] * BOOST)} pts acumulados",
                          ui.F["xs"], (70, 78, 92), x + PAD, sy + 38)
                self.gen_rects[i] = None
            else:
                g     = ui.game
                owned = g.generators[gen["id"]]
                if ui.buy_qty == "max":
                    n_buy   = max(1, g.max_affordable_generators(gen["id"]))
                    can_buy = g.max_affordable_generators(gen["id"]) >= 1
                else:
                    n_buy   = ui.buy_qty
                    can_buy = g.points >= g.generator_cost_n(gen["id"], n_buy)
                cost  = g.generator_cost_n(gen["id"], n_buy)
                pps_r = (gen["pps"] * g.prestige_multiplier * g.perm_pps_mult * BOOST
                         * g.gen_mult.get(gen["id"], 1.0)
                         * g.gen_mult.get("all", 1.0))
                draw_panel(cv, rect, color=(24, 32, 44) if can_buy else PANEL,
                           border=scale_color(GREEN, 0.55) if can_buy else BORDER)
                draw_text(cv, gen["name"], ui.F["md"], TXT, x + PAD, sy + 10)
                draw_text(cv, f"×{owned}", ui.F["md"],
                          ACCENT if owned > 0 else MUTED, x + PAD + 132, sy + 10)
                pps_str = f"+{fmt(pps_r * owned)}/s" if owned > 0 else f"{fmt(pps_r)}/s c/u"
                draw_text(cv, pps_str, ui.F["xs"], MUTED, x + PAD, sy + 36)

                # Mini-barra de ahorro hacia el coste
                if not can_buy:
                    frac = clamp(ui.game.points / max(1, cost), 0, 1)
                    mini = pygame.Rect(x + PAD, sy + row_h - 14, pw - btn_w - PAD * 3, 4)
                    pygame.draw.rect(cv, PANEL2, mini, border_radius=2)
                    if frac > 0:
                        f = mini.copy(); f.width = max(2, int(mini.width * frac))
                        pygame.draw.rect(cv, GOLD_D, f, border_radius=2)

                btn_r = pygame.Rect(x + pw - btn_w - PAD,
                                    sy + (row_h - 4 - btn_h) // 2, btn_w, btn_h)
                self.gen_rects[i] = btn_r
                self._cost_button(cv, btn_r, fmt(cost), can_buy, mx, my)
                if n_buy > 1:
                    draw_text(cv, f"compra ×{n_buy}", ui.F["xs"],
                              GREEN if can_buy else MUTED,
                              btn_r.centerx, btn_r.y - 3, "midbottom")
            vy += row_h
        return vy

    # ── Sección: potenciadores de generadores ────────────────────────────────
    def _draw_gen_upgrades(self, cv, x, vy, pw, mx, my) -> int:
        ui = self.ui
        if self._row_visible(vy, 24):
            draw_text(cv, "POTENCIADORES", ui.F["md"], TXT, x, self._sy(vy))
        vy += 26
        row_h = 48; btn_w = 110; btn_h = 30; icon_s = 28

        visible = [i for i, gu in enumerate(GEN_UPGRADES)
                   if ui.game.gen_upgrades.get(gu["id"])
                   or ui.game.gen_upgrade_unlocked(gu["id"])]
        for i in range(len(GEN_UPGRADES)):
            self.gu_rects[i] = None
        if not visible:
            if self._row_visible(vy, 22):
                draw_text(cv, "Compra generadores para desbloquear", ui.F["xs"],
                          MUTED, x + PAD, self._sy(vy))
            return vy + 22

        for idx in visible:
            gu     = GEN_UPGRADES[idx]
            bought = ui.game.gen_upgrades.get(gu["id"], False)
            if not self._row_visible(vy, row_h):
                vy += row_h
                continue
            sy   = self._sy(vy)
            rect = pygame.Rect(x, sy, pw, row_h - 3)
            cost = ui.game.gen_upgrade_cost(gu["id"])
            can  = ui.game.can_buy_gen_upgrade(gu["id"])

            bg_c = (15, 19, 28) if bought else ((24, 32, 44) if can else PANEL)
            draw_panel(cv, rect, color=bg_c,
                       border=scale_color(ORANGE, 0.55) if can else BORDER)

            icon_c = (62, 46, 14) if bought else \
                     ((52, 38, 10) if gu["target"] == "all" else (28, 46, 72))
            ix, iy = x + PAD, sy + (row_h - 3 - icon_s) // 2
            pygame.draw.rect(cv, icon_c, (ix, iy, icon_s, icon_s), border_radius=6)
            draw_text(cv, gu["icon"], ui.F["sm"], (225, 225, 230),
                      ix + icon_s // 2, iy + icon_s // 2, "center")

            tx = ix + icon_s + 8
            draw_text(cv, gu["name"], ui.F["btn"], MUTED if bought else TXT, tx, sy + 8)
            tgt = next((g["name"] for g in GENERATORS if g["id"] == gu["target"]), "Todos")
            draw_text(cv, f"×{gu['mult']:.1f}  {tgt}", ui.F["xs"], MUTED, tx, sy + 28)

            if bought:
                draw_text(cv, "✓", ui.F["btn"], GREEN, x + pw - PAD - 20,
                          sy + (row_h - 3) // 2, "midleft")
            else:
                btn_r = pygame.Rect(x + pw - btn_w - PAD,
                                    sy + (row_h - 3 - btn_h) // 2, btn_w, btn_h)
                self.gu_rects[idx] = btn_r
                self._cost_button(cv, btn_r, fmt(cost), can, mx, my, accent=ORANGE)
            vy += row_h
        return vy

    # ── Sección: mejoras de clic ─────────────────────────────────────────────
    def _draw_click_upgrades(self, cv, x, vy, pw, mx, my) -> int:
        ui = self.ui
        if self._row_visible(vy, 24):
            draw_text(cv, "MEJORAS DE CLIC", ui.F["md"], TXT, x, self._sy(vy))
        vy += 26
        row_h = 48; btn_w = 110; btn_h = 30; icon_s = 28

        for i in range(len(CLICK_UPGRADES)):
            self.upg_rects[i] = None

        for i, upg in enumerate(CLICK_UPGRADES):
            if not ui.game.click_upgrade_unlocked(upg["id"]):
                continue
            bought = ui.game.click_upgrades[upg["id"]]
            if not self._row_visible(vy, row_h):
                vy += row_h
                continue
            sy   = self._sy(vy)
            rect = pygame.Rect(x, sy, pw, row_h - 3)
            cost = ui.game.click_upgrade_cost(upg["id"])
            can  = not bought and ui.game.points >= cost

            bg_c = (15, 19, 28) if bought else ((24, 32, 44) if can else PANEL)
            draw_panel(cv, rect, color=bg_c,
                       border=scale_color(GREEN, 0.55) if can else BORDER)

            has_mult = upg.get("mult", 1.0) != 1.0
            icon_c   = (62, 46, 14) if has_mult else (28, 46, 72)
            ix, iy   = x + PAD, sy + (row_h - 3 - icon_s) // 2
            pygame.draw.rect(cv, icon_c, (ix, iy, icon_s, icon_s), border_radius=6)
            draw_text(cv, upg["icon"], ui.F["sm"], (225, 225, 230),
                      ix + icon_s // 2, iy + icon_s // 2, "center")

            tx = ix + icon_s + 8
            draw_text(cv, upg["name"], ui.F["btn"], MUTED if bought else TXT, tx, sy + 8)
            bonus, mult = upg.get("bonus", 0), upg.get("mult", 1.0)
            parts = []
            if bonus:       parts.append(f"+{fmt(bonus*BOOST)}")
            if mult != 1.0: parts.append(f"×{mult:.1f} clic")
            draw_text(cv, "  ".join(parts) or "—", ui.F["xs"], MUTED, tx, sy + 28)

            if bought:
                draw_text(cv, "✓", ui.F["btn"], GREEN, x + pw - PAD - 20,
                          sy + (row_h - 3) // 2, "midleft")
            else:
                btn_r = pygame.Rect(x + pw - btn_w - PAD,
                                    sy + (row_h - 3 - btn_h) // 2, btn_w, btn_h)
                self.upg_rects[i] = btn_r
                self._cost_button(cv, btn_r, fmt(cost), can, mx, my)
            vy += row_h
        return vy
