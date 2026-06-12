Feature: Minijuegos con recompensa proporcional al desempeño
  Como jugador
  Quiero minijuegos de habilidad cuya recompensa dependa de cómo juegue
  Para que jugarlos bien valga la pena

  Background:
    Given un minijuego listo para jugarse

  Scenario: Fiebre Dorada premia una buena puntuación
    Given una partida de Fiebre Dorada con 8 monedas atrapadas
    When termina el tiempo del minijuego
    Then el minijuego otorga una recompensa
    And el multiplicador crece con la puntuación

  Scenario: Fiebre Dorada sin la puntuación mínima no premia
    Given una partida de Fiebre Dorada con 1 monedas atrapadas
    When termina el tiempo del minijuego
    Then el minijuego no otorga recompensa

  Scenario: Simón Dice premia completar las 3 rondas con el boost máximo
    When el jugador repite correctamente las 3 secuencias de Simón
    Then la recompensa es el boost máximo de Simón

  Scenario: Simón Dice da premio parcial al fallar tras una ronda completa
    When el jugador completa una ronda de Simón y falla la siguiente
    Then el minijuego otorga una recompensa

  Scenario: Pulso Perfecto premia la precisión total con el boost máximo
    When el jugador detiene el marcador en el centro las 3 rondas
    Then la recompensa es el boost máximo de Pulso

  Scenario: Lluvia Dorada castiga atrapar bombas
    Given una partida de Lluvia Dorada
    When la cesta atrapa una bomba
    Then la puntuación de Lluvia Dorada baja
