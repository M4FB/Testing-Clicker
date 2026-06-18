Feature: Condición de victoria
  Como jugador
  Quiero una meta final clara
  Para saber cuándo he ganado el juego

  Background:
    Given el juego está iniciado

  Scenario: Alcanzar la victoria tras dos prestiges
    Given el jugador alcanzó el umbral de victoria
    When el juego evalúa la condición de victoria
    Then el juego declara la victoria

  Scenario: La victoria no se dispara dos veces
    Given el jugador alcanzó el umbral de victoria
    When el juego evalúa la condición de victoria
    And el juego vuelve a evaluar la condición de victoria
    Then la victoria no se vuelve a disparar

  Scenario: No hay victoria sin completar los prestiges
    Given el jugador tiene muchos puntos pero 0 prestiges
    When el juego evalúa la condición de victoria
    Then el juego no declara la victoria
