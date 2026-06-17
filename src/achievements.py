"""Sistema de logros.

Cada logro define una condición sobre el GameState (incluye state.stats).
`check(state)` devuelve los logros recién desbloqueados y los marca en
state.achievements para que el guardado los persista.
"""
from src.config import GENERATORS, BOOST

# Claves de los 6 minijuegos (deben coincidir con MinigameBase.KEY)
MINI_KEYS = ["rush", "rain", "simon", "pulse", "pairs", "chain"]


def _all_minis_won(s) -> bool:
    mini = s.stats["mini"]
    return all(mini.get(k, {}).get("won", 0) > 0 for k in MINI_KEYS)


ACHIEVEMENTS = [
    {"id": "primer_clic",  "icon": "●", "name": "El Comienzo",
     "desc": "Haz tu primer clic",
     "cond": lambda s: s.stats["clicks"] >= 1},
    {"id": "clics_100",    "icon": "▲", "name": "Dedo Caliente",
     "desc": "Acumula 100 clics",
     "cond": lambda s: s.stats["clicks"] >= 100},
    {"id": "clics_1000",   "icon": "⚡", "name": "Tormenta de Clics",
     "desc": "Acumula 1 000 clics",
     "cond": lambda s: s.stats["clicks"] >= 1000},
    {"id": "combo_25",     "icon": "→", "name": "En Racha",
     "desc": "Llega a combo ×25",
     "cond": lambda s: s.stats["best_combo"] >= 25},
    {"id": "combo_50",     "icon": "∞", "name": "Imparable",
     "desc": "Llega a combo ×50",
     "cond": lambda s: s.stats["best_combo"] >= 50},
    {"id": "primer_crit",  "icon": "★", "name": "¡Crítico!",
     "desc": "Consigue un clic crítico",
     "cond": lambda s: s.stats["crits"] >= 1},
    {"id": "crit_50",      "icon": "✦", "name": "Lluvia de Críticos",
     "desc": "Consigue 50 clics críticos",
     "cond": lambda s: s.stats["crits"] >= 50},
    {"id": "primer_taller", "icon": "■", "name": "Primer Taller",
     "desc": "Compra tu primer Taller",
     "cond": lambda s: s.generators.get("workshop", 0) >= 1},
    {"id": "imperio",      "icon": "♦", "name": "Imperio Industrial",
     "desc": "Posee 10 de cada generador",
     "cond": lambda s: all(s.generators.get(g["id"], 0) >= 10
                           for g in GENERATORS)},
    {"id": "millonario",   "icon": "◆", "name": "Millonario",
     "desc": f"Acumula {1_000_000 * BOOST:,.0f} puntos".replace(",", " "),
     "cond": lambda s: s.total_points >= 1_000_000 * BOOST},
    {"id": "dorada",       "icon": "☀", "name": "Cazador de Fortuna",
     "desc": "Atrapa una moneda dorada",
     "cond": lambda s: s.stats["golden"] >= 1},
    {"id": "mini_win",     "icon": "♠", "name": "Jugón",
     "desc": "Gana un minijuego",
     "cond": lambda s: s.stats["mini_won"] >= 1},
    {"id": "mini_all",     "icon": "♥", "name": "As de los Minijuegos",
     "desc": "Gana los 6 minijuegos distintos",
     "cond": _all_minis_won},
    {"id": "qte_master",   "icon": "⊕", "name": "Reflejos de Acero",
     "desc": "Completa un QTE",
     "cond": lambda s: s.stats["qte_won"] >= 1},
    {"id": "prestigio_1",  "icon": "↑", "name": "Renacido",
     "desc": "Haz tu primer prestigio",
     "cond": lambda s: s.stats["prestiges"] >= 1},
    {"id": "victoria",     "icon": "⊗", "name": "Leyenda",
     "desc": "Gana el juego",
     "cond": lambda s: s.won},
]


def by_id(aid: str) -> dict:
    return next(a for a in ACHIEVEMENTS if a["id"] == aid)


def unlocked_count(state) -> int:
    return sum(1 for a in ACHIEVEMENTS if state.achievements.get(a["id"]))


def check(state) -> list[dict]:
    """Evalúa todas las condiciones; devuelve los logros recién desbloqueados."""
    new = []
    for a in ACHIEVEMENTS:
        if state.achievements.get(a["id"]):
            continue
        try:
            if a["cond"](state):
                state.achievements[a["id"]] = True
                new.append(a)
        except Exception:
            pass
    return new
