Feature: Nuevas mejoras e integraciones de Clicker Game
  Como jugador
  Quiero comprar el Centro de Investigación, usar mejoras de prestigio y jugar al minijuego de mecanografía
  Para tener una experiencia de juego más profunda y variada

  Scenario: Comprar el Centro de Investigación produce alta cantidad de PPS
    Given el juego está iniciado
    And el jugador tiene fondos para un "research"
    And el jugador alcanzó el umbral de total_points de 50000
    When el jugador compra el generador "research"
    Then el jugador posee 1 unidades de "research"
    And los puntos por segundo son de al menos 5000

  Scenario: La mejora de prestigio Auto-Clicker realiza clics automáticos
    Given el juego está iniciado
    And el jugador tiene la mejora de prestigio "pp_autoclick" comprada
    When transcurre 1 segundo de juego
    Then el total de clics registrados es mayor que cero

  Scenario: La mejora de prestigio Doble o Nada permite críticos de ×50
    Given el juego está iniciado
    And el jugador tiene la mejora de prestigio "pp_double_crit" comprada
    And la probabilidad de crítico es del 100%
    When el jugador hace clic una vez
    Then el valor obtenido es 50 veces el clic base
