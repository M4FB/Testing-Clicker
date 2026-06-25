#!/usr/bin/env python3
"""
Clicker Game — versión principal (v1.0).

Uso (desde la raíz del repo):
    .venv/bin/python main.py                       # modo demo (×100)
    GAME_MODE=full .venv/bin/python main.py        # modo full
    CHEAT_TABLE=on .venv/bin/python main.py        # con mesa de trucos (F1)

F11 alterna pantalla completa (la ventana usa SCALED, así que el lienzo
de 1024×680 se escala solo). Con CHEAT_TABLE=on, F1 abre dentro del juego una
"Cheat Table" para forzar minijuegos, stats, mejoras, prestigio y endgame.
"""
import sys

import pygame


def main() -> None:
    pygame.init()
    # Mixer en stereo 16-bit para la música generada con numpy
    try:
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=4096)
    except pygame.error:
        pass

    from src.ui import W, H
    from src.save import load_game, load_prefs

    # ── Preferencias (volúmenes / pantalla), independientes de la partida ─────
    prefs = load_prefs()
    from src.fx import set_theme
    set_theme(prefs.get("theme", "azul"))
    flags = pygame.SCALED
    if prefs.get("fullscreen"):
        flags |= pygame.FULLSCREEN
    screen = pygame.display.set_mode((W, H), flags)
    pygame.display.set_caption("Clicker Game")

    from src import sfx
    sfx.set_volume(prefs.get("sfx_vol", 0.5))

    # ── Música de fondo procedural ────────────────────────────────────────────
    # Tres pistas distintas (menú / juego / ajustes) gestionadas por un único
    # MusicManager que hace crossfade entre ellas. Se pre-generan en segundo
    # plano con una semilla por sesión (variación procedural entre arranques).
    music = None
    try:
        from src import music as music_mod
        music_mod.set_session_seed()              # variación por arranque
        music_mod.prepare_async()                 # genera en un hilo
        music = music_mod.MusicManager(volume=prefs.get("music_vol", 0.32))
    except Exception as exc:
        print(f"[música] No se pudo iniciar: {exc}", file=sys.stderr)

    # ── Bucle menú → juego → menú ─────────────────────────────────────────────
    from src.menu import MainMenu
    from src.ui import GameUI

    while True:
        if music:
            music.play("menu")

        action = MainMenu(screen, music=music).run()
        if action == "quit":
            break

        state, meta = (None, {})
        if action == "cont":
            state, meta = load_game()
        if meta:
            if music and "music_vol" in meta:
                music.set_volume(meta["music_vol"])
            if "sfx_vol" in meta:
                sfx.set_volume(meta["sfx_vol"])

        if music:
            music.play("game")
        result = GameUI(screen=screen, music=music,
                        state=state, elapsed=meta.get("elapsed", 0.0)).run()
        if result == "quit":
            break
        # result == "menu" → volver al while

    if music:
        music.stop()
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
