"""Generador de música ambiente procedural para Clicker Game.

Produce un loop de ~12 s en C menor con tres capas:
  - Bajo (onda triangular, notas por beat)
  - Pad de acordes (senos suaves, un acorde por compás)
  - Arpegio chiptune (onda cuadrada baja en armónicos, corcheas)
Más dos ecos simples para dar sensación de espacio.
"""
import random
import threading

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

def generate_loop(duration: float = 12.0, seed: int | None = None) -> np.ndarray:
    """Devuelve un array int16 stereo con forma (N, 2).

    `seed` introduce variación procedural: con la misma semilla el resultado
    es idéntico (reproducible para tests); con None se usa la variante base.
    """
    rng = random.Random(seed) if seed is not None else None
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
    # Varias variantes melódicas; la semilla elige una (None = la primera).
    arp_variants = [
        [C4,  Eb4, G4,  C5,   G4,  Eb4, C4,  G3,
         C4,  G4,  Eb4, G4,   C4,  Eb4, G4,  C4,
         Ab3, C4,  Eb4, Ab3,  C4,  Eb4, Ab3, C4,
         G3,  Bb3, C4,  Eb4,  G4,  Eb4, C4,  G3],
        [C4,  G4,  Eb4, C5,   Eb4, G4,  C4,  Eb4,
         G3,  C4,  G4,  Eb4,  C4,  G4,  C5,  G4,
         Ab3, Eb4, C4,  Ab3,  Eb4, C4,  Ab3, Eb4,
         G3,  C4,  Bb3, G4,   Eb4, C4,  G3,  C4],
        [G3,  C4,  Eb4, G4,   C5,  G4,  Eb4, C4,
         Eb4, G4,  C5,  G4,   Eb4, C4,  G3,  Eb4,
         C4,  Ab3, Eb4, C4,   Ab3, Eb4, C4,  Ab3,
         Eb4, G3,  Bb3, C4,   Eb4, G4,  Eb4, C4],
    ]
    arp = rng.choice(arp_variants) if rng else arp_variants[0]
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


# ── Música del menú ─────────────────────────────────────────────────────────
# Pieza deliberadamente distinta a la del juego: Fa mayor (luminosa) en vez
# de Do menor, tempo más lento, pad etéreo con campanas y eco amplio. Da una
# sensación de calma/portada frente al pulso "chiptune" del juego.

def generate_menu_loop(duration: float = 16.0, seed: int | None = None) -> np.ndarray:
    """Loop ambiente para el menú principal. Array int16 stereo (N, 2)."""
    rng = random.Random(seed) if seed is not None else None
    n  = int(_SR * duration)
    t  = np.linspace(0, duration, n, endpoint=False)
    au = np.zeros(n, dtype=np.float64)

    # Frecuencias (Hz) — escala de Fa mayor
    F2,  A2,  Bb2, C3 = 87.31, 110.00, 116.54, 130.81
    D4,  E4,  F4,  G4 = 293.66, 329.63, 349.23, 392.00
    A3,  C4          = 220.00, 261.63
    A4,  Bb4, C5, F5 = 440.00, 466.16, 523.25, 698.46

    bar = duration / 4    # 4 s por compás (la mitad de rápido que el juego)

    # ── Capa 1: Pad de acordes Maj7 + sub-bajo suave (uno por compás) ─────
    # Progresión Fmaj7 – Am7 – Bbmaj7 – C : cálida y resolutiva.
    chords = [
        [F4, A4, C5, E4],     # Fmaj7
        [E4, A4, C5, E4],     # Am7
        [D4, F4, A4, Bb4],    # Bbmaj7
        [E4, G4, C5, Bb4],    # C7
    ]
    roots = [F2, A2, Bb2, C3]
    for bi, chord in enumerate(chords):
        t0 = bi * bar
        m  = (t >= t0) & (t < t0 + bar)
        if not m.any():
            continue
        tl   = t[m] - t0
        penv = _ar(tl, bar * 0.30, bar * 0.42, bar)   # ataque lento = pad
        for freq in chord:
            au[m] += 0.040 * penv * _sine(freq, tl)
            au[m] += 0.010 * penv * _sine(freq * 2, tl)
        renv = _ar(tl, bar * 0.10, bar * 0.45, bar)
        au[m] += 0.13 * renv * _tri(roots[bi], tl)

    # ── Capa 2: Arpegio campana (senos con resonancia que se solapa) ──────
    arp_variants = [
        [F4, A4, C5, A4,   E4, A4, C5, E4,   D4, F4, A4, F4,   E4, G4, C5, G4],
        [C5, A4, F4, A4,   C5, E4, A4, E4,   A4, F4, D4, F4,   C5, G4, E4, G4],
        [F4, C5, A4, F4,   A4, C5, E4, A4,   D4, A4, F4, A4,   G4, C5, E4, G4],
    ]
    arp = rng.choice(arp_variants) if rng else arp_variants[0]
    nd = duration / len(arp)
    for i, freq in enumerate(arp):
        t0 = i * nd
        m  = (t >= t0) & (t < t0 + nd * 1.7)          # cola que resuena
        if not m.any():
            continue
        tl  = t[m] - t0
        env = np.exp(-tl * 2.1) * np.clip(tl / 0.010, 0, 1)
        au[m] += 0.046 * env * _sine(freq, tl)
        au[m] += 0.010 * env * _sine(freq * 2, tl)

    # ── Capa 3: Destello agudo lento, medio compás ───────────────────────
    for bi in range(4):
        t0  = bi * bar + bar * 0.5
        dur = bar * 0.5
        m   = (t >= t0) & (t < t0 + dur)
        if not m.any():
            continue
        tl  = t[m] - t0
        env = np.exp(-tl * 4.0) * np.clip(tl / 0.02, 0, 1)
        au[m] += 0.016 * env * _sine(F5, tl)

    # ── Eco amplio (más espacioso que el juego) ──────────────────────────
    for delay_ms, decay in [(190, 0.30), (380, 0.17)]:
        ds = int(_SR * delay_ms / 1000)
        if ds < n:
            au[ds:] += decay * au[:-ds]

    # ── Crossfade + normalizar ───────────────────────────────────────────
    fade = int(_SR * 0.10)
    au[:fade]  *= np.linspace(0, 1, fade)
    au[-fade:] *= np.linspace(1, 0, fade)
    peak = np.max(np.abs(au))
    if peak > 0:
        au = au / peak * 0.64

    stereo = np.column_stack([au, au])
    return np.int16(stereo * 32767)


# ── Música de la pantalla de ajustes ────────────────────────────────────────
# Tercera pieza, distinta de las otras dos: minimalista y "técnica". Drone
# grave con trémolo lento + blips dispersos en pentatónica de La menor.

def generate_config_loop(duration: float = 14.0, seed: int | None = None) -> np.ndarray:
    """Loop ambiente para la pantalla de ajustes. Array int16 stereo (N, 2)."""
    rng = random.Random(seed) if seed is not None else None
    n  = int(_SR * duration)
    t  = np.linspace(0, duration, n, endpoint=False)
    au = np.zeros(n, dtype=np.float64)

    A2, E3 = 110.00, 164.81
    A3, C4, D4, E4, G4, A4, C5 = 220.00, 261.63, 293.66, 329.63, 392.00, 440.00, 523.25
    penta = [A3, C4, D4, E4, G4, A4, C5]

    # ── Drone sostenido con trémolo lento ────────────────────────────────
    trem = 0.80 + 0.20 * np.sin(2 * np.pi * 0.12 * t)
    au += 0.11 * trem * _sine(A2, t)
    au += 0.05 * trem * _sine(E3, t)

    # ── Blips dispersos (uno cada ~1.75 s) en pentatónica ────────────────
    nbl  = 8
    step = duration / nbl
    seq  = [penta[(i * 2) % len(penta)] for i in range(nbl)]
    if rng:
        rng.shuffle(seq)
    for i, freq in enumerate(seq):
        t0 = i * step
        m  = (t >= t0) & (t < t0 + step * 1.2)
        if not m.any():
            continue
        tl  = t[m] - t0
        env = np.exp(-tl * 2.6) * np.clip(tl / 0.012, 0, 1)
        au[m] += 0.060 * env * _sine(freq, tl)
        au[m] += 0.014 * env * _sine(freq * 2, tl)

    # ── Pulso grave suave por cada blanca ────────────────────────────────
    for k in range(int(duration)):
        t0 = float(k)
        m  = (t >= t0) & (t < t0 + 0.5)
        if not m.any():
            continue
        tl  = t[m] - t0
        env = np.exp(-tl * 5.0) * np.clip(tl / 0.01, 0, 1)
        au[m] += 0.05 * env * _tri(A2, tl)

    for delay_ms, decay in [(220, 0.26), (440, 0.13)]:
        ds = int(_SR * delay_ms / 1000)
        if ds < n:
            au[ds:] += decay * au[:-ds]

    fade = int(_SR * 0.10)
    au[:fade]  *= np.linspace(0, 1, fade)
    au[-fade:] *= np.linspace(1, 0, fade)
    peak = np.max(np.abs(au))
    if peak > 0:
        au = au / peak * 0.58

    stereo = np.column_stack([au, au])
    return np.int16(stereo * 32767)


# ═══════════════════════════════════════════════════════════════════════════════
# Caché, pre-generación y gestor de reproducción
# ═══════════════════════════════════════════════════════════════════════════════
_GENERATORS = {
    "game":   generate_loop,
    "menu":   generate_menu_loop,
    "config": generate_config_loop,
}

_arr_cache: dict = {}              # name → np.ndarray (caro de generar)
_snd_cache: dict = {}             # name → pygame.mixer.Sound
_seeds: dict     = {}             # name → semilla de la sesión


def set_session_seed(seed: int | None = None) -> None:
    """Fija una semilla por sesión para que las pistas varíen entre arranques.

    None elige una semilla aleatoria; un entero la hace reproducible.
    """
    base = random.randrange(1 << 30) if seed is None else seed
    for off, name in enumerate(_GENERATORS):
        _seeds[name] = base + off * 101


def _gen_array(name: str) -> np.ndarray:
    arr = _arr_cache.get(name)
    if arr is None:
        arr = _GENERATORS[name](seed=_seeds.get(name))
        _arr_cache[name] = arr
    return arr


def prepare_async(names=("menu", "game", "config")) -> threading.Thread:
    """Genera en segundo plano los arrays (numpy) de las pistas indicadas."""
    def _work():
        for nm in names:
            try:
                _gen_array(nm)
            except Exception:
                pass
    th = threading.Thread(target=_work, daemon=True)
    th.start()
    return th


def get_sound(name: str) -> "pygame.mixer.Sound":
    """Devuelve el Sound de la pista (lo construye desde el array cacheado)."""
    snd = _snd_cache.get(name)
    if snd is None:
        snd = pygame.sndarray.make_sound(_gen_array(name))
        _snd_cache[name] = snd
    return snd


# ── Accesores con nombre (compatibilidad) ────────────────────────────────────
def get_music_sound() -> "pygame.mixer.Sound":
    return get_sound("game")


def get_menu_music_sound() -> "pygame.mixer.Sound":
    return get_sound("menu")


def get_config_music_sound() -> "pygame.mixer.Sound":
    return get_sound("config")


def _reset_cache() -> None:
    _arr_cache.clear()
    _snd_cache.clear()


# ═══════════════════════════════════════════════════════════════════════════════
# MusicManager: reproduce una pista a la vez con crossfade y "ducking"
# ═══════════════════════════════════════════════════════════════════════════════
class MusicManager:
    """Gestiona las tres pistas en canales propios.

    - `play(name)` hace crossfade desde la pista actual a `name`.
    - `set_volume` / `get_volume` controlan el volumen de usuario (0..1).
    - `duck(factor)` atenúa temporalmente sin tocar el volumen de usuario
      (se usa en pausa: misma música del juego, más bajita).
    """

    def __init__(self, volume: float = 0.32):
        self.volume   = max(0.0, min(1.0, volume))
        self._duck    = 1.0
        self.current: str | None = None
        self._channels: dict[str, "pygame.mixer.Channel | None"] = {}

    # ── Volumen ──────────────────────────────────────────────────────────
    def _applied(self) -> float:
        return self.volume * self._duck

    def _apply_current(self) -> None:
        if self.current:
            try:
                get_sound(self.current).set_volume(self._applied())
            except Exception:
                pass

    def set_volume(self, v: float) -> None:
        self.volume = max(0.0, min(1.0, v))
        self._apply_current()

    def get_volume(self) -> float:
        return self.volume

    def duck(self, factor: float = 0.4) -> None:
        self._duck = max(0.0, min(1.0, factor))
        self._apply_current()

    def unduck(self) -> None:
        self.duck(1.0)

    # ── Reproducción ─────────────────────────────────────────────────────
    def play(self, name: str, fade_ms: int = 700) -> None:
        if name == self.current:
            ch = self._channels.get(name)
            if ch is not None and ch.get_busy():
                return
        # Funde las demás pistas que sigan sonando
        for nm, ch in list(self._channels.items()):
            if nm != name and ch is not None and ch.get_busy():
                try:
                    ch.fadeout(fade_ms)
                except Exception:
                    pass
        try:
            snd = get_sound(name)
            snd.set_volume(self._applied())
            self._channels[name] = snd.play(loops=-1, fade_ms=fade_ms)
            self.current = name
        except Exception:
            self.current = name   # mixer ausente: estado lógico igualmente

    def stop(self, fade_ms: int = 400) -> None:
        for ch in self._channels.values():
            if ch is not None and ch.get_busy():
                try:
                    ch.fadeout(fade_ms)
                except Exception:
                    pass
        self.current = None
