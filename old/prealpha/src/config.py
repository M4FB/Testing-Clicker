import os

MODE = os.environ.get("GAME_MODE", "demo").lower()
BOOST = 100 if MODE == "demo" else 1

BASE_CLICK_VALUE = 1
PRICE_SCALE = 1.15

# Minijuego: segundos entre apariciones
MINIGAME_COOLDOWN = 30 if MODE == "demo" else 300

GENERATORS = [
    {"id": "worker",   "name": "Trabajador",  "pps": 0.1,  "cost": 15,     "unlock": 0},
    {"id": "workshop", "name": "Taller",       "pps": 0.5,  "cost": 100,    "unlock": 50},
    {"id": "factory",  "name": "Fábrica",      "pps": 2.0,  "cost": 1100,   "unlock": 500},
    {"id": "lab",      "name": "Laboratorio",  "pps": 10.0, "cost": 12000,  "unlock": 5000},
]

CLICK_UPGRADES = [
    {"id": "cu_1", "name": "Mejor dedo",  "cost": 10,   "bonus": 1,  "unlock": 0},
    {"id": "cu_2", "name": "Mano fuerte", "cost": 100,  "bonus": 5,  "unlock": 100},
    {"id": "cu_3", "name": "Guante",      "cost": 1000, "bonus": 20, "unlock": 500},
]

# Umbrales de prestige (en puntos históricos)
PRESTIGE_1_THRESHOLD = 50_000
PRESTIGE_2_THRESHOLD = 500_000
VICTORY_THRESHOLD    = 5_000_000
