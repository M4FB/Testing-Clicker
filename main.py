#!/usr/bin/env python3
"""
Clicker Game — versión principal (v1.0).

Uso (desde la raíz del repo):
    .venv/bin/python main.py                  # modo demo (×100)
    GAME_MODE=full .venv/bin/python main.py   # modo full

F11 alterna pantalla completa (la ventana usa SCALED, así que el lienzo
de 1024×680 se escala solo).
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
    from src.save import load_game, save_info

    flags = pygame.SCALED
    info  = save_info()
    if info and info.get("fullscreen"):
        flags |= pygame.FULLSCREEN
    screen = pygame.display.set_mode((W, H), flags)
    pygame.display.set_caption("Clicker Game")

    # ── Música de fondo procedural ────────────────────────────────────────────
    music = None
    try:
        from src.music import get_music_sound
        music = get_music_sound()
        music.set_volume(0.32)
        music.play(loops=-1)
    except Exception as exc:
        print(f"[música] No se pudo iniciar: {exc}", file=sys.stderr)

    # ── Bucle menú → juego → menú ─────────────────────────────────────────────
    from src.menu import MainMenu
    from src.ui import GameUI
    from src import sfx

    while True:
        action = MainMenu(screen).run()
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

        result = GameUI(screen=screen, music=music,
                        state=state, elapsed=meta.get("elapsed", 0.0)).run()
        if result == "quit":
            break
        # result == "menu" → volver al while

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
