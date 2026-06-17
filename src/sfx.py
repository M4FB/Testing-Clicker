"""Efectos de sonido procedurales.

Igual que la música, todo se sintetiza con numpy al primer uso y se cachea.
Si el mixer no está inicializado, play() es un no-op silencioso.

Sonidos: click (3 variantes de tono), buy, upgrade, coin, gem, bomb, error,
tick, win, fail, fanfare, crit, golden, logro, flip,
simon0..simon3 (notas de las cajas de Simón).
"""
import random

import numpy as np
import pygame

_SR = 44100
_cache: dict = {}
_volume = 0.5


def set_volume(v: float) -> None:
    global _volume
    _volume = max(0.0, min(1.0, v))


def get_volume() -> float:
    return _volume


# ── Sintetizadores básicos ────────────────────────────────────────────────────

def _note(freq, dur, amp=1.0, harm=False, decay=8.0):
    """Nota con ataque rápido y caída exponencial."""
    n = int(_SR * dur)
    t = np.linspace(0, dur, n, endpoint=False)
    s = np.sin(2 * np.pi * freq * t)
    if harm:
        s += 0.40 * np.sin(2 * np.pi * freq * 2 * t)
        s += 0.15 * np.sin(2 * np.pi * freq * 3 * t)
    env = np.exp(-t * decay) * np.clip(t / 0.004, 0, 1)
    return amp * s * env


def _sweep(f0, f1, dur, amp=1.0, decay=10.0):
    """Barrido exponencial de frecuencia f0 → f1."""
    n = int(_SR * dur)
    t = np.linspace(0, dur, n, endpoint=False)
    f = f0 * (f1 / f0) ** (t / dur)
    ph = 2 * np.pi * np.cumsum(f) / _SR
    env = np.exp(-t * decay) * np.clip(t / 0.003, 0, 1)
    return amp * np.sin(ph) * env


def _noise(dur, amp=1.0, decay=30.0):
    n = int(_SR * dur)
    t = np.linspace(0, dur, n, endpoint=False)
    return amp * np.random.uniform(-1, 1, n) * np.exp(-t * decay)


def _seq(*parts):
    return np.concatenate(parts)


# ── Definiciones ──────────────────────────────────────────────────────────────

_SIMON_FREQS = [391.995, 329.628, 261.626, 195.998]   # G4 E4 C4 G3 (Simon real)


def _build(name):
    if name.startswith("click"):
        pitch = {"click0": 1.0, "click1": 1.12, "click2": 0.9}[name]
        return _sweep(620 * pitch, 380 * pitch, 0.06, 0.55, decay=38)
    if name == "buy":          # ka-ching
        return _seq(_note(987.77, 0.06, 0.65, harm=True, decay=20),
                    _note(1318.51, 0.28, 0.8, harm=True, decay=9))
    if name == "upgrade":
        return _seq(_note(659.25, 0.07, 0.65, harm=True, decay=16),
                    _note(880.0, 0.26, 0.8, harm=True, decay=8))
    if name == "coin":
        return _seq(_note(1244.51, 0.04, 0.5, harm=True, decay=24),
                    _note(1567.98, 0.16, 0.7, harm=True, decay=12))
    if name == "gem":
        return _seq(_note(1760.0, 0.05, 0.55, harm=True, decay=18),
                    _note(2093.0, 0.2, 0.7, harm=True, decay=10))
    if name == "bomb":
        body  = _sweep(130, 42, 0.26, 0.95, decay=9)
        crack = _noise(0.05, 0.5, decay=50)
        body[:len(crack)] += crack
        return body
    if name == "error":
        return (_note(110, 0.14, 0.5, harm=True, decay=10)
                + _note(98, 0.14, 0.35, harm=True, decay=10))
    if name == "tick":
        return _note(1200, 0.035, 0.45, decay=55)
    if name == "win":
        return _seq(_note(523.25, 0.09, 0.6, harm=True, decay=11),
                    _note(659.25, 0.09, 0.6, harm=True, decay=11),
                    _note(783.99, 0.09, 0.6, harm=True, decay=11),
                    _note(1046.5, 0.3, 0.75, harm=True, decay=6))
    if name == "fail":
        return _seq(_note(392.0, 0.15, 0.55, decay=7),
                    _note(311.13, 0.3, 0.55, decay=6))
    if name == "fanfare":
        chord = (_note(1046.5, 0.5, 0.45, harm=True, decay=4)
                 + _note(1318.51, 0.5, 0.35, harm=True, decay=4)
                 + _note(783.99, 0.5, 0.3, harm=True, decay=4))
        return _seq(_note(523.25, 0.11, 0.6, harm=True, decay=9),
                    _note(659.25, 0.11, 0.6, harm=True, decay=9),
                    _note(783.99, 0.11, 0.6, harm=True, decay=9),
                    chord)
    if name == "crit":          # clic crítico: barrido ascendente + campanada
        return _seq(_sweep(500, 1600, 0.09, 0.7, decay=12),
                    _note(1864.66, 0.3, 0.85, harm=True, decay=7))
    if name == "golden":        # moneda dorada: arpegio brillante
        return _seq(_note(1318.51, 0.06, 0.55, harm=True, decay=16),
                    _note(1567.98, 0.06, 0.6, harm=True, decay=16),
                    _note(2093.0, 0.07, 0.65, harm=True, decay=14),
                    _note(2637.0, 0.24, 0.7, harm=True, decay=9))
    if name == "logro":         # logro: dos campanadas solemnes
        return _seq(_note(783.99, 0.16, 0.6, harm=True, decay=7),
                    _note(1174.66, 0.42, 0.75, harm=True, decay=5))
    if name == "flip":          # carta que se voltea
        return _sweep(300, 720, 0.07, 0.4, decay=26)
    if name.startswith("simon"):
        freq = _SIMON_FREQS[int(name[-1])]
        return _note(freq, 0.3, 0.55, harm=True, decay=6)
    raise KeyError(name)


def _to_sound(au):
    au = np.clip(au, -1.0, 1.0)
    stereo = np.column_stack([au, au])
    return pygame.sndarray.make_sound(np.int16(stereo * 32767 * 0.85))


# ── API ───────────────────────────────────────────────────────────────────────

def play(name: str, vol: float = 1.0) -> None:
    if _volume <= 0 or not pygame.mixer.get_init():
        return
    if name == "click":
        name = f"click{random.randrange(3)}"
    snd = _cache.get(name)
    if snd is None:
        try:
            snd = _to_sound(_build(name))
        except Exception:
            return
        _cache[name] = snd
    snd.set_volume(_volume * max(0.0, min(1.0, vol)))
    snd.play()


def _reset_cache() -> None:
    _cache.clear()
