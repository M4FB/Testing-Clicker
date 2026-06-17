Feature: Condición de Victoria y Modo Infinito
  Como jugador
  Quiero completar el juego al alcanzar el objetivo final
  Para sentir que he ganado y poder seguir compitiendo por puntuación

  Background:
    Given el juego está iniciado

  Scenario: Victoria no se activa sin haber completado los prestiges
    Given el jugador tiene muchísimos puntos pero 0 prestiges
    When el juego evalúa la condición de victoria
    Then el juego no declara la victoria

  Scenario: Victoria se activa tras dos prestiges y alcanzar el umbral final
    Given el jugador ha completado los 2 prestiges
    And el jugador ha alcanzado el umbral de victoria
    When el juego evalúa la condición de victoria
    Then el juego declara la victoria
    And el modo infinito queda desbloqueado

  Scenario: La victoria solo se dispara una vez
    Given el jugador ha completado los 2 prestiges
    And el jugador ha alcanzado el umbral de victoria
    When el juego evalúa la condición de victoria
    And el juego vuelve a evaluar la condición de victoria
    Then la segunda evaluación no vuelve a disparar la victoria

  Scenario: El minijuego activa un multiplicador temporal
    When el jugador activa el minijuego con multiplicador 2.0
    Then el multiplicador de minijuego es 2.0
    And los puntos por segundo se duplican respecto a la base

  Scenario: El multiplicador de minijuego expira con el tiempo
    When el jugador activa el minijuego con duración de 0 segundos
    And pasa el tiempo suficiente
    Then el minijuego ya no está activo
    And el multiplicador de minijuego vuelve a 1.0
