Feature: Compra múltiple de generadores
  Como jugador
  Quiero comprar generadores en lotes de 1, 10 o el máximo posible
  Para no repetir decenas de clics en mitad de la partida

  Background:
    Given el juego está iniciado

  Scenario: El coste de un lote coincide con comprar las unidades una a una
    Given el jugador tiene fondos para 10 unidades de "worker"
    Then el coste del lote de 10 "worker" coincide con comprar las unidades una a una

  Scenario: Comprar un lote de 10 con fondos suficientes
    Given el jugador tiene fondos exactos para 10 unidades de "worker"
    When el jugador compra un lote de 10 del generador "worker"
    Then el jugador posee 10 unidades del generador "worker"

  Scenario: Un lote se detiene al agotar los fondos
    Given el jugador tiene fondos exactos para 3 unidades de "worker"
    When el jugador compra un lote de 10 del generador "worker"
    Then el jugador posee 3 unidades del generador "worker"

  Scenario: MAX compra exactamente lo que alcanzan los puntos
    Given el jugador tiene 100000 puntos
    When el jugador compra el máximo posible del generador "worker"
    Then el jugador no puede costear ni una unidad más de "worker"

  Scenario: Un generador bloqueado no admite compra múltiple
    Given el jugador tiene 0 puntos acumulados
    Then el máximo comprable del generador "lab" es 0
