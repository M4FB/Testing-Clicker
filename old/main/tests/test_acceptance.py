"""
Pruebas de Aceptación (ATDD — Acceptance Test Driven Development)

Validan los Requisitos Funcionales desde la perspectiva del usuario.
Cada clase corresponde a un criterio de aceptación (AC-XX) derivado de
los requisitos funcionales mínimos del proyecto.

Referencias:
  AC-01  Inicio del juego
  AC-02  Objetivo claro y medible
  AC-03  Interacción del jugador
  AC-04  Sistema de puntaje y progreso
  AC-05  Respuesta a eventos del jugador
  AC-06  Mecánicas de juego (prestige, minijuego, generadores)
  AC-07  Condición de fin del juego (victoria)
"""
import time
import pytest
from src.game import GameState
from src.config import (
    BOOST, CLICK_UPGRADES, GENERATORS,
    PRESTIGE_1_THRESHOLD, PRESTIGE_2_THRESHOLD, VICTORY_THRESHOLD,
    BASE_CLICK_VALUE,
)


# ─────────────────────────────────────────────────────────────────────────────
class TestAC01_InicioJuego:
    """
    AC-01: El juego debe iniciar con estado limpio y correcto.
    RF: Inicio y cierre del juego.
    """

    def test_juego_inicia_con_cero_puntos(self):
        """El jugador empieza sin puntos acumulados."""
        game = GameState()
        assert game.points == 0.0
        assert game.total_points == 0.0

    def test_juego_inicia_sin_generadores(self):
        """No hay generadores comprados al inicio."""
        game = GameState()
        for gen in GENERATORS:
            assert game.generators[gen["id"]] == 0

    def test_juego_inicia_sin_mejoras(self):
        """No hay mejoras de clic compradas al inicio."""
        game = GameState()
        for upg in CLICK_UPGRADES:
            assert game.click_upgrades[upg["id"]] is False

    def test_juego_inicia_sin_prestiges(self):
        """El contador de prestiges comienza en cero."""
        game = GameState()
        assert game.prestige_count == 0
        assert game.prestige_multiplier == 1.0

    def test_juego_inicia_sin_victoria(self):
        """El estado de victoria está en False al inicio."""
        game = GameState()
        assert game.won is False
        assert game.infinite_mode is False


# ─────────────────────────────────────────────────────────────────────────────
class TestAC02_ObjetivoClaro:
    """
    AC-02: El juego debe tener una meta definida y medible.
    RF: Objetivo claro.
    """

    def test_umbral_de_victoria_esta_definido(self):
        """Existe un umbral de victoria concreto y positivo."""
        assert VICTORY_THRESHOLD > 0

    def test_umbrales_de_prestige_estan_definidos(self):
        """Los umbrales de prestige existen y tienen orden lógico."""
        assert 0 < PRESTIGE_1_THRESHOLD < PRESTIGE_2_THRESHOLD < VICTORY_THRESHOLD

    def test_progreso_hacia_objetivo_es_medible(self):
        """El porcentaje de progreso es calculable y está en rango válido."""
        game = GameState()
        pct = game.prestige_progress_pct()
        assert 0.0 <= pct <= 100.0

    def test_progreso_aumenta_al_acumular_puntos(self):
        """El porcentaje de progreso crece cuando se acumulan puntos."""
        game = GameState()
        pct_antes = game.prestige_progress_pct()
        for _ in range(100):
            game.click()
        pct_despues = game.prestige_progress_pct()
        assert pct_despues > pct_antes

    def test_umbral_siguiente_cambia_con_prestige(self):
        """El umbral objetivo cambia tras cada prestige."""
        game = GameState()
        t1 = game.prestige_threshold()
        game.total_points = PRESTIGE_1_THRESHOLD * BOOST
        game.prestige()
        t2 = game.prestige_threshold()
        assert t2 > t1


# ─────────────────────────────────────────────────────────────────────────────
class TestAC03_InteraccionJugador:
    """
    AC-03: El jugador puede interactuar con el juego mediante acciones directas.
    RF: Interacción del jugador.
    """

    def test_jugador_puede_hacer_clic_y_ganar_puntos(self):
        """La acción de clic produce puntos de forma inmediata."""
        game = GameState()
        earned = game.click()
        assert earned > 0
        assert game.points == earned

    def test_jugador_puede_comprar_generador(self):
        """El jugador puede comprar un generador si tiene fondos."""
        game = GameState()
        cost = game.generator_cost("worker")
        game.points = cost
        game.total_points = cost
        ok = game.buy_generator("worker")
        assert ok is True
        assert game.generators["worker"] == 1

    def test_jugador_puede_comprar_mejora_clic(self):
        """El jugador puede adquirir mejoras de clic."""
        game = GameState()
        upg = CLICK_UPGRADES[0]
        cost = game.click_upgrade_cost(upg["id"])
        game.points = cost
        game.total_points = cost
        ok = game.buy_click_upgrade(upg["id"])
        assert ok is True
        assert game.click_upgrades[upg["id"]] is True

    def test_jugador_puede_activar_prestige(self):
        """El jugador puede activar el prestige cuando cumple el umbral."""
        game = GameState()
        game.total_points = PRESTIGE_1_THRESHOLD * BOOST
        ok = game.prestige()
        assert ok is True
        assert game.prestige_count == 1

    def test_jugador_puede_activar_minijuego(self):
        """El jugador puede activar el minijuego para obtener bonus."""
        game = GameState()
        game.activate_minigame(multiplier=2.0, duration=30.0)
        assert game.minigame_active is True


# ─────────────────────────────────────────────────────────────────────────────
class TestAC04_SistemaPuntaje:
    """
    AC-04: El juego mide el rendimiento del jugador de forma continua.
    RF: Sistema de puntaje o progreso.
    """

    def test_puntos_aumentan_con_clics(self):
        """Cada clic incrementa el contador de puntos."""
        game = GameState()
        game.click()
        assert game.points > 0

    def test_puntos_aumentan_pasivamente(self):
        """Los generadores producen puntos sin intervención del jugador."""
        game = GameState()
        game.generators["worker"] = 5
        time.sleep(0.05)
        game.tick()
        assert game.points > 0

    def test_total_historico_nunca_decrece(self):
        """El total acumulado histórico no disminuye aunque se gasten puntos."""
        game = GameState()
        for _ in range(10):
            game.click()
        total_antes = game.total_points
        cost = game.generator_cost("worker")
        game.points += cost
        game.buy_generator("worker")
        assert game.total_points >= total_antes

    def test_pps_refleja_generadores_comprados(self):
        """Los PPS se calculan correctamente según los generadores activos."""
        game = GameState()
        assert game.pps() == 0.0
        game.generators["worker"] = 3
        pps_esperado = next(g["pps"] for g in GENERATORS if g["id"] == "worker") * 3 * BOOST
        assert game.pps() == pytest.approx(pps_esperado)

    def test_valor_por_clic_refleja_mejoras(self):
        """El valor por clic aumenta correctamente al comprar mejoras."""
        game = GameState()
        valor_base = game.click_value
        upg = CLICK_UPGRADES[0]
        cost = game.click_upgrade_cost(upg["id"])
        game.points = cost
        game.total_points = cost
        game.buy_click_upgrade(upg["id"])
        assert game.click_value > valor_base

    def test_high_score_se_actualiza(self):
        """El marcador de puntuación máxima se actualiza correctamente."""
        game = GameState()
        for _ in range(50):
            game.click()
        game.tick()
        assert game.high_score >= game.total_points - 0.001


# ─────────────────────────────────────────────────────────────────────────────
class TestAC05_RespuestaEventos:
    """
    AC-05: El juego reacciona correctamente ante las acciones del jugador.
    RF: Respuesta a eventos.
    """

    def test_compra_genera_cambio_de_estado(self):
        """Comprar un generador modifica el estado del juego."""
        game = GameState()
        cost = game.generator_cost("worker")
        game.points = cost
        game.total_points = cost
        antes = game.generators["worker"]
        game.buy_generator("worker")
        assert game.generators["worker"] == antes + 1

    def test_compra_descuenta_puntos(self):
        """Comprar descuenta el costo de los puntos disponibles."""
        game = GameState()
        cost = game.generator_cost("worker")
        game.points = cost * 2
        game.total_points = cost * 2
        game.buy_generator("worker")
        assert game.points < cost * 2

    def test_prestige_resetea_todo_el_progreso(self):
        """El prestige elimina puntos, generadores y mejoras compradas."""
        game = GameState()
        game.generators["worker"] = 5
        game.click_upgrades["cu_1"] = True
        game.points = 999_999
        game.total_points = PRESTIGE_1_THRESHOLD * BOOST
        game.prestige()
        assert game.points == pytest.approx(0.0)
        assert game.generators["worker"] == 0
        assert game.click_upgrades["cu_1"] is False

    def test_minijuego_modifica_produccion(self):
        """Activar el minijuego cambia la tasa de producción."""
        game = GameState()
        game.generators["worker"] = 1
        pps_sin_mini = game.pps()
        game.activate_minigame(multiplier=3.0, duration=60.0)
        pps_con_mini = game.pps()
        assert pps_con_mini == pytest.approx(pps_sin_mini * 3.0)

    def test_intento_compra_sin_fondos_no_modifica_estado(self):
        """Intentar comprar sin fondos no altera el estado del juego."""
        game = GameState()
        game.points = 0
        game.buy_generator("worker")
        assert game.generators["worker"] == 0
        assert game.points == 0.0


# ─────────────────────────────────────────────────────────────────────────────
class TestAC06_MecanicasJuego:
    """
    AC-06: El juego implementa mecánicas incrementales no triviales.
    RF: Al menos una mecánica de juego.
    """

    def test_sistema_incremental_escala_costos(self):
        """Los costos de generadores escalan exponencialmente."""
        game = GameState()
        costos = []
        for _ in range(4):
            costos.append(game.generator_cost("worker"))
            game.generators["worker"] += 1
        for i in range(1, len(costos)):
            assert costos[i] > costos[i - 1]

    def test_prestige_aumenta_multiplicador_permanente(self):
        """El prestige otorga bonificación permanente al multiplicador."""
        game = GameState()
        mult_base = game.prestige_multiplier
        game.total_points = PRESTIGE_1_THRESHOLD * BOOST
        game.prestige()
        assert game.prestige_multiplier > mult_base

    def test_multiplicador_prestige_afecta_produccion(self):
        """El multiplicador de prestige amplifica los PPS reales."""
        game_sin = GameState()
        game_sin.generators["worker"] = 1
        pps_sin = game_sin.pps()

        game_con = GameState()
        game_con.total_points = PRESTIGE_1_THRESHOLD * BOOST
        game_con.prestige()
        game_con.generators["worker"] = 1
        pps_con = game_con.pps()

        assert pps_con == pytest.approx(pps_sin * 1.5)

    def test_minijuego_tiene_duracion_limitada(self):
        """El multiplicador del minijuego expira tras el tiempo definido."""
        game = GameState()
        game.activate_minigame(multiplier=2.0, duration=0.01)
        time.sleep(0.05)
        game.tick()
        assert not game.minigame_active
        assert game.minigame_multiplier == pytest.approx(1.0)

    def test_generadores_desbloqueados_progresivamente(self):
        """Los generadores avanzados requieren puntos acumulados para desbloquearse."""
        game = GameState()
        assert not game.generator_unlocked("factory")
        threshold = next(g["unlock"] for g in GENERATORS if g["id"] == "factory")
        game.total_points = threshold * BOOST
        assert game.generator_unlocked("factory")


# ─────────────────────────────────────────────────────────────────────────────
class TestAC07_CondicionVictoria:
    """
    AC-07: El juego tiene una condición de victoria clara y alcanzable.
    RF: Pantalla de inicio y final.
    """

    def test_victoria_requiere_exactamente_dos_prestiges(self):
        """La victoria solo es posible después de 2 prestiges."""
        game = GameState()
        game.total_points = VICTORY_THRESHOLD * BOOST * 10
        assert game.check_victory() is False
        assert game.won is False

    def test_victoria_completa_flujo_tres_partidas(self):
        """El juego puede completarse siguiendo el flujo de 3 partidas."""
        game = GameState()
        # Partida 1 → Prestige 1
        game.total_points = PRESTIGE_1_THRESHOLD * BOOST
        assert game.prestige() is True
        # Partida 2 → Prestige 2
        game.total_points = PRESTIGE_2_THRESHOLD * BOOST
        assert game.prestige() is True
        # Partida 3 → Victoria
        game.total_points = VICTORY_THRESHOLD * BOOST
        assert game.check_victory() is True
        assert game.won is True
        assert game.infinite_mode is True

    def test_modo_infinito_no_permite_nuevo_prestige(self):
        """En modo infinito no es posible hacer más prestiges."""
        game = GameState()
        game.total_points = PRESTIGE_1_THRESHOLD * BOOST
        game.prestige()
        game.total_points = PRESTIGE_2_THRESHOLD * BOOST
        game.prestige()
        game.total_points = VICTORY_THRESHOLD * BOOST
        game.check_victory()
        # Intentar un prestige adicional en modo infinito
        assert game.prestige() is False

    def test_high_score_persiste_como_indicador_post_victoria(self):
        """La puntuación máxima se mantiene como referencia en modo infinito."""
        game = GameState()
        for _ in range(1000):
            game.click()
        game.tick()
        hs = game.high_score
        assert hs > 0
        # Hacer más clics debe actualizar el high score
        for _ in range(1000):
            game.click()
        game.tick()
        assert game.high_score >= hs
