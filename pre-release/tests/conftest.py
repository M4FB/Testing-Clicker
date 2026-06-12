"""
Fixtures y step definitions compartidos (pre-release).

Cubre las mecánicas nuevas de esta versión:
  - Compra múltiple de generadores (×1 / ×10 / MAX)
  - Guardado y carga de partida (JSON)
  - Minijuegos con recompensa proporcional al desempeño
  - Retroalimentación sonora procedural

Patrón BDD: igual que la suite estable — un fixture 'game' por escenario y
fixtures de contexto ('sctx', 'mctx') que los steps comparten.
"""
import os

# Drivers dummy ANTES de importar pygame: la suite corre sin ventana ni audio real
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import json
import math
import time

import pygame
import pytest
from pytest_bdd import given, when, then, parsers

from src.game import GameState
from src.config import GENERATORS, PRICE_SCALE, BOOST, MODE
from src import save as save_mod
from src import sfx
from src.fx import FX
from src.minigames import TargetRush, GoldRain, SimonPlus, PulseBar

RECT = pygame.Rect(232, 120, 580, 440)   # modal estándar para minijuegos


# ═══════════════════════════════════════════════════════════════════════════════
# Fixtures base
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="session", autouse=True)
def _pygame_session():
    """pygame headless para toda la sesión (la UI y los Sound lo requieren)."""
    pygame.init()
    try:
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
    except pygame.error:
        pass
    pygame.display.set_mode((1024, 680))
    yield
    pygame.quit()


@pytest.fixture(autouse=True)
def no_real_save(monkeypatch):
    """La UI nunca debe escribir el guardado real del usuario durante los tests.

    Devuelve la lista de llamadas para que los tests verifiquen que se guardó.
    """
    calls: list[dict] = []
    import src.pygame_ui as pui
    monkeypatch.setattr(pui, "save_game",
                        lambda *a, **k: calls.append(k))
    return calls


@pytest.fixture
def game():
    return GameState()


@pytest.fixture
def result():
    return {"value": None}


@pytest.fixture
def sctx(tmp_path):
    """Contexto de guardado: ruta temporal + estado/metadatos cargados."""
    return {"path": str(tmp_path / "save.json"),
            "original": None, "loaded": None, "meta": {}}


@pytest.fixture
def mctx():
    """Contexto de minijuego: instancia + datos auxiliares."""
    return {"mg": None, "score": None, "extra": {}}


def _click():
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1)


def _gold_target(x=300, y=300):
    return {"x": x, "y": y, "r0": 30, "born": time.time(), "life": 9.0,
            "kind": "gold"}


def _expirar(mg):
    """Fuerza el fin del tiempo del minijuego y lo resuelve."""
    mg.start = time.time() - mg.DURATION - 0.1
    mg.update(time.time(), 0.016)


def _simon_a_fase_input(mg):
    """Salta la fase 'mostrar' de Simón para poder repetir la secuencia."""
    mg.show_start = time.time() - 100
    mg.update(time.time(), 0.016)
    assert mg.phase == "input"


def _simon_repetir_ronda(mg):
    """Repite correctamente la secuencia de la ronda actual."""
    boxes = mg._boxes()
    for ci in list(mg.seq):
        br = boxes[ci]
        mg.event(_click(), br.centerx, br.centery)
    if mg.phase == "gap":
        mg.gap_until = 0
        mg.update(time.time(), 0.016)


def _pulso_clic_en(mg, pos_deseada):
    """Coloca el marcador en pos_deseada (0..1) y dispara el clic."""
    now = time.time()
    speed = mg.SPEEDS[mg.round]
    mg.round_start = now - (pos_deseada / 2.0) / speed
    mg.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE), 0, 0)
    mg.wait_until = 0
    mg.update(time.time(), 0.016)


# ═══════════════════════════════════════════════════════════════════════════════
# GIVEN
# ═══════════════════════════════════════════════════════════════════════════════

@given("el juego está iniciado")
def juego_iniciado(game):
    pass


@given("el jugador tiene 0 puntos acumulados")
def sin_acumulado(game):
    game.points = 0.0
    game.total_points = 0.0


@given(parsers.parse("el jugador tiene {pts:d} puntos"))
def con_puntos(game, pts):
    game.points = float(pts)
    game.total_points = float(pts)


@given(parsers.parse('el jugador tiene fondos exactos para {n:d} unidades de "{gen_id}"'))
def fondos_exactos(game, n, gen_id):
    game.points = float(game.generator_cost_n(gen_id, n))
    game.total_points = game.points


@given(parsers.parse('el jugador tiene fondos para {n:d} unidades de "{gen_id}"'))
def fondos_holgados(game, n, gen_id):
    game.points = float(game.generator_cost_n(gen_id, n))
    game.total_points = game.points


@given("una partida avanzada con generadores y mejoras")
def partida_avanzada(game, sctx):
    game.points = 100_000.0
    game.total_points = 250_000.0
    game.buy_generator_n("worker", 5)
    game.buy_click_upgrade("cu_1")
    game.buy_gen_upgrade("gu_g1")
    game.high_score = 250_000.0
    sctx["original"] = game


@given("no existe ningún archivo de guardado")
def sin_archivo(sctx):
    assert not os.path.exists(sctx["path"])


@given("una partida guardada en otro modo de juego")
def guardado_otro_modo(game, sctx):
    save_mod.save_game(game, path=sctx["path"])
    with open(sctx["path"]) as fh:
        data = json.load(fh)
    data["mode"] = "full" if MODE == "demo" else "demo"
    with open(sctx["path"], "w") as fh:
        json.dump(data, fh)


@given("un minijuego listo para jugarse")
def minijuego_listo(mctx):
    pass


@given(parsers.parse("una partida de Fiebre Dorada con {n:d} monedas atrapadas"))
def fiebre_con_monedas(mctx, n):
    mg = TargetRush(RECT, FX())
    for _ in range(n):
        mg.targets.append(_gold_target())
        mg.event(_click(), 300, 300)
    assert mg.score == n
    mctx["mg"] = mg
    mctx["score"] = n


@given("una partida de Lluvia Dorada")
def lluvia_partida(mctx):
    mctx["mg"] = GoldRain(RECT, FX())


# ═══════════════════════════════════════════════════════════════════════════════
# WHEN
# ═══════════════════════════════════════════════════════════════════════════════

@when(parsers.parse('el jugador compra un lote de {n:d} del generador "{gen_id}"'))
def compra_lote(game, n, gen_id):
    game.buy_generator_n(gen_id, n)


@when(parsers.parse('el jugador compra el máximo posible del generador "{gen_id}"'))
def compra_max(game, gen_id):
    n = game.max_affordable_generators(gen_id)
    game.buy_generator_n(gen_id, n)


@when("el jugador guarda la partida")
def guarda(game, sctx):
    save_mod.save_game(game, path=sctx["path"])


@when(parsers.parse("el jugador guarda la partida tras {seg:d} segundos de juego"))
def guarda_con_tiempo(game, sctx, seg):
    save_mod.save_game(game, elapsed=float(seg), path=sctx["path"])


@when("el jugador carga la partida guardada")
def carga(sctx):
    sctx["loaded"], sctx["meta"] = save_mod.load_game(path=sctx["path"])


@when("el jugador borra la partida guardada")
def borra(sctx):
    save_mod.delete_save(path=sctx["path"])


@when("termina el tiempo del minijuego")
def expira_minijuego(mctx):
    _expirar(mctx["mg"])


@when("el jugador repite correctamente las 3 secuencias de Simón")
def simon_completo(mctx):
    mg = SimonPlus(RECT, FX())
    for _ in range(3):
        _simon_a_fase_input(mg)
        _simon_repetir_ronda(mg)
    mctx["mg"] = mg


@when("el jugador completa una ronda de Simón y falla la siguiente")
def simon_parcial(mctx):
    mg = SimonPlus(RECT, FX())
    _simon_a_fase_input(mg)
    _simon_repetir_ronda(mg)
    _simon_a_fase_input(mg)
    boxes = mg._boxes()
    mal = (mg.seq[0] + 1) % 4
    mg.event(_click(), boxes[mal].centerx, boxes[mal].centery)
    mctx["mg"] = mg


@when("el jugador detiene el marcador en el centro las 3 rondas")
def pulso_perfecto(mctx):
    mg = PulseBar(RECT, FX())
    for _ in range(3):
        _pulso_clic_en(mg, 0.5)
    mctx["mg"] = mg


@when("la cesta atrapa una bomba")
def cesta_bomba(mctx):
    mg = mctx["mg"]
    mg.score = 5
    mg.bx = 400
    basket_y = mg.area.bottom - 22
    mg.objs.append({"x": 400, "y": float(basket_y), "vy": 10,
                    "kind": "bomb", "ph": 0.0})
    mg.update(time.time(), 0.016)
    mctx["score"] = mg.score


@when("el jugador sube el volumen de sonidos más allá del máximo")
def sube_volumen(mctx):
    mctx["extra"]["vol_previo"] = sfx.get_volume()
    sfx.set_volume(2.0)


@when("se reproduce un sonido sin mezclador inicializado")
def play_sin_mixer(mctx):
    params = pygame.mixer.get_init()
    pygame.mixer.quit()
    try:
        sfx.play("click")
        mctx["extra"]["ok"] = True
    except Exception:
        mctx["extra"]["ok"] = False
    finally:
        if params:
            pygame.mixer.init(frequency=params[0], size=params[1],
                              channels=params[2], buffer=512)


# ═══════════════════════════════════════════════════════════════════════════════
# THEN
# ═══════════════════════════════════════════════════════════════════════════════

@then(parsers.parse('el jugador posee {n:d} unidades del generador "{gen_id}"'))
def posee_n(game, n, gen_id):
    assert game.generators[gen_id] == n


@then(parsers.parse('el coste del lote de {n:d} "{gen_id}" coincide con comprar '
                    'las unidades una a una'))
def coste_lote_coincide(game, n, gen_id):
    lote = game.generator_cost_n(gen_id, n)
    sim = GameState()
    sim.points = sim.total_points = 1e15
    antes = sim.points
    for _ in range(n):
        sim.buy_generator(gen_id)
    assert lote == pytest.approx(antes - sim.points)


@then(parsers.parse('el jugador no puede costear ni una unidad más de "{gen_id}"'))
def no_costea_mas(game, gen_id):
    assert game.max_affordable_generators(gen_id) == 0
    assert not game.can_buy_generator(gen_id)


@then(parsers.parse('el máximo comprable del generador "{gen_id}" es {n:d}'))
def max_comprable(game, gen_id, n):
    assert game.max_affordable_generators(gen_id) == n


@then("el estado cargado tiene los mismos puntos")
def mismos_puntos(sctx):
    assert sctx["loaded"] is not None
    assert sctx["loaded"].points == pytest.approx(sctx["original"].points)


@then("el estado cargado tiene los mismos generadores")
def mismos_generadores(sctx):
    assert sctx["loaded"].generators == sctx["original"].generators


@then("el estado cargado produce los mismos puntos por segundo")
def mismo_pps(sctx):
    assert sctx["loaded"].pps() == pytest.approx(sctx["original"].pps())


@then("no hay partida guardada compatible")
def sin_save_compatible(sctx):
    assert not save_mod.has_compatible_save(path=sctx["path"])


@then(parsers.parse("los metadatos indican {seg:d} segundos jugados"))
def metadatos_tiempo(sctx, seg):
    assert sctx["meta"].get("elapsed") == pytest.approx(float(seg))


@then("el minijuego otorga una recompensa")
def con_recompensa(mctx):
    mg = mctx["mg"]
    assert mg.finished and mg.reward is not None
    mult, dur = mg.reward
    assert mult > 1.0 and dur > 0


@then("el minijuego no otorga recompensa")
def sin_recompensa(mctx):
    mg = mctx["mg"]
    assert mg.finished and mg.reward is None


@then("el multiplicador crece con la puntuación")
def mult_crece(mctx):
    peor = TargetRush(RECT, FX())
    peor.score = max(3, mctx["score"] // 2)
    _expirar(peor)
    assert mctx["mg"].reward[0] > peor.reward[0]


@then("la recompensa es el boost máximo de Simón")
def simon_maximo(mctx):
    assert mctx["mg"].reward == (3.0, 45.0)


@then("la recompensa es el boost máximo de Pulso")
def pulso_maximo(mctx):
    assert mctx["mg"].reward == (3.0, 40.0)


@then("la puntuación de Lluvia Dorada baja")
def lluvia_baja(mctx):
    assert mctx["score"] < 5


@then("cada efecto de sonido definido se genera sin errores")
def sonidos_generan(mctx):
    nombres = ["click0", "click1", "click2", "buy", "upgrade", "coin", "gem",
               "bomb", "error", "tick", "win", "fail", "fanfare",
               "simon0", "simon1", "simon2", "simon3"]
    for n in nombres:
        arr = sfx._build(n)
        assert len(arr) > 0, n


@then("el volumen queda limitado al máximo")
def volumen_limitado(mctx):
    try:
        assert sfx.get_volume() == 1.0
    finally:
        sfx.set_volume(mctx["extra"].get("vol_previo", 0.5))


@then("no ocurre ningún error")
def sin_error(mctx):
    assert mctx["extra"].get("ok") is True
