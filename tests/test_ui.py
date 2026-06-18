"""[TDD] Helpers de UI y humo de las pantallas (menú, ajustes, juego)."""
import time

import pygame
import pytest

from src.ui.common import fmt, fmt_time, fade_in_alpha, font


def test_fmt_scales():
    assert fmt(5) == "5.0"
    assert fmt(1500).endswith("K")
    assert fmt(2_500_000).endswith("M")
    assert fmt(3_000_000_000).endswith("B")


def test_fmt_time():
    assert fmt_time(75) == "01:15"
    assert fmt_time(3700).endswith("m")          # incluye horas


def test_fade_in_alpha_bounds():
    now = time.time()
    assert fade_in_alpha(now, 0.3) > 0           # justo al empezar
    assert fade_in_alpha(now - 10, 0.3) == 0     # ventana superada


def test_font_cached():
    a = font(20, bold=True)
    b = font(20, bold=True)
    assert a is b                                # cacheada por (size, bold)


def test_draw_sparkline_runs():
    from src.fx import draw_sparkline
    surf = pygame.Surface((200, 80))
    r = pygame.Rect(10, 10, 180, 60)
    draw_sparkline(surf, r, [1, 5, 3, 9, 7], now=0.0)   # varios puntos
    draw_sparkline(surf, r, [], now=0.0)                # vacío
    draw_sparkline(surf, r, [4], now=0.0)               # un punto
    draw_sparkline(surf, r, [2, 2, 2], now=0.0)         # span 0


def test_menu_smoke():
    from src.menu import MainMenu
    screen = pygame.display.get_surface()
    mm = MainMenu(screen)
    mm._fade_in = 0
    mm._draw(150, 310, time.time())
    assert [b["action"] for b in mm.buttons] == ["new", "cont", "settings", "quit"]


def test_settings_smoke():
    from src import music as M
    from src.settings import SettingsScreen
    screen = pygame.display.get_surface()
    mgr = M.MusicManager(0.4)
    ss = SettingsScreen(screen, mgr)
    ss._fade_in = 0
    ss._draw(ss.back_rect.centerx, ss.back_rect.centery, time.time())
    ss._set("music", 0.6)
    assert abs(mgr.get_volume() - 0.6) < 1e-9


def test_game_smoke_and_history():
    from src.ui import GameUI
    screen = pygame.display.get_surface()
    ui = GameUI(screen=screen)
    ui._next_hist = time.time() - 1
    ui._update()
    ui._draw()
    assert len(ui.game.stats["history"]) == 1
