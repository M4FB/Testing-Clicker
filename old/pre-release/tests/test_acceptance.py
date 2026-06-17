"""
Pruebas de Aceptación (ATDD — Acceptance Test Driven Development)  pre-release

Validan los requisitos de la nueva versión desde la perspectiva del usuario.
Continúan la numeración de la suite estable (AC-01 … AC-07):

  AC-08  Persistencia de partida (guardar / continuar)
  AC-09  Compra múltiple desde la interfaz (×1 / ×10 / MAX)
  AC-10  Minijuegos con recompensa proporcional al desempeño
  AC-11  Retroalimentación sonora
  AC-12  La interfaz gráfica responde y expone los controles
"""
import time

import pygame
import pytest

from src.game import GameState
from src.config import GENERATORS
from src import save as save_mod
from src import sfx
from src.fx import FX
from src.minigames import TargetRush, SimonPlus, PulseBar
from src.pygame_ui import GameUI

RECT = pygame.Rect(232, 120, 580, 440)


def _ui(**kw) -> GameUI:
    return GameUI(screen=pygame.display.get_surface(), **kw)


def _click():
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1)


# ─────────────────────────────────────────────────────────────────────────────
class TestAC08_PersistenciaDePartida:
    """
    AC-08: El progreso debe guardarse y poder continuarse en otra sesión.
    RF: Guardado de partida y botón CONTINUAR.
    """

    def test_guardar_y_continuar_restaura_el_progreso(self, tmp_path):
        """Una partida guardada se restaura con el mismo estado jugable."""
        path = str(tmp_path / "s.json")
        g = GameState()
        g.points = g.total_points = 70_000.0
        g.buy_generator_n("worker", 4)
        save_mod.save_game(g, elapsed=120.0, path=path)

        state, meta = save_mod.load_game(path=path)
        ui = _ui(state=state, elapsed=meta["elapsed"])
        assert ui.game.points == pytest.approx(g.points)
        assert ui.game.generators["worker"] == 4
        assert time.time() - ui.start_time >= 120.0

    def test_el_autoguardado_periodico_se_dispara(self, no_real_save):
        """El juego guarda solo, sin intervención del jugador."""
        ui = _ui()
        ui._next_autosave = 0.0
        ui._update()
        assert no_real_save, "el autoguardado no se ejecutó"
        assert "elapsed" in no_real_save[-1]

    def test_pausar_guarda_la_partida(self, no_real_save):
        """Abrir la pausa con ESC persiste el progreso."""
        ui = _ui()
        esc = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)
        ui._handle_events([esc], 0, 0)
        assert ui.paused
        assert no_real_save

    def test_menu_habilita_continuar_solo_con_guardado(self, monkeypatch):
        """El botón CONTINUAR refleja si existe partida compatible."""
        import src.menu as menu_mod
        screen = pygame.display.get_surface()

        monkeypatch.setattr(menu_mod, "has_compatible_save", lambda: False)
        sin_save = menu_mod.MainMenu(screen)
        assert [b["en"] for b in sin_save.buttons] == [True, False, True]

        monkeypatch.setattr(menu_mod, "has_compatible_save", lambda: True)
        con_save = menu_mod.MainMenu(screen)
        assert [b["en"] for b in con_save.buttons] == [True, True, True]

    def test_los_boosts_temporales_no_se_guardan(self, tmp_path):
        """Un boost activo no debe sobrevivir al cierre del juego."""
        path = str(tmp_path / "s.json")
        g = GameState()
        g.activate_minigame(3.0, 60.0)
        save_mod.save_game(g, path=path)
        g2, _ = save_mod.load_game(path=path)
        assert not g2.minigame_active
        assert g2.minigame_multiplier == pytest.approx(1.0)


# ─────────────────────────────────────────────────────────────────────────────
class TestAC09_CompraMultipleUI:
    """
    AC-09: El jugador puede comprar lotes de generadores desde la interfaz.
    RF: Toggles ×1 / ×10 / MAX en el panel de generadores.
    """

    def test_lote_de_10_desde_la_interfaz(self):
        ui = _ui()
        ui.game.points = ui.game.total_points = 1e6
        ui.buy_qty = 10
        ui._buy_generator(0)
        assert ui.game.generators["worker"] == 10

    def test_max_compra_todo_lo_posible(self):
        ui = _ui()
        ui.game.points = ui.game.total_points = 50_000
        esperado = ui.game.max_affordable_generators("worker")
        ui.buy_qty = "max"
        ui._buy_generator(0)
        assert ui.game.generators["worker"] == esperado
        assert ui.game.max_affordable_generators("worker") == 0

    def test_sin_fondos_no_compra_y_avisa(self):
        ui = _ui()
        ui.game.points = 0.0
        ui.buy_qty = 10
        ui._buy_generator(0)
        assert ui.game.generators["worker"] == 0
        assert any("Faltan" in t["msg"] for t in ui.toasts.items)

    def test_la_interfaz_expone_los_tres_toggles(self):
        ui = _ui()
        ui._update()
        ui._draw()
        valores = [v for _, v in ui._qty_rects]
        assert valores == [1, 10, "max"]

    def test_cambiar_cantidad_con_clic_en_el_toggle(self):
        ui = _ui()
        ui._update()
        ui._draw()
        rect_max = next(r for r, v in ui._qty_rects if v == "max")
        ui._handle_events([_click()], rect_max.centerx, rect_max.centery)
        assert ui.buy_qty == "max"


# ─────────────────────────────────────────────────────────────────────────────
class TestAC10_MinijuegosProporcionales:
    """
    AC-10: La recompensa de cada minijuego crece con el desempeño del jugador.
    RF: Minijuegos de habilidad con premio variable y mínimo exigible.
    """

    def _rush_con(self, score):
        mg = TargetRush(RECT, FX())
        mg.score = score
        mg.start = time.time() - mg.DURATION - 0.1
        mg.update(time.time(), 0.016)
        return mg

    def test_mejor_puntuacion_mayor_boost(self):
        assert self._rush_con(9).reward[0] > self._rush_con(4).reward[0]

    def test_todo_boost_esta_acotado_a_x3(self):
        assert self._rush_con(500).reward[0] <= 3.0

    def test_bajo_el_minimo_no_hay_premio(self):
        assert self._rush_con(2).reward is None

    def test_simon_parcial_premia_menos_que_completo(self):
        parcial = SimonPlus(RECT, FX())
        parcial.round = 1                       # falló tras 1 ronda completa
        parcial._fail(time.time())
        assert parcial.reward is not None
        assert parcial.reward[0] < 3.0          # 3.0 = premio por completarlo

    def test_pulso_la_precision_define_el_boost(self):
        perfecto, regular = PulseBar(RECT, FX()), PulseBar(RECT, FX())
        perfecto.bonus, regular.bonus = 1.8, 0.3
        perfecto._resolve()
        regular._resolve()
        assert perfecto.reward[0] > regular.reward[0]

    def test_la_recompensa_activa_el_boost_del_juego(self):
        """El premio del minijuego termina aplicado al GameState."""
        ui = _ui()
        mg = self._rush_con(8)
        mult_esperado = mg.reward[0]
        ui.mini = mg
        ui._mini_applied = False
        ui._update()
        assert ui.game.minigame_active
        assert ui.game.minigame_multiplier == pytest.approx(mult_esperado)


# ─────────────────────────────────────────────────────────────────────────────
class TestAC11_RetroalimentacionSonora:
    """
    AC-11: Las acciones del jugador producen una respuesta sonora.
    RF: Efectos de sonido procedurales con volumen ajustable.
    """

    def test_la_caja_de_sonidos_esta_completa(self):
        nombres = ["click0", "buy", "upgrade", "coin", "gem", "bomb", "error",
                   "tick", "win", "fail", "fanfare", "simon0", "simon3"]
        for n in nombres:
            assert len(sfx._build(n)) > 0, n

    def test_el_volumen_es_ajustable_y_acotado(self):
        previo = sfx.get_volume()
        sfx.set_volume(0.8)
        assert sfx.get_volume() == pytest.approx(0.8)
        sfx.set_volume(99)
        assert sfx.get_volume() == 1.0
        sfx.set_volume(previo)

    def test_en_silencio_no_se_reproduce_nada(self):
        previo = sfx.get_volume()
        sfx._reset_cache()
        sfx.set_volume(0.0)
        sfx.play("win")
        assert "win" not in sfx._cache
        sfx.set_volume(previo)

    def test_sin_audio_el_juego_sigue_funcionando(self):
        params = pygame.mixer.get_init()
        pygame.mixer.quit()
        try:
            sfx.play("fanfare")              # no debe lanzar excepción
            ui = _ui()
            ui._do_click(200, 300)           # acciones con sonido tampoco
            assert ui.game.points > 0
        finally:
            if params:
                pygame.mixer.init(frequency=params[0], size=params[1],
                                  channels=params[2], buffer=512)


# ─────────────────────────────────────────────────────────────────────────────
class TestAC12_InterfazResponde:
    """
    AC-12: La interfaz dibuja sus secciones y expone los controles interactivos.
    RF: Render estable del juego, minijuegos modales y pausa.
    """

    def test_un_frame_completo_se_dibuja_sin_errores(self):
        ui = _ui()
        ui._update()
        ui._draw()
        assert ui.canvas.get_size() == (1024, 680)
        assert ui._click_rect is not None
        assert ui._gen_rects[0] is not None      # worker comprable desde el inicio

    def test_panel_derecho_scrollable_con_todo_desbloqueado(self):
        ui = _ui()
        ui.game.points = ui.game.total_points = 1e12
        for gen in GENERATORS:                   # desbloquea los potenciadores
            ui.game.buy_generator_n(gen["id"], 10)
        ui._update()
        ui._draw()
        assert ui._right_max_scroll > 0

    def test_el_minijuego_abre_como_modal_y_se_dibuja(self):
        ui = _ui()
        ui.mini_available = True
        ui._open_minigame()
        assert ui.mini is not None
        assert not ui.mini_available
        ui._update()
        ui._draw()

    def test_escape_cancela_el_minijuego_sin_premio(self):
        ui = _ui()
        ui.mini_available = True
        ui._open_minigame()
        esc = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)
        ui._handle_events([esc], 0, 0)
        assert ui.mini is None
        assert not ui.game.minigame_active

    def test_la_pausa_se_dibuja_con_sus_tres_botones(self):
        ui = _ui()
        ui.paused = True
        ui._draw()
        assert ui._pause_resume_rect is not None
        assert ui._pause_menu_rect is not None
        assert ui._pause_quit_rect is not None

    def test_el_combo_se_acumula_con_clics_seguidos(self):
        ui = _ui()
        for _ in range(6):
            ui._do_click(200, 300)
        assert ui.combo == 6
