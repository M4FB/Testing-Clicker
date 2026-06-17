"""Guardado/carga de partida en JSON.

El archivo vive en el home del usuario para sobrevivir a `git clean` y a
mover el repo. Los boosts temporales (minijuego/QTE/fiebre dorada) no se
serializan; los efectos permanentes de prestigio se reconstruyen al cargar
a partir de prestige_upgrades.
"""
import json
import os
import time

from src.game import GameState, _new_stats
from src.config import MODE

SAVE_PATH = os.path.expanduser("~/.clicker_game_save.json")
SAVE_VERSION = 2

_SCALAR_FIELDS = [
    "points", "total_points", "click_value", "click_mult",
    "prestige_count", "prestige_multiplier", "prestige_points",
    "won", "infinite_mode", "high_score",
]
_DICT_FIELDS = ["generators", "click_upgrades", "gen_upgrades",
                "prestige_upgrades"]


def save_game(state: GameState, *, elapsed: float = 0.0,
              music_vol: float | None = None, sfx_vol: float | None = None,
              fullscreen: bool | None = None,
              path: str = SAVE_PATH) -> None:
    data = {f: getattr(state, f) for f in _SCALAR_FIELDS}
    for f in _DICT_FIELDS:
        data[f] = getattr(state, f)
    data["gen_mult"]     = state.gen_mult
    data["stats"]        = state.stats
    data["achievements"] = state.achievements
    data["version"]   = SAVE_VERSION
    data["elapsed"]   = elapsed
    data["mode"]      = MODE
    data["saved_at"]  = time.time()
    if music_vol is not None:
        data["music_vol"] = music_vol
    if sfx_vol is not None:
        data["sfx_vol"] = sfx_vol
    if fullscreen is not None:
        data["fullscreen"] = fullscreen
    tmp = path + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(data, fh)
    os.replace(tmp, path)


def save_info(path: str = SAVE_PATH) -> dict | None:
    try:
        with open(path) as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def has_compatible_save(path: str = SAVE_PATH) -> bool:
    """Hay partida guardada y es del mismo modo (demo/full) que el actual."""
    data = save_info(path)
    return bool(data) and data.get("mode") == MODE


def load_game(path: str = SAVE_PATH) -> tuple[GameState | None, dict]:
    """Devuelve (estado, metadatos) o (None, {}) si no hay guardado válido."""
    data = save_info(path)
    if not data or data.get("mode") != MODE:
        return None, {}
    st = GameState()
    for f in _SCALAR_FIELDS:
        if f in data:
            setattr(st, f, data[f])
    # Dicts: solo claves que existan en la config actual (tolera cambios)
    for f in _DICT_FIELDS:
        cur   = getattr(st, f)
        saved = data.get(f, {})
        for k in cur:
            if k in saved:
                cur[k] = saved[k]
    st.gen_mult = {k: float(v) for k, v in data.get("gen_mult", {}).items()}

    # Estadísticas: solo claves conocidas; "mini" se copia entera
    saved_stats = data.get("stats", {})
    st.stats = _new_stats()
    for k in st.stats:
        if k in saved_stats:
            st.stats[k] = saved_stats[k]

    st.achievements = {k: bool(v) for k, v in data.get("achievements", {}).items()}
    st.reapply_prestige_upgrades()
    st._last_tick = time.time()
    return st, data


def delete_save(path: str = SAVE_PATH) -> None:
    try:
        os.remove(path)
    except OSError:
        pass
