"""Configuración común de los tests de la versión actual (v1.0).

Fuerza los drivers "dummy" de SDL para que pygame funcione sin pantalla ni
tarjeta de sonido (CI / headless) e inicializa pygame una sola vez.
"""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("GAME_MODE", "demo")

import pygame
import pytest
from pytest_bdd import given, when, then, parsers


@pytest.fixture(scope="session", autouse=True)
def _pygame_session():
    pygame.init()
    try:
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=4096)
    except pygame.error:
        pass
    pygame.display.set_mode((1024, 680))
    yield
    pygame.quit()


@pytest.fixture
def state():
    """GameState recién creado para cada test que lo pida."""
    from src.game import GameState
    return GameState()


@pytest.fixture
def tmp_save(tmp_path):
    """Ruta a un archivo de guardado temporal."""
    return str(tmp_path / "save.json")


@pytest.fixture
def tmp_prefs(tmp_path):
    return str(tmp_path / "prefs.json")


# ═══════════════════════════════════════════════════════════════════════════════
# BDD — fixtures y step definitions (pytest-bdd, Gherkin en español)
# Las usan los escenarios de tests/features/*.feature vía tests/test_bdd.py.
# ═══════════════════════════════════════════════════════════════════════════════
from src.config import (
    BOOST, GENERATORS, BASE_CLICK_VALUE,
    PRESTIGE_1_THRESHOLD, PRESTIGE_2_THRESHOLD, VICTORY_THRESHOLD,
)


@pytest.fixture
def game():
    """GameState para BDD. Críticos desactivados → escenarios deterministas."""
    from src.game import GameState
    g = GameState()
    g.crit_chance = 0.0
    return g


@pytest.fixture
def result():
    return {"value": None}


@pytest.fixture
def ctx():
    """Bolsa de datos compartida entre steps de un escenario."""
    return {}


# ── GIVEN ─────────────────────────────────────────────────────────────────────
@given("el juego está iniciado")
def _iniciado(game):
    pass


@given("el jugador tiene 0 puntos acumulados")
def _sin_acumulado(game):
    game.points = game.total_points = 0.0


@given(parsers.parse('el jugador tiene fondos para la mejora "{upg_id}"'))
def _fondos_mejora(game, upg_id):
    game.points = game.click_upgrade_cost(upg_id) * 2
    game.total_points = max(game.total_points, game.points)


@given(parsers.parse('el jugador tiene fondos para un "{gen_id}"'))
def _fondos_gen(game, gen_id):
    game.points = game.generator_cost(gen_id) * 2
    game.total_points = max(game.total_points, game.points)


@given(parsers.parse('el jugador tiene fondos para {n:d} unidades de "{gen_id}"'))
def _fondos_n(game, n, gen_id):
    game.points = game.generator_cost_n(gen_id, n) + 10
    game.total_points = max(game.total_points, game.points)


@given("el jugador alcanzó el umbral del Prestige 1")
def _umbral_p1(game):
    game.total_points = PRESTIGE_1_THRESHOLD * BOOST
    game.points = max(game.points, 1_000.0)


@given("el jugador completó el Prestige 1")
def _completo_p1(game):
    game.total_points = PRESTIGE_1_THRESHOLD * BOOST
    game.prestige()


@given("el jugador alcanzó el umbral del Prestige 2")
def _umbral_p2(game):
    game.total_points = PRESTIGE_2_THRESHOLD * BOOST
    game.points = max(game.points, 1_000.0)


@given("el jugador alcanzó el umbral de victoria")
def _umbral_victoria(game):
    game.total_points = PRESTIGE_1_THRESHOLD * BOOST
    game.prestige()
    game.total_points = PRESTIGE_2_THRESHOLD * BOOST
    game.prestige()
    game.total_points = VICTORY_THRESHOLD * BOOST


@given("el jugador tiene muchos puntos pero 0 prestiges")
def _muchos_sin_prestige(game):
    game.total_points = VICTORY_THRESHOLD * BOOST * 10
    game.points = game.total_points


@given("una partida con progreso")
def _partida_progreso(game):
    game.points = 4321.0
    game.total_points = 9999.0
    game.generators["worker"] = 7
    game.stats["clicks"] = 50


@given(parsers.parse("el volumen de música configurado es {v:f}"))
def _vol_config(ctx, v):
    ctx["mv"] = v


@given("las tres pistas de música")
def _tres_pistas(ctx):
    from src import music as M
    ctx["tracks"] = {
        "game":   M.generate_loop(),
        "menu":   M.generate_menu_loop(),
        "config": M.generate_config_loop(),
    }


@given("un gestor de música")
def _gestor(ctx):
    from src import music as M
    ctx["mgr"] = M.MusicManager(volume=0.5)


# ── WHEN ──────────────────────────────────────────────────────────────────────
@when("el jugador hace clic una vez")
def _un_clic(game):
    game.click()


@when(parsers.parse("el jugador hace clic {n:d} veces"))
def _n_clics(game, n):
    for _ in range(n):
        game.click()


@when("el jugador gasta todos sus puntos en un generador")
def _gasta(game):
    while game.buy_generator("worker"):
        pass


@when(parsers.parse('el jugador compra la mejora de clic "{upg_id}"'))
def _compra_mejora(game, upg_id):
    game.buy_click_upgrade(upg_id)


@when(parsers.parse('el jugador intenta comprar la mejora "{upg_id}" otra vez'))
def _recompra_mejora(game, result, upg_id):
    result["value"] = game.buy_click_upgrade(upg_id)


@when(parsers.parse('el jugador compra el generador "{gen_id}"'))
def _compra_gen(game, gen_id):
    game.buy_generator(gen_id)


@when(parsers.parse('el jugador intenta comprar el generador "{gen_id}"'))
def _intenta_gen(game, result, gen_id):
    result["value"] = game.buy_generator(gen_id)


@when(parsers.parse('el jugador compra {n:d} unidades de "{gen_id}"'))
def _compra_n(game, n, gen_id):
    game.buy_generator_n(gen_id, n)


@when("el jugador activa el Prestige")
def _activa_prestige(game, result):
    result["value"] = game.prestige()


@when("el jugador intenta hacer prestige")
def _intenta_prestige(game, result):
    result["value"] = game.prestige()


@when("el juego evalúa la condición de victoria")
def _evalua_victoria(game, result):
    result["value"] = game.check_victory()


@when("el juego vuelve a evaluar la condición de victoria")
def _reevalua_victoria(game, result):
    result["value"] = game.check_victory()


@when("se guarda y se vuelve a cargar la partida")
def _guardar_cargar(game, ctx, tmp_save):
    from src import save as S
    S.save_game(game, elapsed=42.0, path=tmp_save)
    ctx["loaded"], ctx["meta"] = S.load_game(path=tmp_save)


@when("se guardan y recargan las preferencias")
def _guardar_prefs(ctx, tmp_prefs):
    from src import save as S
    S.save_prefs(music_vol=ctx["mv"], path=tmp_prefs)
    ctx["prefs"] = S.load_prefs(path=tmp_prefs)


@when(parsers.parse('el gestor reproduce la pista "{name}"'))
def _reproduce(ctx, name):
    ctx["mgr"].play(name)


@when("el juego se pausa")
def _pausa(ctx):
    ctx["mgr"].duck(0.4)


# ── THEN ──────────────────────────────────────────────────────────────────────
@then("los puntos del jugador son mayores a cero")
def _puntos_pos(game):
    assert game.points > 0


@then("el total acumulado es el valor de clic multiplicado por 10")
def _total_diez(game):
    assert game.total_points == pytest.approx(game.click_value * 10)


@then("el total histórico sigue siendo mayor a cero")
def _historico_pos(game):
    assert game.total_points > 0


@then("el valor por clic supera al valor base")
def _click_sube(game):
    assert game.click_value > BASE_CLICK_VALUE * BOOST


@then("la segunda compra falla")
def _segunda_falla(result):
    assert result["value"] is False


@then("la compra del generador falla")
def _compra_falla(result):
    assert result["value"] is False


@then(parsers.parse('el jugador posee {n:d} unidades de "{gen_id}"'))
def _posee_n(game, n, gen_id):
    assert game.generators[gen_id] == n


@then("los puntos por segundo son mayores a cero")
def _pps_pos(game):
    assert game.pps() > 0


@then(parsers.parse('el costo del generador "{gen_id}" ha escalado'))
def _costo_escala(game, gen_id):
    base = next(g["cost"] for g in GENERATORS if g["id"] == gen_id)
    import math
    assert game.generator_cost(gen_id) > math.ceil(base * BOOST)


@then("el prestige se realiza con éxito")
def _prestige_ok(game, result):
    assert result["value"] is True and game.prestige_count >= 1


@then("el prestige no ocurre")
def _prestige_no(result):
    assert result["value"] is False


@then("los puntos actuales se reinician a cero")
def _puntos_cero(game):
    assert game.points == pytest.approx(0.0)


@then(parsers.parse("el multiplicador permanente de prestigio es {mult:f}"))
def _mult_prestige(game, mult):
    assert game.prestige_multiplier == pytest.approx(mult)


@then("el jugador gana puntos de prestigio")
def _gana_pp(game):
    assert game.prestige_points >= 2


@then("el juego declara la victoria")
def _declara_victoria(game, result):
    assert result["value"] is True and game.won and game.infinite_mode


@then("la victoria no se vuelve a disparar")
def _no_redispara(result):
    assert result["value"] is False


@then("el juego no declara la victoria")
def _no_victoria(game, result):
    assert result["value"] is False and not game.won


@then("la partida cargada conserva los puntos y generadores")
def _conserva(ctx):
    g = ctx["loaded"]
    assert g is not None
    assert g.points == 4321.0 and g.total_points == 9999.0
    assert g.generators["worker"] == 7


@then(parsers.parse("las preferencias cargadas tienen música {v:f}"))
def _prefs_musica(ctx, v):
    assert ctx["prefs"]["music_vol"] == pytest.approx(v)


@then("las tres pistas tienen duraciones distintas")
def _duraciones_distintas(ctx):
    lens = {k: a.shape[0] for k, a in ctx["tracks"].items()}
    assert len(set(lens.values())) == 3


@then(parsers.parse('la pista actual es "{name}"'))
def _pista_actual(ctx, name):
    assert ctx["mgr"].current == name


@then("el volumen aplicado es menor que el de usuario")
def _volumen_menor(ctx):
    assert ctx["mgr"]._applied() < ctx["mgr"].get_volume()


# ── Nuevas features steps ─────────────────────────────────────────────────────
@given(parsers.parse("el jugador alcanzó el umbral de total_points de {pts:d}"))
def _umbral_puntos(game, pts):
    game.total_points = float(pts * BOOST)


@then(parsers.parse("los puntos por segundo son de al menos {pps:d}"))
def _pps_al_menos(game, pps):
    assert game.pps() >= float(pps)


@given(parsers.parse('el jugador tiene la mejora de prestigio "{upg_id}" comprada'))
def _prestige_comprada(game, upg_id):
    from src.config import PRESTIGE_UPGRADES
    game.prestige_upgrades[upg_id] = True
    for u in PRESTIGE_UPGRADES:
        if u["id"] == upg_id:
            game._apply_prestige_effect(u)
    if upg_id == "pp_double_crit":
        game.double_crit_chance = 1.0


@when(parsers.parse("transcurre {n:d} segundo de juego"))
def _transcurre_segundo(game, n):
    import time
    game._last_tick = time.time() - float(n)
    game.tick()


@then("el total de clics registrados es mayor que cero")
def _clics_mayor_cero(game):
    assert game.stats["clicks"] > 0


@given("la probabilidad de crítico es del 100%")
def _crit_100(game):
    game.crit_chance = 1.0


@then(parsers.parse("el valor obtenido es {n:d} veces el clic base"))
def _valor_clic_n(game, n):
    base_click = game.click_value * game.click_mult * game.perm_click_mult * game._boosts()
    assert game.points == base_click * n
