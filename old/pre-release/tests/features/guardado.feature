Feature: Guardado y carga de partida
  Como jugador
  Quiero que mi progreso se guarde y se pueda continuar
  Para no perder la partida al cerrar el juego

  Scenario: Guardar y cargar conserva el progreso
    Given el juego está iniciado
    And una partida avanzada con generadores y mejoras
    When el jugador guarda la partida
    And el jugador carga la partida guardada
    Then el estado cargado tiene los mismos puntos
    And el estado cargado tiene los mismos generadores
    And el estado cargado produce los mismos puntos por segundo

  Scenario: Sin archivo de guardado no hay partida que continuar
    Given no existe ningún archivo de guardado
    Then no hay partida guardada compatible

  Scenario: Un guardado de otro modo de juego no es compatible
    Given el juego está iniciado
    And una partida guardada en otro modo de juego
    Then no hay partida guardada compatible

  Scenario: Borrar el guardado lo hace incompatible
    Given el juego está iniciado
    And una partida avanzada con generadores y mejoras
    When el jugador guarda la partida
    And el jugador borra la partida guardada
    Then no hay partida guardada compatible

  Scenario: El tiempo jugado se conserva en los metadatos
    Given el juego está iniciado
    And una partida avanzada con generadores y mejoras
    When el jugador guarda la partida tras 300 segundos de juego
    And el jugador carga la partida guardada
    Then los metadatos indican 300 segundos jugados
