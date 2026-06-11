"""Generador de música ambiente procedural para Clicker Game.

Produce un loop de ~12 s en C menor con tres capas:
  - Bajo (onda triangular, notas por beat)
  - Pad de acordes (senos suaves, un acorde por compás)
  - Arpegio chiptune (onda cuadrada baja en armónicos, corcheas)
Más dos ecos simples para dar sensación de espacio.
"""
import numpy as np
import pygame

_SR = 44100   # Hz

# ── Formas de onda ────────────────────────────────────────────────────────────

def _sine(f: float, t: np.ndarray) -> np.ndarray:
    return np.sin(2 * np.pi * f * t)

def _tri(f: float, t: np.ndarray) -> np.ndarray:
    p = (f * t) % 1.0
    return 2.0 * np.abs(2.0 * p - 1.0) - 1.0

def _sqr(f: float, t: np.ndarray) -> np.ndarray:
    """Onda cuadrada baja en armónicos (suena chiptune-suave)."""
    s = _sine(f, t)
    s += 0.333 * _sine(3 * f, t)
    s += 0.200 * _sine(5 * f, t)
    s += 0.143 * _sine(7 * f, t)
    return s * 0.637

def _ar(t: np.ndarray, attack: float, release: float, total: float) -> np.ndarray:
    """Envolvente Attack-Release simple."""
    env = np.ones_like(t)
    a = t < attack
    env[a] = t[a] / (attack + 1e-9)
    r = t > total - release
    env[r] = np.clip((total - t[r]) / (release + 1e-9), 0, 1)
    return np.clip(env, 0, 1)

# ── Generador principal ───────────────────────────────────────────────────────

def generate_loop(duration: float = 12.0) -> np.ndarray:
    """Devuelve un array int16 stereo con forma (N, 2)."""
    n  = int(_SR * duration)
    t  = np.linspace(0, duration, n, endpoint=False)
    au = np.zeros(n, dtype=np.float64)

    # Frecuencias (Hz) — escala de Do menor
    C2,  G2  = 65.41, 98.00
    Ab3, Bb3 = 207.65, 233.08
    C4,  Eb4, F4, G4 = 261.63, 311.13, 349.23, 392.00
    Ab4, C5  = 415.30, 523.25
    G3       = 196.00

    bar  = duration / 4   # duración de un compás (3 s)
    beat = bar / 4        # duración de un tiempo (0.75 s)

    # ── Capa 1: Bajo triangular, un tiempo por nota ───────────────────────
    bass_notes = [C2, C2, G2, C2,   C2, C2, G2, C2,
                  C2, C2, G2, C2,   C2, G2, C2, G2]
    for bi, freq in enumerate(bass_notes):
        t0 = bi * beat
        m  = (t >= t0) & (t < t0 + beat)
        if not m.any():
            continue
        tl  = t[m] - t0
        env = _ar(tl, beat * 0.04, beat * 0.25, beat)
        au[m] += 0.22 * env * _tri(freq, tl)

    # ── Capa 2: Pad de acordes, un acorde por compás ──────────────────────
    chords = [
        [C4, Eb4, G4],         # Cm
        [C4, Eb4, G4],         # Cm
        [Ab3, C4, Eb4],        # Ab
        [C4, Eb4, G4],         # Cm
    ]
    for bi, chord in enumerate(chords):
        t0 = bi * bar
        m  = (t >= t0) & (t < t0 + bar)
        if not m.any():
            continue
        tl  = t[m] - t0
        env = _ar(tl, bar * 0.18, bar * 0.28, bar)
        for freq in chord:
            au[m] += 0.055 * env * _sine(freq, tl)
            au[m] += 0.020 * env * _sine(freq * 2, tl)

    # ── Capa 3: Arpegio chiptune, corcheas (32 notas) ────────────────────
    arp = [
        C4,  Eb4, G4,  C5,   G4,  Eb4, C4,  G3,   # compás 1 (Cm ↑↓)
        C4,  G4,  Eb4, G4,   C4,  Eb4, G4,  C4,   # compás 2 (Cm variación)
        Ab3, C4,  Eb4, Ab3,  C4,  Eb4, Ab3, C4,   # compás 3 (Ab)
        G3,  Bb3, C4,  Eb4,  G4,  Eb4, C4,  G3,   # compás 4 (resolución)
    ]
    nd = duration / len(arp)
    for i, freq in enumerate(arp):
        t0 = i * nd
        m  = (t >= t0) & (t < t0 + nd)
        if not m.any():
            continue
        tl  = t[m] - t0
        env = np.exp(-tl * 3.5) * np.clip(tl / 0.012, 0, 1)
        au[m] += 0.068 * env * _sqr(freq, tl)

    # ── Capa 4: Destellos agudos (muy suaves) ────────────────────────────
    sparks = [(bar * 0.5, C5 * 2), (bar * 1.5, G4 * 2),
              (bar * 2.5, Eb4 * 2), (bar * 3.5, C5 * 2)]
    for t0, freq in sparks:
        dur = beat * 0.3
        m   = (t >= t0) & (t < t0 + dur)
        if not m.any():
            continue
        tl  = t[m] - t0
        env = np.exp(-tl * 12.0) * np.clip(tl / 0.008, 0, 1)
        au[m] += 0.022 * env * _sine(freq, tl)

    # ── Eco simple (sensación de espacio) ────────────────────────────────
    for delay_ms, decay in [(75, 0.24), (155, 0.11)]:
        ds = int(_SR * delay_ms / 1000)
        if ds < n:
            au[ds:] += decay * au[:-ds]

    # ── Crossfade inicio/fin para loop sin clic ───────────────────────────
    fade = int(_SR * 0.08)
    au[:fade]  *= np.linspace(0, 1, fade)
    au[-fade:] *= np.linspace(1, 0, fade)

    # ── Normalizar ────────────────────────────────────────────────────────
    peak = np.max(np.abs(au))
    if peak > 0:
        au = au / peak * 0.72

    stereo = np.column_stack([au, au])
    return np.int16(stereo * 32767)


_cached: "pygame.mixer.Sound | None" = None


def get_music_sound() -> "pygame.mixer.Sound":
    """Devuelve el Sound generado (lo crea solo la primera vez)."""
    global _cached
    if _cached is None:
        arr = generate_loop()
        _cached = pygame.sndarray.make_sound(arr)
    return _cached
