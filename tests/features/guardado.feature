Feature: Guardado de partida y preferencias
  Como jugador
  Quiero que mi progreso y mis ajustes persistan
  Para retomar el juego como lo dejé

  Scenario: La partida se guarda y se recupera intacta
    Given una partida con progreso
    When se guarda y se vuelve a cargar la partida
    Then la partida cargada conserva los puntos y generadores

  Scenario: Las preferencias de volumen persisten
    Given el volumen de música configurado es 0.7
    When se guardan y recargan las preferencias
    Then las preferencias cargadas tienen música 0.7
