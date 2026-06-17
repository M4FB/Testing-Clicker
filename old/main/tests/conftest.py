"""
Fixtures y step definitions compartidos para BDD (pytest-bdd).

Patrón: un único @pytest.fixture 'game' + 'result' por escenario.
Todos los @given modifican el objeto game en lugar de reemplazarlo,
evitando conflictos de fixture cuando Background y Scenario coinciden.
"""
import time
import math
import pytest
from pytest_bdd import given, when, then, parsers

from src.game import GameState
from src.config import (
    BOOST, GENERATORS, CLICK_UPGRADES,
    PRESTIGE_1_THRESHOLD, PRESTIGE_2_THRESHOLD, VICTORY_THRESHOLD,
    BASE_CLICK_VALUE,
)


# ═══════════════════════════════════════════════════════════════════════════════
# Fixtures base (un único objeto por escenario)
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def game():
    return GameState()


@pytest.fixture
def result():
    return {"value": None}


# ═══════════════════════════════════════════════════════════════════════════════
# GIVEN — configuran estado del juego existente
# ═══════════════════════════════════════════════════════════════════════════════

@given("el juego está iniciado")
def game_fresco(game):
    """No-op: el fixture 'game' ya crea un GameState limpio."""
    pass


@given("el jugador tiene 0 puntos")
def sin_puntos(game):
    game.points = 0.0
    game.total_points = 0.0


@given("el jugador tiene 0 puntos acumulados")
def sin_acumulado(game):
    game.points = 0.0
    game.total_points = 0.0


@given("el jugador tiene muchísimos puntos pero 0 prestiges")
def muchos_sin_prestige(game):
    game.points = VICTORY_THRESHOLD * BOOST * 100
    game.total_points = VICTORY_THRESHOLD * BOOST * 100


@given(parsers.parse('el jugador tiene suficientes puntos para la mejora "{upg_id}"'))
def fondos_mejora(game, upg_id):
    cost = game.click_upgrade_cost(upg_id)
    game.points      = max(game.points,       cost * 2)
    game.total_points = max(game.total_points, game.points)


@given(parsers.parse('el jugador tiene fondos suficientes para comprar un "{gen_id}"'))
def fondos_gen(game, gen_id):
    cost = game.generator_cost(gen_id)
    game.points      = max(game.points,       cost * 2)
    game.total_points = max(game.total_points, game.points)


@given(parsers.parse('el jugador tiene fondos para {n:d} unidades de "{gen_id}"'))
def fondos_n_gen(game, n, gen_id):
    total = sum(
        math.ceil(
            next(g["cost"] for g in GENERATORS if g["id"] == gen_id)
            * (1.15 ** i) * BOOST
        )
        for i in range(n)
    )
    game.points      = max(game.points,       total * 2)
    game.total_points = max(game.total_points, game.points)


@given("el jugador ha acumulado puntos suficientes para el Prestige 1")
def umbral_prestige1(game):
    game.total_points = PRESTIGE_1_THRESHOLD * BOOST
    game.points = max(game.points, 1_000_000 * BOOST)


@given("el jugador ha acumulado puntos suficientes para el Prestige 2")
def umbral_prestige2(game):
    game.total_points = PRESTIGE_2_THRESHOLD * BOOST
    game.points = max(game.points, 1_000_000 * BOOST)


@given("el jugador ha completado el Prestige 1")
def completo_p1(game):
    game.total_points = PRESTIGE_1_THRESHOLD * BOOST
    game.prestige()


@given("el jugador ha completado los 2 prestiges")
def completo_dos_p(game):
    game.total_points = PRESTIGE_1_THRESHOLD * BOOST
    game.prestige()
    game.total_points = PRESTIGE_2_THRESHOLD * BOOST
    game.prestige()


@given("el jugador ha alcanzado el umbral de victoria")
def alcanza_victoria(game):
    game.total_points = PRESTIGE_1_THRESHOLD * BOOST
    game.prestige()
    game.total_points = PRESTIGE_2_THRESHOLD * BOOST
    game.prestige()
    game.total_points = VICTORY_THRESHOLD * BOOST


# ═══════════════════════════════════════════════════════════════════════════════
# WHEN — acciones
# ═══════════════════════════════════════════════════════════════════════════════

@when("el jugador hace clic una vez")
def un_clic(game):
    game.click()


@when(parsers.parse("el jugador hace clic {n:d} veces"))
def n_clics(game, n):
    for _ in range(n):
        game.click()


@when("el jugador gasta todos sus puntos comprando un generador")
def gasta_en_gen(game):
    cost = game.generator_cost("worker")
    if game.points >= cost:
        game.buy_generator("worker")


@when(parsers.parse('el jugador compra la mejora de clic "{upg_id}"'))
def compra_mejora(game, upg_id):
    game.buy_click_upgrade(upg_id)


@when(parsers.parse('el jugador intenta comprar la mejora "{upg_id}" de nuevo'))
def intenta_mejora_de_nuevo(game, result, upg_id):
    result["value"] = game.buy_click_upgrade(upg_id)


@when(parsers.parse('el jugador compra el generador "{gen_id}"'))
def compra_gen(game, gen_id):
    game.buy_generator(gen_id)


@when(parsers.parse('el jugador intenta comprar el generador "{gen_id}"'))
def intenta_compra_gen(game, result, gen_id):
    result["value"] = game.buy_generator(gen_id)


@when(parsers.parse('el jugador compra {n:d} unidades del generador "{gen_id}"'))
def compra_n_gen(game, n, gen_id):
    for _ in range(n):
        game.buy_generator(gen_id)


@when("el jugador intenta hacer prestige")
def intenta_prestige(game, result):
    result["value"] = game.prestige()


@when("el jugador activa el Prestige 1")
def activa_p1(game, result):
    result["value"] = game.prestige()


@when("el jugador activa el Prestige 2")
def activa_p2(game, result):
    result["value"] = game.prestige()


@when("el jugador intenta hacer prestige con muchos puntos")
def intenta_prestige_muchos(game, result):
    game.total_points = VICTORY_THRESHOLD * BOOST * 99
    result["value"] = game.prestige()


@when("el juego evalúa la condición de victoria")
def evalua_victoria(game, result):
    result["value"] = game.check_victory()


@when("el juego vuelve a evaluar la condición de victoria")
def re_evalua_victoria(game, result):
    result["value"] = game.check_victory()


@when(parsers.parse("el jugador activa el minijuego con multiplicador {mult:f}"))
def activa_minijuego(game, mult):
    game.activate_minigame(multiplier=mult, duration=60.0)


@when(parsers.parse("el jugador activa el minijuego con duración de {dur:d} segundos"))
def activa_minijuego_corto(game, dur):
    game.activate_minigame(multiplier=2.0, duration=0.01)


@when("pasa el tiempo suficiente")
def pasa_tiempo(game):
    time.sleep(0.05)
    game.tick()


# ═══════════════════════════════════════════════════════════════════════════════
# THEN — verificaciones
# ═══════════════════════════════════════════════════════════════════════════════

@then("los puntos del jugador son mayores a cero")
def puntos_positivos(game):
    assert game.points > 0


@then("el total acumulado es igual al valor de clic por 10")
def total_diez(game):
    assert game.total_points == pytest.approx(game.click_value * 10)


@then("el total histórico sigue siendo mayor a cero")
def historico_positivo(game):
    assert game.total_points > 0


@then("el valor por clic aumenta respecto al valor base")
def click_value_sube(game):
    assert game.click_value > BASE_CLICK_VALUE * BOOST


@then("la segunda compra falla")
def segunda_falla(result):
    assert result["value"] is False


@then("la compra del generador falla")
def compra_gen_falla(result):
    assert result["value"] is False


@then(parsers.parse('el jugador posee {n:d} unidad del generador "{gen_id}"'))
def tiene_n_gen(game, n, gen_id):
    assert game.generators[gen_id] == n


@then("los puntos por segundo son mayores a cero")
def pps_positivo(game):
    assert game.pps() > 0


@then(parsers.parse('el jugador sigue teniendo 0 generadores "{gen_id}"'))
def cero_gen(game, gen_id):
    assert game.generators[gen_id] == 0


@then(parsers.parse('el costo del generador "{gen_id}" ha escalado correctamente'))
def precio_escala(game, gen_id):
    base = next(g["cost"] for g in GENERATORS if g["id"] == gen_id)
    costo_inicial = math.ceil(base * BOOST)
    costo_actual  = game.generator_cost(gen_id)
    assert costo_actual > costo_inicial


@then(parsers.parse('los puntos por segundo son proporcionales a {n:d} unidades'))
def pps_proporcional(game, n):
    pps_unit = next(g["pps"] for g in GENERATORS if g["id"] == "worker") * BOOST
    assert game.pps() == pytest.approx(pps_unit * n)


@then("el prestige no ocurre")
def prestige_no(result):
    assert result["value"] is False


@then("el prestige ocurre exitosamente")
def prestige_si(game):
    assert game.prestige_count >= 1


@then(parsers.parse("el contador de prestiges sigue en {n:d}"))
def contador_prestige(game, n):
    assert game.prestige_count == n


@then(parsers.parse("el multiplicador permanente es {mult:f}"))
def mult_permanente(game, mult):
    assert game.prestige_multiplier == pytest.approx(mult)


@then("los puntos actuales se reinician a cero")
def puntos_cero(game):
    assert game.points == pytest.approx(0.0)


@then(parsers.parse('el jugador tiene 0 unidades de "{gen_id}" tras el reinicio'))
def gen_reset(game, gen_id):
    assert game.generators[gen_id] == 0


@then(parsers.parse("el multiplicador total permanente es {mult:f}"))
def mult_total(game, mult):
    assert game.prestige_multiplier == pytest.approx(mult)


@then("el juego no declara la victoria")
def no_victoria(game):
    assert not game.won


@then("el juego declara la victoria")
def si_victoria(game):
    assert game.won


@then("el modo infinito queda desbloqueado")
def modo_infinito(game):
    assert game.infinite_mode


@then("la segunda evaluación no vuelve a disparar la victoria")
def no_re_dispara(result):
    assert result["value"] is False


@then(parsers.parse("el multiplicador de minijuego es {mult:f}"))
def mult_minijuego(game, mult):
    assert game.minigame_multiplier == pytest.approx(mult)


@then("los puntos por segundo se duplican respecto a la base")
def pps_doble(game):
    game.generators["worker"] = 1
    pps_base = next(g["pps"] for g in GENERATORS if g["id"] == "worker") * BOOST
    assert game.pps() == pytest.approx(pps_base * game.minigame_multiplier)


@then("el minijuego ya no está activo")
def mini_inactivo(game):
    assert not game.minigame_active


@then("el multiplicador de minijuego vuelve a 1.0")
def mult_mini_uno(game):
    assert game.minigame_multiplier == pytest.approx(1.0)
