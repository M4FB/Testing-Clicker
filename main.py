#!/usr/bin/env python3
"""
Clicker Game — versión pygame.
Uso:
    .venv/bin/python main.py              # modo demo (×100, ~20 min)
    GAME_MODE=full .venv/bin/python main.py  # modo full (~10-12 h)

Versión TUI (prealpha):
    cd prealpha && ../.venv/bin/python main.py
"""
from src.pygame_ui import main

if __name__ == "__main__":
    main()
