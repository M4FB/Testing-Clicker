# Documento de Requisitos — Clicker Game (Incremental)

> Proyecto: Clicker Game con pytest  
> Versiones: `demo_ver` | `full_ver`  
> Fecha: 2026-06-04

---

## 1. Descripción General

El juego es un clicker incremental de complejidad media, similar a la mitad del contenido de Cookie Clicker. El jugador acumula puntos haciendo clic y comprando mejoras que automatizan la generación de puntos. El juego incluye un sistema de reinicio con bonificaciones permanentes (prestige), un minijuego periódico, y concluye con una condición de victoria real tras el tercer reinicio. Existe una versión demo acelerada y una versión completa de larga duración.

---

## 2. Versiones del Juego

### 2.1 `demo_ver`
- Todos los valores de generación de puntos y costos de mejoras se escalan con un multiplicador de **×100**.
- La duración esperada de una partida completa (hasta la victoria) es de aproximadamente **20 minutos**.
- Permite probar todas las mecánicas del juego sin invertir tiempo prolongado.
- El cooldown del minijuego se reduce a **30 segundos** entre apariciones.

### 2.2 `full_ver`
- Progresión calibrada sin aceleradores artificiales.
- La duración esperada hasta la primera victoria es de **10 a 12 horas**.
- El cooldown del minijuego es de **5 minutos** entre apariciones.

En ambas versiones, el juego muestra claramente al inicio qué versión está activa (`[DEMO]` / `[FULL]`).

---

## 3. Mecánica Principal de Clic

- El jugador dispone de un botón (acción) principal que al activarse suma puntos al contador global.
- El valor base por clic es **1 punto**.
- Este valor puede ser incrementado mediante mejoras de clic manual.
- La interfaz muestra en todo momento:
  - Puntos actuales disponibles.
  - Puntos por clic.
  - Puntos por segundo (generación pasiva).
  - Total histórico de puntos acumulados (incluyendo los gastados).

---

## 4. Sistema de Mejoras (Upgrades)

### 4.1 Mejoras de Clic
Aumentan los puntos obtenidos por cada clic manual. Ejemplos de niveles:
- Mejora 1: +1 punto/clic — costo base: 10 pts
- Mejora 2: +5 puntos/clic — costo base: 100 pts
- Mejora 3: +20 puntos/clic — costo base: 1.000 pts

### 4.2 Generadores Automáticos
Producen puntos por segundo sin intervención del jugador. Cada tipo de generador tiene nombre, descripción, producción base y precio base. Ejemplos de categorías (de menor a mayor):

| Generador | Producción base | Costo base |
|-----------|-----------------|------------|
| Trabajador | 0.1 pts/s | 15 pts |
| Taller | 0.5 pts/s | 100 pts |
| Fábrica | 2 pts/s | 1.100 pts |
| Laboratorio | 10 pts/s | 12.000 pts |
| Centro de investigación | 50 pts/s | 130.000 pts |

### 4.3 Escalado de Precios
El costo de cada generador o mejora escala con la cantidad ya comprada:

```
costo_actual = costo_base × 1.15 ^ cantidad_comprada
```

### 4.4 Desbloqueo Progresivo
Las mejoras y generadores se desbloquean al alcanzar umbrales de puntos históricos acumulados, no de puntos actuales. Esto evita que el jugador se bloquee por gastar puntos.

---

## 5. Sistema de Hitos y Notificaciones

- El juego registra hitos de puntos acumulados (e.g., 100, 1.000, 10.000…).
- Al alcanzar un hito, se notifica al jugador y pueden desbloquearse nuevas mejoras o generadores.
- Se muestra una barra de progreso o indicador numérico hacia el siguiente hito relevante.

---

## 6. Minijuego

- Aparece disponible de forma periódica según el cooldown de la versión activa.
- El jugador tiene una ventana de tiempo limitada para activarlo (si no lo activa, desaparece).
- Mecánica simple de reacción o habilidad (ejemplos válidos: adivinar un número en rango, clic rápido en un objeto que aparece brevemente, secuencia de inputs).
- Recompensa al completarlo exitosamente: **multiplicador temporal ×2 o ×3** sobre la generación total durante **30 segundos**.
- No interrumpe el flujo principal del juego; es completamente opcional.

---

## 7. Sistema de Reinicio (Prestige)

El juego permite exactamente **2 reinicios de progreso** antes de la victoria final. Cada reinicio borra el progreso de puntos y mejoras, pero otorga bonificaciones permanentes.

### 7.1 Primer Reinicio
- Disponible al alcanzar el **umbral de Prestige 1** (definido por balance del juego).
- Recompensa permanente: **multiplicador ×1.5** sobre todos los puntos generados (clic + pasivos).
- El jugador comienza desde cero pero avanza notablemente más rápido.

### 7.2 Segundo Reinicio
- Disponible al alcanzar el **umbral de Prestige 2**.
- Recompensa permanente adicional: **multiplicador ×2** que se acumula sobre el bono del primer reinicio.
- Multiplicador efectivo tras ambos reinicios: ×1.5 × ×2 = **×3** total.
- Al completarse, el juego advierte explícitamente que el siguiente reinicio es el **Reinicio Final** y constituye la condición de victoria.

### 7.3 Límite de Reinicios
- El sistema no permite un tercer reinicio en el sentido de prestige; en cambio, el tercer umbral activa la **condición de victoria**.
- El contador de reinicios disponibles es visible en la interfaz en todo momento.

---

## 8. Condición de Victoria y Modo Post-Victoria

### 8.1 Victoria
- Se activa cuando el jugador alcanza el **umbral final** en su tercera partida (tras los 2 reinicios).
- Se muestra una pantalla de victoria con:
  - Tiempo total de juego acumulado.
  - Puntuación máxima alcanzada.
  - Número de reinicios completados.

### 8.2 Modo Infinito (Post-Victoria)
- Tras la victoria, el jugador puede continuar en un **Modo Infinito** sin condición de fin.
- El objetivo es alcanzar la mayor puntuación posible.
- La puntuación máxima se registra en un archivo local como marcador.
- No hay nuevos reinicios en este modo; los multiplicadores acumulados permanecen activos.

---

## 9. Guardado y Persistencia

- El estado del juego se guarda automáticamente en un archivo local cada **60 segundos** (`full_ver`) o cada **10 segundos** (`demo_ver`).
- Al iniciar, el juego detecta si existe una partida guardada y ofrece continuar o comenzar de nuevo.
- Los datos guardados incluyen: puntos actuales, histórico, mejoras compradas, reinicios completados, multiplicadores activos, puntuación máxima.

---

## 10. Requisitos de Pruebas (pytest)

Todas las mecánicas del juego deben tener cobertura de tests. Los requisitos de testing son parte del proyecto, no opcionales.

### 10.1 Tests Unitarios
- Verificar que el clic base suma correctamente los puntos.
- Verificar que cada mejora de clic incrementa el valor por clic según lo esperado.
- Verificar que cada generador produce la tasa de puntos por segundo correcta.
- Verificar que la fórmula de escalado de precios devuelve el costo correcto para distintas cantidades compradas.
- Verificar que los multiplicadores de prestige se aplican correctamente sobre la generación base.
- Verificar que el minijuego activa y desactiva el multiplicador temporal en los tiempos correctos.

### 10.2 Tests del Sistema de Reinicios
- Verificar que al realizar el Prestige 1 se borran puntos y mejoras, y que el bono ×1.5 queda registrado.
- Verificar que al realizar el Prestige 2 el bono acumulado es ×3 (×1.5 × ×2).
- Verificar que no es posible un tercer reinicio de prestige (el sistema bloquea la acción y activa la victoria).

### 10.3 Tests de Condición de Victoria
- Verificar que la victoria se activa al alcanzar el umbral final en la tercera partida.
- Verificar que el Modo Infinito se habilita correctamente tras la victoria.
- Verificar que el marcador de puntuación máxima se actualiza y persiste.

### 10.4 Tests de Integración
- Simular una sesión completa en `demo_ver` desde 0 puntos hasta la victoria sin intervención manual.
- Verificar que el guardado y carga de partida restauran el estado exacto de la sesión.

---

## 11. Estructura de Archivos Esperada

```
GameTesting/
├── REQUISITOS.md
├── src/
│   ├── game.py          # Lógica principal del juego
│   ├── upgrades.py      # Definición de mejoras y generadores
│   ├── prestige.py      # Sistema de reinicios y bonificaciones
│   ├── minigame.py      # Lógica del minijuego
│   ├── save.py          # Guardado y carga de partida
│   └── config.py        # Constantes y configuración (demo/full)
└── tests/
    ├── test_core.py      # Tests de mecánica principal
    ├── test_upgrades.py  # Tests de mejoras y generadores
    ├── test_prestige.py  # Tests del sistema de reinicios
    ├── test_minigame.py  # Tests del minijuego
    └── test_integration.py  # Tests de sesión completa
```

---

## 12. Restricciones y Decisiones de Diseño

- El juego no requiere interfaz gráfica; puede operarse completamente desde terminal o mediante llamadas a funciones (facilitando los tests con pytest).
- Los umbrales exactos de prestige y victoria se definen en `config.py` para permitir ajuste de balance sin modificar la lógica.
- El factor de aceleración de `demo_ver` (×100) se aplica exclusivamente en `config.py`, sin duplicar lógica de juego.
- El sistema de reinicios está estrictamente limitado a 2; no debe ser extensible sin cambio explícito de diseño.
