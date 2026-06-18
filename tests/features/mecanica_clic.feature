Feature: Mecánica de clic principal
  Como jugador
  Quiero hacer clic para ganar puntos
  Para progresar activamente en el juego

  Background:
    Given el juego está iniciado

  Scenario: Ganar puntos con un solo clic
    When el jugador hace clic una vez
    Then los puntos del jugador son mayores a cero

  Scenario: Acumular puntos con varios clics
    When el jugador hace clic 10 veces
    Then el total acumulado es el valor de clic multiplicado por 10

  Scenario: El total histórico no decrece al gastar puntos
    When el jugador hace clic 5 veces
    And el jugador gasta todos sus puntos en un generador
    Then el total histórico sigue siendo mayor a cero

  Scenario: Comprar una mejora de clic sube el valor por clic
    Given el jugador tiene fondos para la mejora "cu_1"
    When el jugador compra la mejora de clic "cu_1"
    Then el valor por clic supera al valor base

  Scenario: No se puede comprar dos veces la misma mejora
    Given el jugador tiene fondos para la mejora "cu_1"
    When el jugador compra la mejora de clic "cu_1"
    And el jugador intenta comprar la mejora "cu_1" otra vez
    Then la segunda compra falla
