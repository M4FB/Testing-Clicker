Feature: Sistema de Prestige (Reinicio con Bonificación)
  Como jugador
  Quiero reiniciar mi progreso con bonificaciones permanentes
  Para avanzar más rápido en futuras partidas

  Background:
    Given el juego está iniciado

  Scenario: Prestige no disponible sin alcanzar el umbral
    Given el jugador tiene 0 puntos acumulados
    When el jugador intenta hacer prestige
    Then el prestige no ocurre
    And el contador de prestiges sigue en 0

  Scenario: Primer prestige disponible al alcanzar el umbral
    Given el jugador ha acumulado puntos suficientes para el Prestige 1
    When el jugador activa el Prestige 1
    Then el prestige ocurre exitosamente
    And el multiplicador permanente es 1.5
    And los puntos actuales se reinician a cero

  Scenario: Prestige reinicia generadores y mejoras
    Given el jugador ha acumulado puntos suficientes para el Prestige 1
    And el jugador tiene fondos suficientes para comprar un "worker"
    When el jugador compra el generador "worker"
    And el jugador activa el Prestige 1
    Then el jugador tiene 0 unidades de "worker" tras el reinicio

  Scenario: Segundo prestige acumula multiplicador total de 3x
    Given el jugador ha completado el Prestige 1
    And el jugador ha acumulado puntos suficientes para el Prestige 2
    When el jugador activa el Prestige 2
    Then el multiplicador total permanente es 3.0

  Scenario: No es posible un tercer prestige
    Given el jugador ha completado los 2 prestiges
    When el jugador intenta hacer prestige con muchos puntos
    Then el prestige no ocurre
    And el contador de prestiges sigue en 2
