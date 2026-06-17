Feature: Mecánica de Clic Principal
  Como jugador
  Quiero hacer clic para ganar puntos
  Para progresar activamente en el juego

  Background:
    Given el juego está iniciado

  Scenario: Ganar puntos con un solo clic
    When el jugador hace clic una vez
    Then los puntos del jugador son mayores a cero

  Scenario: Acumular puntos con múltiples clics
    When el jugador hace clic 10 veces
    Then el total acumulado es igual al valor de clic por 10

  Scenario: El historial total no decrece al gastar puntos
    When el jugador hace clic 5 veces
    And el jugador gasta todos sus puntos comprando un generador
    Then el total histórico sigue siendo mayor a cero

  Scenario: Comprar mejora de clic aumenta el valor por clic
    Given el jugador tiene suficientes puntos para la mejora "cu_1"
    When el jugador compra la mejora de clic "cu_1"
    Then el valor por clic aumenta respecto al valor base

  Scenario: No se puede comprar una mejora ya adquirida
    Given el jugador tiene suficientes puntos para la mejora "cu_1"
    When el jugador compra la mejora de clic "cu_1"
    And el jugador intenta comprar la mejora "cu_1" de nuevo
    Then la segunda compra falla
