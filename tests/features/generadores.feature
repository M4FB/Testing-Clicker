Feature: Generadores de producción pasiva
  Como jugador
  Quiero comprar generadores
  Para producir puntos automáticamente

  Background:
    Given el juego está iniciado

  Scenario: Comprar un generador produce puntos por segundo
    Given el jugador tiene fondos para un "worker"
    When el jugador compra el generador "worker"
    Then el jugador posee 1 unidades de "worker"
    And los puntos por segundo son mayores a cero

  Scenario: No se puede comprar sin fondos
    Given el jugador tiene 0 puntos acumulados
    When el jugador intenta comprar el generador "worker"
    Then la compra del generador falla
    And el jugador posee 0 unidades de "worker"

  Scenario: El precio escala con la cantidad poseída
    Given el jugador tiene fondos para 5 unidades de "worker"
    When el jugador compra 5 unidades de "worker"
    Then el costo del generador "worker" ha escalado

  Scenario: Comprar varias unidades de golpe
    Given el jugador tiene fondos para 3 unidades de "worker"
    When el jugador compra 3 unidades de "worker"
    Then el jugador posee 3 unidades de "worker"
