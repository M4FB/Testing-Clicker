"""Pruebas de Aceptación (ATDD — Acceptance Test Driven Development).

Validan los criterios de aceptación (AC-XX) de la versión actual (v1.0) desde
la perspectiva del usuario. Continúan la numeración del laboratorio:

  Núcleo (heredado y revalidado en v1.0)
    AC-01  Inicio del juego con estado limpio
    AC-02  Objetivo claro y medible
    AC-03  Interacción del jugador (clic)
    AC-04  Puntaje y progreso (generadores / mejoras)
    AC-05  Respuesta a eventos (críticos, boosts, fiebre dorada)
    AC-06  Mecánicas avanzadas (prestige + puntos de prestigio)
    AC-07  Condición de victoria

  Nuevo en v1.0
    AC-13  Logros
    AC-14  Guardado v2 y preferencias
    AC-15  Banda sonora procedural y gestor de audio
    AC-16  Menú principal, ajustes y estadísticas
"""
import time

import pygame
import pytest

from src.game import GameState
from src.config import (
    BOOST, GENERATORS, CLICK_UPGRADES, GEN_UPGRADES, PRESTIGE_UPGRADES,
    PRESTIGE_1_THRESHOLD, PRESTIGE_2_THRESHOLD, VICTORY_THRESHOLD,
    BASE_CLICK_VALUE, CRIT_MULT,
)


# ─────────────────────────────────────────────────────────────────────────────
class TestAC01_InicioJuego:
    """AC-01: el juego inicia con estado limpio y coherente."""

    def test_inicia_sin_puntos(self):
        g = GameState()
        assert g.points == 0.0 and g.total_points == 0.0

    def test_inicia_sin_generadores_ni_mejoras(self):
        g = GameState()
        assert all(c == 0 for c in g.generators.values())
        assert all(v is False for v in g.click_upgrades.values())

    def test_inicia_sin_prestige_ni_victoria(self):
        g = GameState()
        assert g.prestige_count == 0 and g.prestige_multiplier == 1.0
        assert g.won is False and g.infinite_mode is False

    def test_inicia_con_historial_vacio(self):
        assert GameState().stats["history"] == []


# ─────────────────────────────────────────────────────────────────────────────
class TestAC02_ObjetivoMedible:
    """AC-02: existe una meta medible y umbrales ordenados."""

    def test_umbrales_ordenados(self):
        assert PRESTIGE_1_THRESHOLD < PRESTIGE_2_THRESHOLD < VICTORY_THRESHOLD

    def test_progreso_es_porcentaje(self):
        g = GameState()
        g.total_points = PRESTIGE_1_THRESHOLD * BOOST / 2
        pct = g.prestige_progress_pct()
        assert 0.0 <= pct <= 100.0


# ─────────────────────────────────────────────────────────────────────────────
class TestAC03_Interaccion:
    """AC-03: el jugador interactúa mediante el clic."""

    def test_clic_suma_puntos(self):
        g = GameState(); g.crit_chance = 0.0
        earned, crit = g.click()
        assert crit is False and g.points == earned and g.stats["clicks"] == 1

    def test_clic_acumula_historico(self):
        g = GameState(); g.crit_chance = 0.0
        for _ in range(5):
            g.click()
        assert g.total_points == pytest.approx(g.click_value * 5)


# ─────────────────────────────────────────────────────────────────────────────
class TestAC04_PuntajeYProgreso:
    """AC-04: generadores y mejoras hacen progresar el puntaje."""

    def test_generador_produce_pps(self):
        g = GameState()
        g.points = g.generator_cost("worker")
        assert g.buy_generator("worker") is True
        assert g.pps() > 0.0

    def test_mejora_de_clic_sube_valor(self):
        g = GameState()
        g.points = g.click_upgrade_cost("cu_1")
        assert g.buy_click_upgrade("cu_1") is True
        assert g.click_value > BASE_CLICK_VALUE * BOOST

    def test_mejora_de_generador_multiplica(self):
        g = GameState()
        g.generators["worker"] = 1
        g.points = g.gen_upgrade_cost("gu_w1")
        base = g.pps()
        assert g.buy_gen_upgrade("gu_w1") is True
        assert g.pps() > base

    def test_tick_acumula_pasivo(self):
        g = GameState()
        g.generators["worker"] = 10
        g._last_tick = time.time() - 1.0
        assert g.tick() > 0.0


# ─────────────────────────────────────────────────────────────────────────────
class TestAC05_RespuestaEventos:
    """AC-05: el juego responde a eventos (críticos, boosts, fiebre)."""

    def test_critico_multiplica(self):
        g = GameState(); g.crit_chance = 1.0
        earned, crit = g.click()
        assert crit is True and earned == g.effective_click() * CRIT_MULT

    def test_boost_minijuego_multiplica_pps(self):
        g = GameState()
        g.generators["worker"] = 1
        base = g.pps()
        g.activate_minigame(multiplier=3.0, duration=60.0)
        assert g.pps() == pytest.approx(base * 3.0)

    def test_fiebre_dorada_caduca(self):
        g = GameState()
        g.activate_golden(multiplier=7.0, duration=0.01)
        assert g.golden_active is True
        time.sleep(0.02)
        g.tick()
        assert g.golden_active is False and g.golden_mult == 1.0


# ─────────────────────────────────────────────────────────────────────────────
class TestAC06_Prestige:
    """AC-06: prestige reinicia, multiplica y otorga puntos de prestigio."""

    def test_prestige1_reinicia_y_multiplica(self):
        g = GameState()
        g.total_points = PRESTIGE_1_THRESHOLD * BOOST
        g.points = 5000.0
        assert g.prestige() is True
        assert g.prestige_count == 1 and g.prestige_multiplier == 1.5
        assert g.points == 0.0 and g.prestige_points >= 2

    def test_prestige_bloqueado_sin_umbral(self):
        g = GameState()
        assert g.can_prestige() is False and g.prestige() is False

    def test_mejora_de_prestigio_permanente(self):
        g = GameState()
        g.prestige_points = 10
        assert g.buy_prestige_upgrade("pp_click") is True
        antes = g.perm_click_mult
        g.reapply_prestige_upgrades()        # sobrevive a recargar
        assert g.perm_click_mult == antes > 1.0


# ─────────────────────────────────────────────────────────────────────────────
class TestAC07_Victoria:
    """AC-07: la victoria requiere 2 prestiges + umbral y no se repite."""

    def _ganar(self):
        g = GameState()
        g.prestige_count = 2
        g.total_points = VICTORY_THRESHOLD * BOOST
        return g

    def test_victoria_se_declara(self):
        g = self._ganar()
        assert g.check_victory() is True
        assert g.won and g.infinite_mode

    def test_victoria_no_se_repite(self):
        g = self._ganar()
        g.check_victory()
        assert g.check_victory() is False

    def test_sin_prestiges_no_hay_victoria(self):
        g = GameState()
        g.total_points = VICTORY_THRESHOLD * BOOST * 5
        assert g.check_victory() is False


# ─────────────────────────────────────────────────────────────────────────────
class TestAC13_Logros:
    """AC-13 (v1.0): sistema de logros desbloqueables."""

    def test_primer_clic_desbloquea_logro(self):
        from src import achievements as ach
        g = GameState()
        g.stats["clicks"] = 1
        nuevos = ach.check(g)
        assert any(a["id"] == "primer_clic" for a in nuevos)
        assert g.achievements.get("primer_clic") is True

    def test_logro_no_se_desbloquea_dos_veces(self):
        from src import achievements as ach
        g = GameState()
        g.stats["clicks"] = 1
        ach.check(g)
        assert ach.check(g) == []                  # ya estaba desbloqueado

    def test_conteo_de_logros(self):
        from src import achievements as ach
        g = GameState()
        assert ach.unlocked_count(g) == 0
        g.stats["clicks"] = 1
        ach.check(g)
        assert ach.unlocked_count(g) == 1


# ─────────────────────────────────────────────────────────────────────────────
class TestAC14_GuardadoYPrefs:
    """AC-14 (v1.0): persistencia de partida (v2) y preferencias."""

    def test_round_trip_partida(self, tmp_save):
        from src import save as S
        g = GameState()
        g.points = 100.0; g.total_points = 500.0
        g.generators["worker"] = 3
        g.stats["history"] = [1.0, 2.0]
        S.save_game(g, elapsed=10.0, path=tmp_save)
        loaded, meta = S.load_game(path=tmp_save)
        assert loaded.generators["worker"] == 3
        assert loaded.stats["history"] == [1.0, 2.0]
        assert meta["version"] == S.SAVE_VERSION

    def test_prefs_persisten_y_se_recortan(self, tmp_prefs):
        from src import save as S
        S.save_prefs(music_vol=1.5, sfx_vol=0.3, fullscreen=True, path=tmp_prefs)
        prefs = S.load_prefs(path=tmp_prefs)
        assert prefs["music_vol"] == 1.0 and prefs["sfx_vol"] == 0.3
        assert prefs["fullscreen"] is True

    def test_save_incompatible_de_otro_modo(self, tmp_save):
        from src import save as S
        import json
        S.save_game(GameState(), path=tmp_save)
        with open(tmp_save) as fh:
            data = json.load(fh)
        data["mode"] = "otro_modo"
        with open(tmp_save, "w") as fh:
            json.dump(data, fh)
        assert S.has_compatible_save(path=tmp_save) is False


# ─────────────────────────────────────────────────────────────────────────────
class TestAC15_Audio:
    """AC-15 (v1.0): banda sonora procedural y gestor de audio."""

    def test_tres_pistas_distintas(self):
        from src import music as M
        g = M.generate_loop(); me = M.generate_menu_loop(); cf = M.generate_config_loop()
        assert len({g.shape[0], me.shape[0], cf.shape[0]}) == 3

    def test_variacion_reproducible_con_semilla(self):
        from src import music as M
        assert M.generate_menu_loop(seed=7).tobytes() == \
               M.generate_menu_loop(seed=7).tobytes()

    def test_gestor_crossfade_y_ducking(self):
        from src import music as M
        mgr = M.MusicManager(volume=0.6)
        mgr.play("menu"); assert mgr.current == "menu"
        mgr.play("game"); assert mgr.current == "game"
        mgr.duck(0.4)
        assert mgr._applied() < mgr.get_volume()
        mgr.unduck()
        assert mgr._applied() == mgr.get_volume()


# ─────────────────────────────────────────────────────────────────────────────
class TestAC16_MenuYAjustes:
    """AC-16 (v1.0): menú principal, ajustes y tarjeta de estadísticas."""

    def test_menu_ofrece_cuatro_acciones(self):
        from src.menu import MainMenu
        screen = pygame.display.get_surface()
        mm = MainMenu(screen)
        assert [b["action"] for b in mm.buttons] == \
               ["new", "cont", "settings", "quit"]

    def test_ajustes_cambian_y_persisten_volumen(self):
        from src import music as M
        from src.settings import SettingsScreen
        screen = pygame.display.get_surface()
        mgr = M.MusicManager(0.3)
        ss = SettingsScreen(screen, mgr)
        ss._set("music", 0.8)
        assert abs(mgr.get_volume() - 0.8) < 1e-9

    def test_estadisticas_registran_historial(self):
        from src.ui import GameUI
        screen = pygame.display.get_surface()
        ui = GameUI(screen=screen)
        ui._next_hist = time.time() - 1
        ui._update()
        assert len(ui.game.stats["history"]) == 1


# ─────────────────────────────────────────────────────────────────────────────
class TestAC17_CentroInvestigacion:
    """AC-17: El Centro de Investigación genera PPS de alta escala."""

    def test_research_center_unlocked_and_adds_pps(self):
        g = GameState()
        g.points = 200000 * BOOST
        g.total_points = 55000 * BOOST
        assert g.generator_unlocked("research")
        assert g.buy_generator("research")
        assert g.pps() == pytest.approx(50.0 * BOOST)


# ─────────────────────────────────────────────────────────────────────────────
class TestAC18_NuevasMejorasPrestige:
    """AC-18: Nuevas mejoras de prestigio (Auto-Clicker, Doble o Nada, Descuento)."""

    def test_prestige_autoclicker_effect(self):
        g = GameState()
        g.autoclick_rate = 1
        g.crit_chance = 0.0
        g._last_tick = time.time() - 2.5
        g.tick()
        assert g.stats["clicks"] == 2

    def test_prestige_double_crit_effect(self):
        g = GameState()
        g.crit_chance = 1.0
        g.double_crit_chance = 1.0
        earned, crit = g.click()
        assert crit
        assert earned == pytest.approx(g.effective_click() * 50.0)

    def test_prestige_price_discount_effect(self):
        g = GameState()
        g.price_scale = 1.12
        cost_discount = g.generator_cost("worker")
        g.price_scale = 1.15
        cost_normal = g.generator_cost("worker")
        assert cost_discount == cost_normal  # base price remains same for 0 owned
        # purchase one
        g.generators["worker"] = 1
        g.price_scale = 1.12
        cost_discount = g.generator_cost("worker")
        g.price_scale = 1.15
        cost_normal = g.generator_cost("worker")
        assert cost_discount < cost_normal


# ─────────────────────────────────────────────────────────────────────────────
class TestAC19_FiltroDSPAudiovisual:
    """AC-19: Filtro DSP de paso bajo en pausa."""

    def test_lowpass_audio_active_on_duck(self):
        from src import music as M
        mgr = M.MusicManager(volume=0.5)
        mgr.play("game")
        assert mgr.current == "game"
        # Duck triggers low-pass crossfade to muffled
        mgr.duck(0.4)
        assert mgr.current == "game_muffled"
        # Unduck returns to normal
        mgr.unduck()
        assert mgr.current == "game"


# ─────────────────────────────────────────────────────────────────────────────
class TestAC20_TemasVisualesYSkins:
    """AC-20: Cambios de tema visual y persistencia en preferencias."""

    def test_theme_persists_in_prefs(self, tmp_path):
        from src.save import load_prefs, save_prefs
        prefs_file = str(tmp_path / "prefs.json")
        save_prefs(theme="verde", path=prefs_file)
        loaded = load_prefs(path=prefs_file)
        assert loaded["theme"] == "verde"
