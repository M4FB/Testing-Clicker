Feature: Sistema de Prestige
  Como jugador
  Quiero reiniciar con bonificaciones permanentes
  Para acelerar partidas futuras

  Background:
    Given el juego está iniciado

  Scenario: Prestige 1 reinicia y multiplica
    Given el jugador alcanzó el umbral del Prestige 1
    When el jugador activa el Prestige
    Then el prestige se realiza con éxito
    And el multiplicador permanente de prestigio es 1.5
    And los puntos actuales se reinician a cero

  Scenario: No se puede hacer prestige sin alcanzar el umbral
    Given el jugador tiene 0 puntos acumulados
    When el jugador intenta hacer prestige
    Then el prestige no ocurre

  Scenario: El Prestige 2 acumula el multiplicador
    Given el jugador completó el Prestige 1
    And el jugador alcanzó el umbral del Prestige 2
    When el jugador activa el Prestige
    Then el multiplicador permanente de prestigio es 3.0

  Scenario: El prestige otorga puntos de prestigio
    Given el jugador alcanzó el umbral del Prestige 1
    When el jugador activa el Prestige
    Then el jugador gana puntos de prestigio
