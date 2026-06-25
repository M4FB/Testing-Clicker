"""Cheat Table (mesa de trucos) — panel de depuración in-game.

Se activa con la variable de entorno CHEAT_TABLE=on (análoga a GAME_MODE).
Dentro de la partida, F1 abre/cierra el panel; cada botón fuerza un estado del
juego para enseñar o probar mecánicas sin tener que jugarlas:

    Puntos +50% victoria · Stats al 50% · Desbloquear mejoras · Generadores +25
    Dar 10 PP · Crítico garantizado · Fiebre dorada · Forzar minijuego
    Forzar QTE · Soltar moneda dorada · Prestigiar ya · Forzar victoria

No afecta al juego normal: si CHEATS está apagado, el panel no existe.
"""
import math
import random
import time

import pygame

from src.config import (
    CLICK_UPGRADES, GEN_UPGRADES, GENERATORS, BOOST, CRIT_CHANCE,
    VICTORY_THRESHOLD,
)
from src.fx import (
    BORDER, TXT, MUTED, ACCENT, GOLD, GREEN, RED, ORANGE, PURPLE,
    lerp_color, draw_text, shiny_button,
)
from src.ui.common import W, H, fmt
from src.ui.qte import QTE, QTE_KEY_SET


class CheatPanel:
    PW, PH = 500, 470

    def __init__(self, ui):
        self.ui = ui
        # (etiqueta, color, método)
        self.specs = [
            ("Puntos +50% victoria", GOLD,   self._points),
            ("Stats al 50%",         ACCENT, self._stats_half),
            ("Desbloquear mejoras",  GREEN,  self._unlock),
            ("Generadores +25",      GREEN,  self._gens),
            ("Dar 10 PP",            PURPLE, self._pp),
            ("Crítico garantizado",  GOLD,   self._crit),
            ("Fiebre dorada ×7",     ORANGE, self._fever),
            ("Forzar minijuego",     PURPLE, self._minigame),
            ("Forzar QTE",           ORANGE, self._qte),
            ("Soltar moneda dorada", GOLD,   self._golden),
            ("Prestigiar ya",        ACCENT, self._prestige),
            ("Forzar victoria",      RED,    self._endgame),
        ]
        self.rects: list[pygame.Rect] = []

    # ── Geometría ────────────────────────────────────────────────────────────
    def _layout(self):
        px, py = (W - self.PW) // 2, (H - self.PH) // 2
        bw, bh, gx, gy = 222, 40, 14, 10
        ox = px + (self.PW - (bw * 2 + gx)) // 2
        oy = py + 84
        self.rects = []
        for i in range(len(self.specs)):
            col, row = i % 2, i // 2
            self.rects.append(pygame.Rect(ox + col * (bw + gx),
                                          oy + row * (bh + gy), bw, bh))
        return px, py

    # ── Interacción ──────────────────────────────────────────────────────────
    def click(self, mx, my) -> bool:
        for r, (label, _c, fn) in zip(self.rects, self.specs):
            if r.collidepoint(mx, my):
                fn()
                return True
        return False

    # ── Cheats ───────────────────────────────────────────────────────────────
    def _toast(self, msg, color=GREEN):
        self.ui.toasts.add(f"⚙ {msg}", color, 2.4)

    def _points(self):
        g = self.ui.game
        amt = VICTORY_THRESHOLD * BOOST * 0.5
        g.points += amt
        g.total_points = max(g.total_points, g.points)
        self._toast(f"+{fmt(amt)} puntos", GOLD)

    def _stats_half(self):
        g = self.ui.game
        g.points = g.total_points = VICTORY_THRESHOLD * BOOST * 0.5
        s = g.stats
        s["clicks"]     = max(s["clicks"], 750)
        s["crits"]      = max(s["crits"], 25)
        s["best_combo"] = max(s["best_combo"], 30)
        s["golden"]     = max(s["golden"], 12)
        s["qte_won"]    = max(s["qte_won"], 5)
        s["mini_won"]   = max(s["mini_won"], 5)
        g.high_score    = max(g.high_score, g.total_points)
        self._toast("Stats al 50%", ACCENT)

    def _unlock(self):
        g = self.ui.game
        for u in CLICK_UPGRADES:
            if not g.click_upgrades.get(u["id"]):
                g.click_upgrades[u["id"]] = True
                g.click_value += u.get("bonus", 0) * BOOST
                g.click_mult  *= u.get("mult", 1.0)
        for u in GEN_UPGRADES:
            if not g.gen_upgrades.get(u["id"]):
                g.gen_upgrades[u["id"]] = True
                tgt = u["target"]
                g.gen_mult[tgt] = g.gen_mult.get(tgt, 1.0) * u["mult"]
        self._toast("Todas las mejoras desbloqueadas", GREEN)

    def _gens(self):
        for gen in GENERATORS:
            self.ui.game.generators[gen["id"]] += 25
        self._toast("+25 a cada generador", GREEN)

    def _pp(self):
        self.ui.game.prestige_points += 10
        self._toast("+10 puntos de prestigio", PURPLE)

    def _crit(self):
        g = self.ui.game
        if g.crit_chance < 1.0:
            g.crit_chance = 1.0
            self._toast("Crítico garantizado (×10)", GOLD)
        else:
            g.crit_chance = CRIT_CHANCE
            self._toast("Crítico restaurado", MUTED)

    def _fever(self):
        self.ui.game.activate_golden(7.0, 15.0)
        self.ui._golden_total = 15.0
        self._toast("Fiebre dorada ×7 (15s)", ORANGE)

    def _minigame(self):
        self.ui.cheats_open = False
        self.ui.mini_available = True
        self.ui._open_minigame()
        self._toast("Minijuego forzado", PURPLE)

    def _qte(self):
        keys = list(QTE_KEY_SET)
        random.shuffle(keys)
        self.ui.qte = QTE(sequence=keys[:8])
        self.ui.cheats_open = False
        self._toast("QTE forzado", ORANGE)

    def _golden(self):
        from src.events import GoldenCoin
        coin = GoldenCoin(W, H)
        coin.x, coin.base_y, coin.y = W * 0.30, H * 0.42, H * 0.42
        coin.vx = abs(coin.vx)
        self.ui.golden.coin = coin
        self.ui.cheats_open = False
        self._toast("Moneda dorada soltada", GOLD)

    def _prestige(self):
        g = self.ui.game
        if g.prestige_count >= 2:
            self._toast("Ya estás en el máximo prestigio", MUTED)
            return
        g.total_points = max(g.total_points, g.prestige_threshold())
        if g.prestige():
            self._toast(f"Prestige {g.prestige_count} forzado "
                        f"(×{g.prestige_multiplier:.1f})", ACCENT)

    def _endgame(self):
        g = self.ui.game
        g.prestige_count = 2
        g.prestige_multiplier = max(g.prestige_multiplier, 3.0)
        g.total_points = max(g.total_points, VICTORY_THRESHOLD * BOOST)
        g.points = max(g.points, g.total_points)
        self._toast("Endgame forzado — ¡victoria!", RED)

    # ── Dibujo ───────────────────────────────────────────────────────────────
    def draw(self, cv, mx, my):
        now = time.time()
        overlay = pygame.Surface((W, H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        cv.blit(overlay, (0, 0))

        px, py = self._layout()
        panel = pygame.Rect(px, py, self.PW, self.PH)
        pulse = 0.5 + 0.5 * math.sin(now * 3.0)
        pygame.draw.rect(cv, (24, 16, 22), panel, border_radius=14)
        pygame.draw.rect(cv, lerp_color(RED, ORANGE, pulse), panel, 2,
                         border_radius=14)

        draw_text(cv, "⚙  CHEAT TABLE", self.ui.F["big"],
                  lerp_color(RED, (255, 150, 120), pulse * 0.5),
                  panel.centerx, py + 26, "center")
        draw_text(cv, "Herramientas de depuración — fuerza estados del juego",
                  self.ui.F["xs"], MUTED, panel.centerx, py + 52, "center")

        for r, (label, color, _fn) in zip(self.rects, self.specs):
            hov = r.collidepoint(mx, my)
            shiny_button(cv, r, (30, 26, 34), color if hov else BORDER,
                         hover=hov, glow=0.7 if hov else 0.0, now=now, radius=9)
            draw_text(cv, label, self.ui.F["btn"],
                      (235, 243, 255) if hov else TXT,
                      r.centerx, r.centery, "center")

        draw_text(cv, "F1 / ESC para cerrar", self.ui.F["xs"], MUTED,
                  panel.centerx, panel.bottom - 16, "center")
