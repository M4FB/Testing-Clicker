Feature: Sistema de Generadores Automáticos
  Como jugador
  Quiero comprar generadores para producir puntos automáticamente
  Para progresar sin necesidad de hacer clic constantemente

  Background:
    Given el juego está iniciado

  Scenario: Comprar un Trabajador con fondos suficientes
    Given el jugador tiene fondos suficientes para comprar un "worker"
    When el jugador compra el generador "worker"
    Then el jugador posee 1 unidad del generador "worker"
    And los puntos por segundo son mayores a cero

  Scenario: No se puede comprar un generador sin fondos
    Given el jugador tiene 0 puntos
    When el jugador intenta comprar el generador "worker"
    Then la compra del generador falla
    And el jugador sigue teniendo 0 generadores "worker"

  Scenario: El precio escala con la cantidad comprada
    Given el jugador tiene fondos suficientes para comprar un "worker"
    When el jugador compra el generador "worker"
    Then el costo del generador "worker" ha escalado correctamente

  Scenario: Múltiples generadores suman su producción
    Given el jugador tiene fondos para 3 unidades de "worker"
    When el jugador compra 3 unidades del generador "worker"
    Then los puntos por segundo son proporcionales a 3 unidades

  Scenario: Generador bloqueado no se puede comprar
    Given el jugador tiene 0 puntos acumulados
    When el jugador intenta comprar el generador "factory"
    Then la compra del generador falla
