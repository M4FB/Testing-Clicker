Feature: Música procedural y gestor de audio
  Como jugador
  Quiero una banda sonora distinta en cada pantalla
  Para que menú, juego y ajustes se sientan diferentes

  Scenario: Las tres pistas son distintas
    Given las tres pistas de música
    Then las tres pistas tienen duraciones distintas

  Scenario: El gestor hace crossfade entre pistas
    Given un gestor de música
    When el gestor reproduce la pista "menu"
    Then la pista actual es "menu"

  Scenario: Cambiar de pista actualiza la actual
    Given un gestor de música
    When el gestor reproduce la pista "menu"
    And el gestor reproduce la pista "game"
    Then la pista actual es "game"

  Scenario: En pausa la música baja de volumen
    Given un gestor de música
    When el gestor reproduce la pista "game"
    And el juego se pausa
    Then el volumen aplicado es menor que el de usuario
