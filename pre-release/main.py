#!/usr/bin/env python3
"""
Clicker Game — PRE-RELEASE (visuales mejorados + minijuegos nuevos).

Uso (desde esta carpeta):
    cd pre-release
    ../.venv/bin/python main.py                  # modo demo (×100)
    GAME_MODE=full ../.venv/bin/python main.py   # modo full
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

    from src.pygame_ui import W, H
    screen = pygame.display.set_mode((W, H))
    pygame.display.set_caption("Clicker Game — PRE-RELEASE")

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
    from src.pygame_ui import GameUI

    while True:
        action = MainMenu(screen).run()
        if action == "quit":
            break

        result = GameUI(screen=screen, music=music).run()
        if result == "quit":
            break
        # result == "menu" → volver al while

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
