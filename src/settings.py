"""Pantalla de ajustes (accesible desde el menú principal).

Tiene su propia música ambiente (pista "config", distinta del menú y del
juego). Permite ajustar el volumen de música y de efectos y alternar pantalla
completa. Los cambios se aplican al instante y se guardan en las preferencias.
"""
import sys
import time

import pygame

from src.fx import (
    BG, BG2, BORDER, TXT, MUTED, ACCENT, GOLD, PURPLE, GREEN,
    draw_text, vgradient, Nebula, StarField, shiny_button, striped_bar,
)
from src.ui.common import (
    W, H, FPS, font, draw_panel, fade_in_alpha, fade_out,
    is_fullscreen, toggle_fullscreen,
)
from src.save import save_prefs
from src import sfx


class SettingsScreen:
    def __init__(self, screen: pygame.Surface,
                 music: "object | None" = None):
        self.screen = screen
        self.music  = music
        self.clock  = pygame.time.Clock()
        self.W, self.H = screen.get_width(), screen.get_height()

        self.f_title = font(34, bold=True)
        self.f_lbl   = font(17)
        self.f_val   = font(16, bold=True)
        self.f_btn   = font(18, bold=True)
        self.f_hint  = font(12)

        self.bg_grad = vgradient(self.W, self.H, BG, BG2)
        self.nebulas = [Nebula(self.W, self.H) for _ in range(3)]
        self.stars   = StarField(self.W, self.H, 90)

        cx = self.W // 2
        self.panel = pygame.Rect(cx - 240, 150, 480, 320)

        # Sliders: (clave, etiqueta, color, rect_de_pista)
        sx = self.panel.x + 150
        sw = 230
        self.sliders = {
            "music": {"label": "Música",  "color": ACCENT,
                      "rect": pygame.Rect(sx, self.panel.y + 70,  sw, 16)},
            "sfx":   {"label": "Sonidos", "color": PURPLE,
                      "rect": pygame.Rect(sx, self.panel.y + 120, sw, 16)},
        }
        self.full_rect = pygame.Rect(sx, self.panel.y + 168, 150, 34)
        self.back_rect = pygame.Rect(cx - 90, self.panel.bottom - 56, 180, 42)

        self._drag: str | None = None
        self._fade_in = time.time()

    # ── Valores actuales ────────────────────────────────────────────────────
    def _get(self, key) -> float:
        if key == "music":
            return self.music.get_volume() if self.music else 0.0
        return sfx.get_volume()

    def _set(self, key, v):
        v = max(0.0, min(1.0, v))
        if key == "music":
            if self.music:
                self.music.set_volume(v)
        else:
            sfx.set_volume(v)
            sfx.play("tick", 0.7)
        save_prefs(music_vol=self._get("music"), sfx_vol=self._get("sfx"))

    def _set_from_mouse(self, key, mx):
        r = self.sliders[key]["rect"]
        self._set(key, (mx - r.x) / max(1, r.width))

    # ── Loop ────────────────────────────────────────────────────────────────
    def run(self) -> None:
        if self.music:
            self.music.play("config")
        prev = time.time()
        while True:
            now  = time.time()
            dt   = min(0.05, now - prev)
            prev = now
            mx, my = pygame.mouse.get_pos()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                        return self._leave()
                    if event.key == pygame.K_F11:
                        self._toggle_full()
                    if event.key in (pygame.K_LEFT, pygame.K_RIGHT):
                        d = 0.05 if event.key == pygame.K_RIGHT else -0.05
                        self._set("music", self._get("music") + d)
                    if event.key in (pygame.K_UP, pygame.K_DOWN):
                        d = 0.05 if event.key == pygame.K_UP else -0.05
                        self._set("sfx", self._get("sfx") + d)
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.back_rect.collidepoint(mx, my):
                        return self._leave()
                    if self.full_rect.collidepoint(mx, my):
                        self._toggle_full()
                    for key, s in self.sliders.items():
                        if s["rect"].inflate(10, 18).collidepoint(mx, my):
                            self._drag = key
                            self._set_from_mouse(key, mx)
                if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    self._drag = None
                if event.type == pygame.MOUSEMOTION and self._drag:
                    self._set_from_mouse(self._drag, mx)

            for n in self.nebulas:
                n.update(dt)
            self.stars.update(dt)
            self._draw(mx, my, now)
            self.clock.tick(FPS)

    def _toggle_full(self):
        full = toggle_fullscreen()
        save_prefs(fullscreen=full)

    def _leave(self):
        fade_out(self.screen, self.clock, 0.25)
        if self.music:
            self.music.play("menu")
        return None

    # ── Dibujo ──────────────────────────────────────────────────────────────
    def _draw(self, mx, my, now):
        sc = self.screen
        sc.blit(self.bg_grad, (0, 0))
        for n in self.nebulas:
            n.draw(sc)
        self.stars.draw(sc)

        draw_text(sc, "AJUSTES", self.f_title, TXT, self.W // 2, 96, "center")
        draw_panel(sc, self.panel, color=(18, 22, 33), border=BORDER, radius=14)

        for key, s in self.sliders.items():
            r = s["rect"]
            draw_text(sc, s["label"], self.f_lbl, MUTED, r.x - 18, r.centery, "midright")
            val = self._get(key)
            striped_bar(sc, r, val, s["color"], now=now, radius=8)
            # tirador
            hx = r.x + int(r.width * val)
            pygame.draw.circle(sc, (235, 243, 255), (hx, r.centery), 8)
            pygame.draw.circle(sc, s["color"], (hx, r.centery), 8, 2)
            draw_text(sc, f"{int(val * 100)}%", self.f_val, TXT,
                      r.right + 18, r.centery, "midleft")

        # Toggle pantalla completa
        full = is_fullscreen()
        hov  = self.full_rect.collidepoint(mx, my)
        draw_text(sc, "Pantalla", self.f_lbl, MUTED,
                  self.full_rect.x - 18, self.full_rect.centery, "midright")
        shiny_button(sc, self.full_rect, (30, 40, 30) if full else (30, 34, 46),
                     GREEN if full else (ACCENT if hov else BORDER),
                     hover=hov, now=now, radius=9)
        draw_text(sc, "COMPLETA: ON" if full else "COMPLETA: OFF", self.f_val,
                  GREEN if full else TXT, self.full_rect.centerx,
                  self.full_rect.centery, "center")

        # Volver
        hov = self.back_rect.collidepoint(mx, my)
        shiny_button(sc, self.back_rect, (28, 42, 64), ACCENT if hov else BORDER,
                     hover=hov, glow=0.8 if hov else 0.0, now=now, radius=10)
        draw_text(sc, "← VOLVER", self.f_btn, (235, 243, 255) if hov else TXT,
                  self.back_rect.centerx, self.back_rect.centery, "center")

        draw_text(sc, "← → música    ↑ ↓ sonidos    F11 pantalla    ESC volver",
                  self.f_hint, MUTED, self.W // 2, self.H - 30, "center")

        a = fade_in_alpha(self._fade_in, 0.30)
        if a > 0:
            veil = pygame.Surface((self.W, self.H))
            veil.fill((0, 0, 0))
            veil.set_alpha(a)
            sc.blit(veil, (0, 0))
        pygame.display.flip()
