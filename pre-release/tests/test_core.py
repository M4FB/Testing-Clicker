"""
Pruebas TDD — unitarias de las mecánicas nuevas del pre-release:
compra múltiple, guardado/carga, efectos de sonido y lógica de minijuegos.
"""
import json
import math
import os
import time

import pygame
import pytest

from src.game import GameState
from src.config import GENERATORS, PRICE_SCALE, BOOST, MODE
from src import save as save_mod
from src import sfx
from src.fx import FX
from src.minigames import TargetRush, GoldRain, SimonPlus, PulseBar, MINIGAMES

RECT = pygame.Rect(232, 120, 580, 440)


# ── Helpers ──────────────────────────────────────────────────────────────────

def game_with_points(pts: float) -> GameState:
    g = GameState()
    g.points = pts
    g.total_points = pts
    return g


def click_event():
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1)


# ═══════════════════════════════════════════════════════════════════════════════
# Compra múltiple
# ═══════════════════════════════════════════════════════════════════════════════

class TestCompraMultiple:

    def test_coste_lote_de_1_igual_al_coste_unitario(self):
        g = GameState()
        assert g.generator_cost_n("worker", 1) == g.generator_cost("worker")

    def test_coste_lote_es_suma_de_costes_escalados(self):
        g = GameState()
        esperado = sum(math.ceil(15 * PRICE_SCALE ** i * BOOST) for i in range(10))
        assert g.generator_cost_n("worker", 10) == esperado

    def test_coste_lote_parte_de_las_unidades_ya_compradas(self):
        g = game_with_points(1e12)
        g.buy_generator_n("worker", 5)
        esperado = sum(math.ceil(15 * PRICE_SCALE ** (5 + i) * BOOST)
                       for i in range(3))
        assert g.generator_cost_n("worker", 3) == esperado

    def test_max_affordable_cero_sin_fondos(self):
        g = GameState()
        assert g.max_affordable_generators("worker") == 0

    def test_max_affordable_frontera_exacta(self):
        g = GameState()
        g.points = g.total_points = float(g.generator_cost_n("worker", 4))
        assert g.max_affordable_generators("worker") == 4

    def test_max_affordable_generador_bloqueado_es_cero(self):
        g = GameState()
        g.points = 1e12          # fondos de sobra pero sin acumulado: bloqueado
        assert g.max_affordable_generators("lab") == 0

    def test_max_affordable_respeta_el_tope(self):
        g = game_with_points(1e30)
        assert g.max_affordable_generators("worker") == 200

    def test_buy_n_compra_y_descuenta_el_coste_exacto(self):
        g = game_with_points(1e6)
        antes = g.points
        coste = g.generator_cost_n("worker", 10)
        assert g.buy_generator_n("worker", 10) == 10
        assert g.generators["worker"] == 10
        assert g.points == pytest.approx(antes - coste)

    def test_buy_n_parcial_al_agotar_fondos(self):
        g = GameState()
        g.points = g.total_points = float(g.generator_cost_n("worker", 3))
        assert g.buy_generator_n("worker", 10) == 3
        assert g.generators["worker"] == 3

    def test_buy_n_equivale_a_compras_individuales(self):
        ga, gb = game_with_points(1e6), game_with_points(1e6)
        ga.buy_generator_n("worker", 7)
        for _ in range(7):
            gb.buy_generator("worker")
        assert ga.points == pytest.approx(gb.points)
        assert ga.generators == gb.generators


# ═══════════════════════════════════════════════════════════════════════════════
# Guardado / carga
# ═══════════════════════════════════════════════════════════════════════════════

class TestGuardado:

    def _estado_avanzado(self) -> GameState:
        g = game_with_points(100_000)
        g.buy_generator_n("worker", 3)
        g.buy_click_upgrade("cu_1")
        g.buy_gen_upgrade("gu_g1")
        g.prestige_count = 1
        g.prestige_multiplier = 1.5
        g.high_score = 99_999.0
        return g

    def test_roundtrip_conserva_escalares(self, tmp_path):
        path = str(tmp_path / "s.json")
        g = self._estado_avanzado()
        save_mod.save_game(g, path=path)
        g2, _ = save_mod.load_game(path=path)
        assert g2.points == pytest.approx(g.points)
        assert g2.total_points == pytest.approx(g.total_points)
        assert g2.prestige_multiplier == pytest.approx(1.5)
        assert g2.high_score == pytest.approx(99_999.0)

    def test_roundtrip_conserva_generadores_y_mejoras(self, tmp_path):
        path = str(tmp_path / "s.json")
        g = self._estado_avanzado()
        save_mod.save_game(g, path=path)
        g2, _ = save_mod.load_game(path=path)
        assert g2.generators == g.generators
        assert g2.click_upgrades == g.click_upgrades
        assert g2.gen_upgrades == g.gen_upgrades
        assert g2.gen_mult == g.gen_mult

    def test_roundtrip_produce_el_mismo_pps(self, tmp_path):
        path = str(tmp_path / "s.json")
        g = self._estado_avanzado()
        save_mod.save_game(g, path=path)
        g2, _ = save_mod.load_game(path=path)
        assert g2.pps() == pytest.approx(g.pps())

    def test_metadatos_incluyen_tiempo_modo_y_volumenes(self, tmp_path):
        path = str(tmp_path / "s.json")
        save_mod.save_game(GameState(), elapsed=123.0,
                           music_vol=0.3, sfx_vol=0.7, path=path)
        _, meta = save_mod.load_game(path=path)
        assert meta["elapsed"] == pytest.approx(123.0)
        assert meta["mode"] == MODE
        assert meta["music_vol"] == pytest.approx(0.3)
        assert meta["sfx_vol"] == pytest.approx(0.7)

    def test_sin_archivo_no_hay_partida(self, tmp_path):
        path = str(tmp_path / "no_existe.json")
        assert not save_mod.has_compatible_save(path=path)
        assert save_mod.load_game(path=path) == (None, {})

    def test_archivo_corrupto_no_revienta(self, tmp_path):
        path = str(tmp_path / "s.json")
        with open(path, "w") as fh:
            fh.write("{esto no es json")
        assert not save_mod.has_compatible_save(path=path)
        assert save_mod.load_game(path=path) == (None, {})

    def test_guardado_de_otro_modo_es_incompatible(self, tmp_path):
        path = str(tmp_path / "s.json")
        save_mod.save_game(GameState(), path=path)
        with open(path) as fh:
            data = json.load(fh)
        data["mode"] = "full" if MODE == "demo" else "demo"
        with open(path, "w") as fh:
            json.dump(data, fh)
        assert not save_mod.has_compatible_save(path=path)
        assert save_mod.load_game(path=path) == (None, {})

    def test_claves_desconocidas_se_ignoran(self, tmp_path):
        """Si la config cambia entre versiones, el load no debe romperse."""
        path = str(tmp_path / "s.json")
        save_mod.save_game(GameState(), path=path)
        with open(path) as fh:
            data = json.load(fh)
        data["generators"]["generador_fantasma"] = 99
        with open(path, "w") as fh:
            json.dump(data, fh)
        g2, _ = save_mod.load_game(path=path)
        assert g2 is not None
        assert "generador_fantasma" not in g2.generators

    def test_borrar_es_idempotente(self, tmp_path):
        path = str(tmp_path / "s.json")
        save_mod.save_game(GameState(), path=path)
        save_mod.delete_save(path=path)
        save_mod.delete_save(path=path)      # segunda vez: no debe fallar
        assert not os.path.exists(path)

    def test_no_deja_archivo_temporal(self, tmp_path):
        path = str(tmp_path / "s.json")
        save_mod.save_game(GameState(), path=path)
        assert not os.path.exists(path + ".tmp")


# ═══════════════════════════════════════════════════════════════════════════════
# Efectos de sonido
# ═══════════════════════════════════════════════════════════════════════════════

SFX_NAMES = ["click0", "click1", "click2", "buy", "upgrade", "coin", "gem",
             "bomb", "error", "tick", "win", "fail", "fanfare",
             "simon0", "simon1", "simon2", "simon3"]


class TestSfx:

    @pytest.mark.parametrize("name", SFX_NAMES)
    def test_cada_sonido_se_sintetiza(self, name):
        arr = sfx._build(name)
        assert len(arr) > 0

    def test_nombre_desconocido_lanza_keyerror(self):
        with pytest.raises(KeyError):
            sfx._build("inexistente")

    def test_to_sound_produce_un_sound_reproducible(self):
        if not pygame.mixer.get_init():
            pytest.skip("mixer no disponible")
        snd = sfx._to_sound(sfx._build("buy"))
        assert snd.get_length() > 0.02

    def test_play_cachea_el_sonido(self):
        if not pygame.mixer.get_init():
            pytest.skip("mixer no disponible")
        sfx._reset_cache()
        sfx.set_volume(0.5)
        sfx.play("buy")
        assert "buy" in sfx._cache
        antes = sfx._cache["buy"]
        sfx.play("buy")
        assert sfx._cache["buy"] is antes

    def test_volumen_se_acota_a_0_1(self):
        previo = sfx.get_volume()
        sfx.set_volume(5.0)
        assert sfx.get_volume() == 1.0
        sfx.set_volume(-3.0)
        assert sfx.get_volume() == 0.0
        sfx.set_volume(previo)

    def test_volumen_cero_no_sintetiza_nada(self):
        previo = sfx.get_volume()
        sfx._reset_cache()
        sfx.set_volume(0.0)
        sfx.play("fanfare")
        assert "fanfare" not in sfx._cache
        sfx.set_volume(previo)

    def test_play_sin_mixer_es_noop(self):
        params = pygame.mixer.get_init()
        pygame.mixer.quit()
        try:
            sfx.play("click")        # no debe lanzar excepción
        finally:
            if params:
                pygame.mixer.init(frequency=params[0], size=params[1],
                                  channels=params[2], buffer=512)


# ═══════════════════════════════════════════════════════════════════════════════
# Lógica de minijuegos
# ═══════════════════════════════════════════════════════════════════════════════

def _gold(x=300, y=300, life=9.0):
    return {"x": x, "y": y, "r0": 30, "born": time.time(), "life": life,
            "kind": "gold"}


def _bomb(x=300, y=300):
    d = _gold(x, y)
    d["kind"] = "bomb"
    return d


class TestTargetRush:

    def test_hay_cuatro_minijuegos_registrados(self):
        assert len(MINIGAMES) == 4

    def test_clic_en_moneda_suma(self):
        mg = TargetRush(RECT, FX())
        mg.targets.append(_gold())
        mg.event(click_event(), 300, 300)
        assert mg.score == 1
        assert not mg.targets

    def test_clic_en_bomba_resta_sin_bajar_de_cero(self):
        mg = TargetRush(RECT, FX())
        mg.targets.append(_bomb())
        mg.event(click_event(), 300, 300)
        assert mg.score == 0

    def test_clic_fuera_del_objetivo_no_hace_nada(self):
        mg = TargetRush(RECT, FX())
        mg.targets.append(_gold(300, 300))
        mg.event(click_event(), 500, 500)
        assert mg.score == 0 and len(mg.targets) == 1

    def test_el_objetivo_encoge_con_la_edad(self):
        mg = TargetRush(RECT, FX())
        tg = _gold(life=1.0)
        r_nuevo = mg._radius(tg, tg["born"] + 0.2)
        r_viejo = mg._radius(tg, tg["born"] + 0.9)
        assert r_viejo < r_nuevo

    def test_resolucion_con_puntuacion_da_recompensa(self):
        mg = TargetRush(RECT, FX())
        mg.score = 8
        mg.start = time.time() - mg.DURATION - 0.1
        mg.update(time.time(), 0.016)
        assert mg.finished and mg.reward is not None

    def test_resolucion_bajo_el_minimo_no_premia(self):
        mg = TargetRush(RECT, FX())
        mg.score = 2
        mg.start = time.time() - mg.DURATION - 0.1
        mg.update(time.time(), 0.016)
        assert mg.finished and mg.reward is None

    def test_multiplicador_acotado_a_3(self):
        mg = TargetRush(RECT, FX())
        mg.score = 100
        mg.start = time.time() - mg.DURATION - 0.1
        mg.update(time.time(), 0.016)
        assert mg.reward[0] == pytest.approx(3.0)

    def test_finish_es_de_un_solo_disparo(self):
        mg = TargetRush(RECT, FX())
        mg.finish((2.0, 30.0), "primero", (0, 255, 0))
        mg.finish(None, "segundo", (255, 0, 0))
        assert mg.reward == (2.0, 30.0)
        assert mg.result_msg == "primero"


class TestGoldRain:

    def _atrapa(self, mg, kind):
        mg.bx = 400
        basket_y = mg.area.bottom - 22
        mg.objs.append({"x": 400, "y": float(basket_y), "vy": 10,
                        "kind": kind, "ph": 0.0})
        mg.update(time.time(), 0.016)

    def test_atrapar_moneda_suma_1(self):
        mg = GoldRain(RECT, FX())
        self._atrapa(mg, "coin")
        assert mg.score == 1

    def test_atrapar_gema_suma_3(self):
        mg = GoldRain(RECT, FX())
        self._atrapa(mg, "gem")
        assert mg.score == 3

    def test_atrapar_bomba_resta_3(self):
        mg = GoldRain(RECT, FX())
        mg.score = 5
        self._atrapa(mg, "bomb")
        assert mg.score == 2

    def test_objeto_lejos_de_la_cesta_no_se_atrapa(self):
        mg = GoldRain(RECT, FX())
        mg.bx = mg.area.x + 60
        basket_y = mg.area.bottom - 22
        mg.objs.append({"x": mg.area.right - 30, "y": float(basket_y),
                        "vy": 10, "kind": "coin", "ph": 0.0})
        mg.update(time.time(), 0.016)
        assert mg.score == 0

    def test_resolucion_umbral_minimo(self):
        ok, mal = GoldRain(RECT, FX()), GoldRain(RECT, FX())
        ok.score, mal.score = 10, 5
        for mg in (ok, mal):
            mg.start = time.time() - mg.DURATION - 0.1
            mg.update(time.time(), 0.016)
        assert ok.reward is not None
        assert mal.reward is None


class TestSimonPlus:

    def _a_input(self, mg):
        mg.show_start = time.time() - 100
        mg.update(time.time(), 0.016)

    def _repite_ronda(self, mg):
        boxes = mg._boxes()
        for ci in list(mg.seq):
            mg.event(click_event(), boxes[ci].centerx, boxes[ci].centery)
        if mg.phase == "gap":
            mg.gap_until = 0
            mg.update(time.time(), 0.016)

    def test_la_fase_mostrar_avanza_hasta_terminar(self):
        mg = SimonPlus(RECT, FX())
        idx, done = mg._show_index(mg.show_start - 1)
        assert idx == -1 and not done
        _, done = mg._show_index(mg.show_start + 100)
        assert done

    def test_las_secuencias_crecen_3_4_5(self):
        assert SimonPlus.LENGTHS == [3, 4, 5]

    def test_fallar_en_la_primera_ronda_no_premia(self):
        mg = SimonPlus(RECT, FX())
        self._a_input(mg)
        mal = (mg.seq[0] + 1) % 4
        boxes = mg._boxes()
        mg.event(click_event(), boxes[mal].centerx, boxes[mal].centery)
        assert mg.finished and mg.reward is None

    def test_fallar_tras_una_ronda_da_premio_parcial(self):
        mg = SimonPlus(RECT, FX())
        self._a_input(mg)
        self._repite_ronda(mg)
        self._a_input(mg)
        mal = (mg.seq[0] + 1) % 4
        boxes = mg._boxes()
        mg.event(click_event(), boxes[mal].centerx, boxes[mal].centery)
        assert mg.finished and mg.reward is not None
        assert mg.reward[0] < 3.0

    def test_completar_las_3_rondas_da_el_maximo(self):
        mg = SimonPlus(RECT, FX())
        for _ in range(3):
            self._a_input(mg)
            self._repite_ronda(mg)
        assert mg.finished and mg.reward == (3.0, 45.0)


class TestPulseBar:

    def test_pos_es_onda_triangular(self):
        mg = PulseBar(RECT, FX())
        speed = mg.SPEEDS[0]
        t0 = mg.round_start
        assert mg._pos(t0) == pytest.approx(0.0)
        assert mg._pos(t0 + 0.25 / speed) == pytest.approx(0.5)
        assert mg._pos(t0 + 0.50 / speed) == pytest.approx(1.0)
        assert mg._pos(t0 + 0.75 / speed) == pytest.approx(0.5)

    def _clic_en(self, mg, pos):
        now = time.time()
        speed = mg.SPEEDS[mg.round]
        mg.round_start = now - (pos / 2.0) / speed
        mg.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE), 0, 0)
        mg.wait_until = 0
        mg.update(time.time(), 0.016)

    def test_centro_exacto_da_la_ganancia_perfecta(self):
        mg = PulseBar(RECT, FX())
        self._clic_en(mg, 0.5)
        assert mg.hits[0][1] == pytest.approx(0.6)

    def test_fuera_de_zona_no_gana(self):
        mg = PulseBar(RECT, FX())
        self._clic_en(mg, 0.05)
        assert mg.hits[0][1] == pytest.approx(0.0)

    def test_timeout_cuenta_como_fallo(self):
        mg = PulseBar(RECT, FX())
        mg.round_start = time.time() - mg.ROUND_TIMEOUT - 1
        mg.update(time.time(), 0.016)
        assert len(mg.hits) == 1 and mg.hits[0][1] == pytest.approx(0.0)

    def test_tres_perfectos_dan_el_boost_maximo(self):
        mg = PulseBar(RECT, FX())
        for _ in range(3):
            self._clic_en(mg, 0.5)
        assert mg.finished and mg.reward == (3.0, 40.0)

    def test_ningun_acierto_no_premia(self):
        mg = PulseBar(RECT, FX())
        for _ in range(3):
            self._clic_en(mg, 0.02)
        assert mg.finished and mg.reward is None
