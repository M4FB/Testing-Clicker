"""[TDD] Unit tests for new features: research generator, new prestige upgrades, typing minigame, DSP lowpass filter and visual skins."""
import os
import time
import pytest
import numpy as np
import pygame

from src.game import GameState
from src.config import BOOST, GENERATORS
from src import config as C
from src import fx
from src import music as music_mod
from src.minigames import SpeedTypist
from src.save import load_prefs, save_prefs


# ── 1. TEST GENERADOR: CENTRO DE INVESTIGACIÓN ───────────────────────────────
def test_research_center_unlocked_and_cost():
    g = GameState()
    assert not g.generator_unlocked("research")
    g.total_points = 50000 * BOOST
    assert g.generator_unlocked("research")
    cost = g.generator_cost("research")
    assert cost == 130000 * BOOST


def test_research_center_buy_and_pps():
    g = GameState()
    g.points = 260000 * BOOST
    g.total_points = 50000 * BOOST
    assert g.buy_generator("research")
    assert g.generators["research"] == 1
    # Base pps is 50.0. Under BOOST=100, pps is 5000.0
    assert g.pps() == 50.0 * BOOST


# ── 2. TEST PRESTIGE UPGRADES ───────────────────────────────────────────────
def test_autoclicker_performs_clicks_in_tick():
    g = GameState()
    g.autoclick_rate = 5  # 5 clicks per second
    g.crit_chance = 0.0   # no crits for deterministic clicks
    g._last_tick = time.time()
    # Simulate 1 second passing
    time.sleep(0.25)
    g.tick()
    # Should have performed around 1 click
    assert g.stats["clicks"] > 0


def test_double_crit_multiplier():
    g = GameState()
    g.crit_chance = 1.0  # force crits
    g.double_crit_chance = 1.0  # force double crits
    earned, crit = g.click()
    assert crit
    expected_mult = C.CRIT_MULT * 5.0  # ×50 total
    assert earned == pytest.approx(g.effective_click() * expected_mult)


def test_price_discount_upgrade():
    g = GameState()
    g.points = 10000.0
    g.total_points = 10000.0
    
    # Base price scale
    assert g.price_scale == 1.15
    cost_base = g.generator_cost("worker")
    
    # Buy one worker
    g.buy_generator("worker")
    cost_after_base = g.generator_cost("worker")
    assert cost_after_base == pytest.approx(cost_base * 1.15)
    
    # Set price scale to 1.12 (discount)
    g.price_scale = 1.12
    cost_after_discount = g.generator_cost("worker")
    assert cost_after_discount == pytest.approx(cost_base * 1.12)
    assert cost_after_discount < cost_after_base


# ── 3. TEST MINIJUEGO: SPEED TYPIST ──────────────────────────────────────────
def test_speed_typist_typing_logic():
    rect = pygame.Rect(0, 0, 560, 440)
    typist = SpeedTypist(rect, None)
    word = typist.target_word
    
    # Press first correct key
    first_char = word[0]
    # Create mock key event
    event = pygame.event.Event(pygame.KEYDOWN, unicode=first_char, key=pygame.K_a)
    typist.event(event, 0, 0)
    assert typist.typed_word == first_char
    
    # Press incorrect key
    event_wrong = pygame.event.Event(pygame.KEYDOWN, unicode="Z" if first_char != "Z" else "Y", key=pygame.K_z)
    typist.event(event_wrong, 0, 0)
    # Incorrect key resets progress
    assert typist.typed_word == ""
    
    # Type full word correctly
    for char in word:
        event_char = pygame.event.Event(pygame.KEYDOWN, unicode=char, key=pygame.K_a)
        typist.event(event_char, 0, 0)
    
    assert typist.finished
    assert typist.reward == (2.0, 30.0)


# ── 4. TEST DSP LOW-PASS FILTER ──────────────────────────────────────────────
def test_dsp_lowpass_filter():
    # Create simple sine wave array of float
    t = np.linspace(0, 1.0, 44100, endpoint=False)
    # Stereo sine wave: high frequency (10000 Hz)
    sine = np.sin(2 * np.pi * 10000 * t)
    arr = np.column_stack([sine, sine])
    # Convert to int16
    int_arr = (arr * 30000).astype(np.int16)
    
    filtered = music_mod.lowpass_filter(int_arr, window=15)
    assert filtered.shape == int_arr.shape
    assert filtered.dtype == np.int16
    
    # Lowpass should reduce high frequency amplitude significantly
    orig_amplitude = np.max(np.abs(int_arr))
    filt_amplitude = np.max(np.abs(filtered))
    assert filt_amplitude < orig_amplitude * 0.5


# ── 5. TEST SKINS / TEMAS VISUALES ───────────────────────────────────────────
def test_visual_themes_loading_and_saving(tmp_path):
    prefs_file = str(tmp_path / "prefs.json")
    
    # Save a pref with rojo theme
    save_prefs(theme="rojo", path=prefs_file)
    prefs = load_prefs(path=prefs_file)
    assert prefs["theme"] == "rojo"
    
    # Switch theme
    fx.set_theme("verde")
    assert fx.ACTIVE_THEME == "verde"
    # Colors should match verde definition in fx.py
    assert fx.BG == (5, 5, 5)
    assert fx.ACCENT == (50, 220, 120)
    
    # Revert to base theme
    fx.set_theme("azul")
    assert fx.ACTIVE_THEME == "azul"


# ── 6. TEST GRÁFICO ESTADÍSTICO ──────────────────────────────────────────────
def test_stats_graph_overlay_drawing():
    from src.ui import GameUI
    from src.ui.overlays import StatsGraphOverlay
    screen = pygame.display.get_surface()
    ui = GameUI(screen=screen)
    # Rellenar historial con múltiples puntos para generar curva
    ui.game.stats["history"] = [100.0, 500.0, 1200.0, 4500.0]
    
    overlay = StatsGraphOverlay(ui)
    
    # Dibujar sin hover
    surf = pygame.Surface((1024, 680))
    overlay.draw(surf, mx=0, my=0)
    
    # Dibujar con hover en un punto (mx=402, my=480 corresponde a idx=1)
    overlay.draw(surf, mx=402, my=480)
    
    # Comprobar clicks
    assert not overlay.click(0, 0)
    assert overlay.click_outside(0, 0)
    assert not overlay.click_outside(122 + 10, 90 + 10)


# ── 7. TESTS ADICIONALES (MÁS COBERTURA) ─────────────────────────────────────
def test_autoclicker_rate_accumulation():
    g = GameState()
    g.autoclick_rate = 2  # 2 clics/segundo -> 1 clic cada 0.5s
    g.crit_chance = 0.0
    g.autoclick_timer = 0.0
    
    # Simular dt=0.25 (acumula 0.5 timer, 0 clics)
    g._last_tick = time.time() - 0.25
    g.tick()
    assert g.stats["clicks"] == 0
    assert g.autoclick_timer == pytest.approx(0.5, abs=1e-3)
    
    # Simular otro dt=0.3 (llega a 1.1 timer, realiza 1 clic, deja 0.1)
    g._last_tick = time.time() - 0.3
    g.tick()
    assert g.stats["clicks"] == 1
    assert g.autoclick_timer == pytest.approx(0.1, abs=1e-3)


def test_autoclicker_rate_zero():
    g = GameState()
    g.autoclick_rate = 0
    g._last_tick = time.time() - 10.0
    g.tick()
    assert g.stats["clicks"] == 0


def test_double_crit_chance_zero():
    g = GameState()
    g.crit_chance = 1.0
    g.double_crit_chance = 0.0
    earned, crit = g.click()
    assert crit
    assert earned == pytest.approx(g.effective_click() * C.CRIT_MULT)


def test_price_discount_upgrade_multiple():
    g = GameState()
    g.price_scale = 1.15
    g.generators["worker"] = 5
    cost_normal = g.generator_cost("worker")
    
    g.price_scale = 1.12
    cost_discount = g.generator_cost("worker")
    assert cost_discount < cost_normal


def test_speed_typist_special_keys():
    rect = pygame.Rect(0, 0, 560, 440)
    typist = SpeedTypist(rect, None)
    # Pulsar tecla de control sin unicode no debe resetear el progreso
    event_control = pygame.event.Event(pygame.KEYDOWN, unicode="", key=pygame.K_LSHIFT)
    typist.event(event_control, 0, 0)
    assert typist.typed_word == ""


def test_speed_typist_timeout():
    rect = pygame.Rect(0, 0, 560, 440)
    typist = SpeedTypist(rect, None)
    typist.update(typist.start + 10.0, 10.0)
    assert typist.finished
    assert typist.reward is None


def test_dsp_lowpass_filter_different_windows():
    t = np.linspace(0, 1.0, 44100, endpoint=False)
    sine = np.sin(2 * np.pi * 5000 * t)
    arr = np.column_stack([sine, sine])
    int_arr = (arr * 30000).astype(np.int16)
    
    filtered_small = music_mod.lowpass_filter(int_arr, window=5)
    filtered_large = music_mod.lowpass_filter(int_arr, window=25)
    
    amp_small = np.max(np.abs(filtered_small))
    amp_large = np.max(np.abs(filtered_large))
    assert amp_large < amp_small


def test_set_theme_invalid():
    fx.set_theme("azul")
    assert fx.ACTIVE_THEME == "azul"
    fx.set_theme("invalid_theme_name")
    assert fx.ACTIVE_THEME == "azul"


def test_save_prefs_merges_theme(tmp_path):
    prefs_file = str(tmp_path / "prefs.json")
    save_prefs(music_vol=0.7, theme="verde", path=prefs_file)
    save_prefs(theme="rojo", path=prefs_file)
    loaded = load_prefs(path=prefs_file)
    assert loaded["theme"] == "rojo"
    assert loaded["music_vol"] == pytest.approx(0.7)


def test_stats_graph_empty_history():
    from src.ui import GameUI
    from src.ui.overlays import StatsGraphOverlay
    screen = pygame.display.get_surface()
    ui = GameUI(screen=screen)
    ui.game.stats["history"] = []
    overlay = StatsGraphOverlay(ui)
    surf = pygame.Surface((1024, 680))
    overlay.draw(surf, mx=0, my=0)


def test_stats_graph_flat_history():
    from src.ui import GameUI
    from src.ui.overlays import StatsGraphOverlay
    screen = pygame.display.get_surface()
    ui = GameUI(screen=screen)
    ui.game.stats["history"] = [100.0, 100.0, 100.0]
    overlay = StatsGraphOverlay(ui)
    surf = pygame.Surface((1024, 680))
    overlay.draw(surf, mx=0, my=0)


def test_achievements_typing_minigame():
    from src import achievements as ach
    g = GameState()
    g.stats["mini"]["type"] = {"won": 1, "lost": 0, "best": 1.0}
    ach.check(g)
    assert g.achievements.get("todas_las_pistas") is None


