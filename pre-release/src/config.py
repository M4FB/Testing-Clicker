import os

MODE  = os.environ.get("GAME_MODE", "demo").lower()
BOOST = 100 if MODE == "demo" else 1

BASE_CLICK_VALUE = 1
PRICE_SCALE      = 1.15

# Segundos entre apariciones de minijuego / QTE
MINIGAME_COOLDOWN = 30  if MODE == "demo" else 300
QTE_COOLDOWN      = 90  if MODE == "demo" else 600

GENERATORS = [
    {"id": "worker",   "name": "Trabajador",  "pps": 0.1,  "cost": 15,    "unlock": 0},
    {"id": "workshop", "name": "Taller",       "pps": 0.5,  "cost": 100,   "unlock": 50},
    {"id": "factory",  "name": "Fábrica",      "pps": 2.0,  "cost": 1100,  "unlock": 500},
    {"id": "lab",      "name": "Laboratorio",  "pps": 10.0, "cost": 12000, "unlock": 5000},
]

# ─── Mejoras de clic (15) ─────────────────────────────────────────────────────
# Campos:
#   bonus        → suma flat al click_value (antes de BOOST; se multiplica en game.py)
#   mult         → (opcional) multiplica click_mult acumulativo
#   unlock_after → lista de IDs; se desbloquea si CUALQUIERA está comprado
#                  (vacío = siempre visible)
#   unlock       → LEGACY: umbral de total_points (vacío = 0)
#
# Árbol: comprar N revela N+1 y N+2:
#   unlock_after de cu_N  = [cu_(N-2), cu_(N-1)]
# ─────────────────────────────────────────────────────────────────────────────
CLICK_UPGRADES = [
    # ── Tier 0 ──────────────────────────────────────────────────────────────
    {"id": "cu_1",  "icon": "●", "name": "Mejor dedo",        "bonus": 1,      "cost": 10,
     "unlock": 0,  "unlock_after": []},
    # ── Tier 1 (tras cu_1) ──────────────────────────────────────────────────
    {"id": "cu_2",  "icon": "▲", "name": "Mano fuerte",        "bonus": 5,      "cost": 100,
     "unlock": 0,  "unlock_after": ["cu_1"]},
    {"id": "cu_3",  "icon": "◆", "name": "Guante",             "bonus": 20,     "cost": 1_000,
     "unlock": 0,  "unlock_after": ["cu_1", "cu_2"]},
    # ── Tier 2 (tras cu_2 / cu_3) ───────────────────────────────────────────
    {"id": "cu_4",  "icon": "⚡", "name": "Dedo Biónico",       "bonus": 100,    "cost": 5_000,
     "unlock": 0,  "unlock_after": ["cu_2", "cu_3"]},
    {"id": "cu_5",  "icon": "★", "name": "Toque de Oro",       "mult":  1.5,    "cost": 8_000,
     "unlock": 0,  "unlock_after": ["cu_3", "cu_4"]},
    # ── Tier 3 ──────────────────────────────────────────────────────────────
    {"id": "cu_6",  "icon": "■", "name": "Exoesqueleto",       "bonus": 200,    "cost": 15_000,
     "unlock": 0,  "unlock_after": ["cu_4", "cu_5"]},
    {"id": "cu_7",  "icon": "⊕", "name": "Eco Cuántico",       "mult":  2.0,    "cost": 25_000,
     "unlock": 0,  "unlock_after": ["cu_5", "cu_6"]},
    # ── Tier 4 ──────────────────────────────────────────────────────────────
    {"id": "cu_8",  "icon": "→", "name": "Sinergia Neuronal",  "bonus": 500,    "cost": 80_000,
     "unlock": 0,  "unlock_after": ["cu_6", "cu_7"]},
    {"id": "cu_9",  "icon": "♦", "name": "Zona de Flow",       "mult":  2.5,    "cost": 150_000,
     "unlock": 0,  "unlock_after": ["cu_7", "cu_8"]},
    # ── Tier 5 ──────────────────────────────────────────────────────────────
    {"id": "cu_10", "icon": "♠", "name": "Implante Cósmico",   "bonus": 2_000,  "cost": 400_000,
     "unlock": 0,  "unlock_after": ["cu_8", "cu_9"]},
    {"id": "cu_11", "icon": "♥", "name": "Resonancia",         "mult":  3.0,    "cost": 800_000,
     "unlock": 0,  "unlock_after": ["cu_9", "cu_10"]},
    # ── Tier 6 ──────────────────────────────────────────────────────────────
    {"id": "cu_12", "icon": "↑", "name": "Trascendencia",      "bonus": 5_000,  "cost": 2_000_000,
     "unlock": 0,  "unlock_after": ["cu_10", "cu_11"]},
    {"id": "cu_13", "icon": "∞", "name": "Clic Infinito",      "mult":  4.0,    "cost": 5_000_000,
     "unlock": 0,  "unlock_after": ["cu_11", "cu_12"]},
    # ── Tier 7 ──────────────────────────────────────────────────────────────
    {"id": "cu_14", "icon": "⊗", "name": "Paradoja Temporal",  "bonus": 20_000, "mult": 2.0, "cost": 15_000_000,
     "unlock": 0,  "unlock_after": ["cu_12", "cu_13"]},
    {"id": "cu_15", "icon": "★", "name": "Dedo de Dios",       "bonus": 50_000, "mult": 5.0, "cost": 50_000_000,
     "unlock": 0,  "unlock_after": ["cu_13", "cu_14"]},
]

# ─── Mejoras de generadores (30) ─────────────────────────────────────────────
# Campos:
#   target       → "all" | gen_id concreto
#   mult         → multiplicador a aplicar sobre target
#   unlock_after → lista de IDs de GEN_UPGRADES; todos deben estar comprados
#   unlock_own   → dict {gen_id: min_count}; debe poseer al menos esa cantidad
# ─────────────────────────────────────────────────────────────────────────────
GEN_UPGRADES = [
    # ── Globales (×all) ─────────────────────────────────────────────────────
    {"id": "gu_g1", "icon": "⚡", "name": "Engranajes",          "target": "all", "mult": 1.5,
     "cost": 500,         "unlock_after": [],     "unlock_own": {}},
    {"id": "gu_g2", "icon": "■", "name": "Cadena de Montaje",   "target": "all", "mult": 1.5,
     "cost": 5_000,       "unlock_after": ["gu_g1"], "unlock_own": {}},
    {"id": "gu_g3", "icon": "◆", "name": "IA Gestora",          "target": "all", "mult": 2.0,
     "cost": 50_000,      "unlock_after": ["gu_g2"], "unlock_own": {}},
    {"id": "gu_g4", "icon": "★", "name": "Modo Turbo",          "target": "all", "mult": 2.0,
     "cost": 500_000,     "unlock_after": ["gu_g3"], "unlock_own": {}},
    {"id": "gu_g5", "icon": "∞", "name": "Megaboost",           "target": "all", "mult": 3.0,
     "cost": 5_000_000,   "unlock_after": ["gu_g4"], "unlock_own": {}},
    {"id": "gu_g6", "icon": "⊕", "name": "Singularidad Prod.",  "target": "all", "mult": 5.0,
     "cost": 50_000_000,  "unlock_after": ["gu_g5"], "unlock_own": {}},

    # ── Worker ──────────────────────────────────────────────────────────────
    {"id": "gu_w1", "icon": "●", "name": "Cafeína",             "target": "worker", "mult": 2.0,
     "cost": 50,          "unlock_after": [],     "unlock_own": {"worker": 1}},
    {"id": "gu_w2", "icon": "▲", "name": "Horas Extra",         "target": "worker", "mult": 2.0,
     "cost": 500,         "unlock_after": ["gu_w1"], "unlock_own": {}},
    {"id": "gu_w3", "icon": "⚡", "name": "Exotraje Worker",     "target": "worker", "mult": 3.0,
     "cost": 50_000,      "unlock_after": ["gu_w2"], "unlock_own": {}},
    {"id": "gu_w4", "icon": "★", "name": "Implante Worker",     "target": "worker", "mult": 4.0,
     "cost": 500_000,     "unlock_after": ["gu_w3"], "unlock_own": {}},
    {"id": "gu_w5", "icon": "∞", "name": "Clon Cuántico",       "target": "worker", "mult": 5.0,
     "cost": 5_000_000,   "unlock_after": ["gu_w4"], "unlock_own": {}},

    # ── Workshop ─────────────────────────────────────────────────────────────
    {"id": "gu_ws1", "icon": "◆", "name": "Herramientas Pro",   "target": "workshop", "mult": 2.0,
     "cost": 300,         "unlock_after": [],       "unlock_own": {"workshop": 1}},
    {"id": "gu_ws2", "icon": "■", "name": "Automatización",     "target": "workshop", "mult": 2.0,
     "cost": 3_000,       "unlock_after": ["gu_ws1"], "unlock_own": {}},
    {"id": "gu_ws3", "icon": "⊕", "name": "Robótica Avanzada",  "target": "workshop", "mult": 3.0,
     "cost": 300_000,     "unlock_after": ["gu_ws2"], "unlock_own": {}},
    {"id": "gu_ws4", "icon": "→", "name": "Taller Cuántico",    "target": "workshop", "mult": 4.0,
     "cost": 3_000_000,   "unlock_after": ["gu_ws3"], "unlock_own": {}},
    {"id": "gu_ws5", "icon": "★", "name": "Mega Taller",        "target": "workshop", "mult": 5.0,
     "cost": 30_000_000,  "unlock_after": ["gu_ws4"], "unlock_own": {}},

    # ── Factory ─────────────────────────────────────────────────────────────
    {"id": "gu_f1", "icon": "■", "name": "Mantenimiento+",      "target": "factory", "mult": 2.0,
     "cost": 2_000,       "unlock_after": [],     "unlock_own": {"factory": 1}},
    {"id": "gu_f2", "icon": "⚡", "name": "Línea Turbo",         "target": "factory", "mult": 2.0,
     "cost": 20_000,      "unlock_after": ["gu_f1"], "unlock_own": {}},
    {"id": "gu_f3", "icon": "◆", "name": "Nano-Fab",            "target": "factory", "mult": 3.0,
     "cost": 2_000_000,   "unlock_after": ["gu_f2"], "unlock_own": {}},
    {"id": "gu_f4", "icon": "★", "name": "Hiperfábrica",        "target": "factory", "mult": 4.0,
     "cost": 20_000_000,  "unlock_after": ["gu_f3"], "unlock_own": {}},
    {"id": "gu_f5", "icon": "∞", "name": "Fábrica Oscura",      "target": "factory", "mult": 5.0,
     "cost": 200_000_000, "unlock_after": ["gu_f4"], "unlock_own": {}},

    # ── Lab ─────────────────────────────────────────────────────────────────
    {"id": "gu_l1", "icon": "⊕", "name": "Reactivo Mejorado",   "target": "lab", "mult": 2.0,
     "cost": 20_000,      "unlock_after": [],     "unlock_own": {"lab": 1}},
    {"id": "gu_l2", "icon": "◆", "name": "IA de Síntesis",      "target": "lab", "mult": 2.0,
     "cost": 200_000,     "unlock_after": ["gu_l1"], "unlock_own": {}},
    {"id": "gu_l3", "icon": "★", "name": "Cómputo Cuántico",    "target": "lab", "mult": 3.0,
     "cost": 20_000_000,  "unlock_after": ["gu_l2"], "unlock_own": {}},
    {"id": "gu_l4", "icon": "∞", "name": "Omega Lab",           "target": "lab", "mult": 4.0,
     "cost": 200_000_000, "unlock_after": ["gu_l3"], "unlock_own": {}},
    {"id": "gu_l5", "icon": "⊗", "name": "Singularidad Cient.", "target": "lab", "mult": 6.0,
     "cost": 2_000_000_000, "unlock_after": ["gu_l4"], "unlock_own": {}},

    # ── Sinergia / especiales ────────────────────────────────────────────────
    {"id": "gu_sp1", "icon": "♦", "name": "Sinergia Inicial",   "target": "all", "mult": 2.0,
     "cost": 1_000,       "unlock_after": [],       "unlock_own": {"worker": 5}},
    {"id": "gu_sp2", "icon": "♠", "name": "Industrialismo",     "target": "all", "mult": 2.0,
     "cost": 10_000,      "unlock_after": [],       "unlock_own": {"workshop": 3}},
    {"id": "gu_sp3", "icon": "♥", "name": "Megacomplejo",       "target": "all", "mult": 2.0,
     "cost": 100_000,     "unlock_after": [],       "unlock_own": {"factory": 2}},
    {"id": "gu_sp4", "icon": "★", "name": "El Gran Todo",       "target": "all", "mult": 3.0,
     "cost": 5_000_000,   "unlock_after": ["gu_g3"], "unlock_own": {"lab": 1}},
]

# Umbrales de prestige
PRESTIGE_1_THRESHOLD = 50_000
PRESTIGE_2_THRESHOLD = 500_000
VICTORY_THRESHOLD    = 5_000_000
