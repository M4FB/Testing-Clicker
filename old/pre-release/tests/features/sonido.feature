Feature: Retroalimentación sonora procedural
  Como jugador
  Quiero que el juego responda con sonidos a mis acciones
  Para recibir confirmación inmediata de lo que ocurre

  Background:
    Given un minijuego listo para jugarse

  Scenario: Todos los efectos de sonido se sintetizan correctamente
    Then cada efecto de sonido definido se genera sin errores

  Scenario: El volumen de sonidos queda acotado al máximo
    When el jugador sube el volumen de sonidos más allá del máximo
    Then el volumen queda limitado al máximo

  Scenario: Reproducir un sonido sin mezclador de audio no rompe el juego
    When se reproduce un sonido sin mezclador inicializado
    Then no ocurre ningún error
