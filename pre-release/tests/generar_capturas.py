"""Genera las capturas del informe pre-release en la carpeta ss/.

  1. Ejecuta las tres suites (TDD / BDD / ATDD) y renderiza su salida como
     imágenes de terminal (mismo estilo que informe/generar_screenshots.py).
  2. Renderiza capturas de cada apartado del juego con el driver dummy de SDL
     (no necesita ventana).

Uso:
    cd pre-release
    ../.venv/bin/python generar_capturas.py
"""
import os
import random
import subprocess
import sys
import time

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from PIL import Image, ImageDraw, ImageFont

BASE   = os.path.dirname(os.path.abspath(__file__))
SS_DIR = os.path.join(BASE, "ss")

FONT_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
]

BG    = (13,  17,  23)
TXT   = (201, 209, 217)
GREEN = (63,  185,  80)
RED   = (248,  81,  73)
GOLD  = (210, 153,  34)
BLUE  = (88,  166, 255)
MUTED = (110, 118, 129)
ORNG  = (255, 166,  87)


# ═══════════════════════════════════════════════════════════════════════════════
# Render de terminal (salida de pytest → PNG)
# ═══════════════════════════════════════════════════════════════════════════════

def load_font(size=13):
    for path in FONT_PATHS:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def line_color(line: str) -> tuple:
    l = line.strip()
    if "PASSED" in line:                          return GREEN
    if "FAILED" in line or "ERROR" in line:       return RED
    if line.startswith("====="):                  return BLUE
    if "passed" in line and "failed" not in line: return GREEN
    if "failed" in line:                          return RED
    if l.startswith("tests/") and "::" in l:      return TXT
    if "warnings" in line or "warn" in line.lower(): return ORNG
    if l.startswith(("platform", "rootdir", "plugins", "collecting", "collected")):
        return MUTED
    return TXT


def render_terminal(lines: list[str], out_path: str, title: str,
                    width: int = 980, font_size: int = 13,
                    max_lines: int = 200):
    font  = load_font(font_size)
    lines = lines[:max_lines]

    lh, PAD, TBH = font_size + 5, 18, 32
    height = TBH + len(lines) * lh + PAD * 2

    img  = Image.new("RGB", (width, height), BG)
    draw = ImageDraw.Draw(img)

    draw.rectangle([(0, 0), (width, TBH)], fill=(30, 35, 45))
    draw.rectangle([(0, TBH), (width, TBH + 1)], fill=(48, 54, 61))
    draw.text((PAD, TBH // 2), title, font=font, fill=GOLD, anchor="lm")
    for i, c in enumerate([RED, ORNG, GREEN]):
        cx = width - 20 - i * 18
        draw.ellipse([(cx - 5, TBH // 2 - 5), (cx + 5, TBH // 2 + 5)], fill=c)

    for i, line in enumerate(lines):
        draw.text((PAD, TBH + PAD + i * lh), line[:130],
                  font=font, fill=line_color(line))

    img.save(out_path)
    print(f"  → {os.path.relpath(out_path, BASE)}")


def run_suite(target: str, out_png: str, title: str):
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", target, "-v", "--no-header"],
        capture_output=True, text=True, cwd=BASE,
    )
    lines = proc.stdout.splitlines()
    render_terminal(lines, out_png, title)
    if proc.returncode != 0:
        print(f"  ⚠ {target} terminó con fallos (código {proc.returncode})")


# ═══════════════════════════════════════════════════════════════════════════════
# Capturas del juego
# ═══════════════════════════════════════════════════════════════════════════════

def game_screenshots():
    random.seed(7)
    import pygame
    pygame.init()
    try:
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
    except pygame.error:
        pass
    screen = pygame.display.set_mode((1024, 680))

    from src.menu import MainMenu
    from src.pygame_ui import GameUI, _QTE, W, H
    from src.minigames import TargetRush, GoldRain, SimonPlus, PulseBar
    from src.fx import FX
    import src.pygame_ui as pui
    pui.save_game = lambda *a, **k: None       # las capturas no tocan el save real

    def save(surface, name):
        pygame.image.save(surface, os.path.join(SS_DIR, name))
        print(f"  → ss/{name}")

    # ── 01: menú principal ────────────────────────────────────────────────
    menu = MainMenu(screen)
    for _ in range(50):
        menu.stars.update(0.03)
        for n in menu.nebulas:
            n.update(0.03)
        from src.menu import _FloatText
        if random.random() < 0.4:
            menu.floats.append(_FloatText(1024, 680))
        for f in menu.floats:
            f.update(0.03)
    menu._draw(512, 430, time.time())
    save(screen, "01_menu_principal.png")

    # ── 02: partida temprana ──────────────────────────────────────────────
    ui = GameUI(screen=screen)
    ui.game.points = 850
    ui.game.total_points = 2_300
    ui.game.buy_generator_n("worker", 2)
    for _ in range(30):
        ui._update()
    ui._do_click(190, 320)
    ui._update(); ui._draw()
    save(ui.canvas, "02_juego_inicio.png")

    # ── 03: partida media con compra múltiple MAX ─────────────────────────
    ui = GameUI(screen=screen)
    ui.game.points = 95_000
    ui.game.total_points = 160_000
    ui.game.buy_generator_n("worker", 8)
    ui.game.buy_generator_n("workshop", 3)
    ui.game.buy_gen_upgrade("gu_w1")
    ui.buy_qty = "max"
    ui.combo = 14
    ui.last_click = time.time()
    for _ in range(30):
        ui._update()
    ui._update(); ui._draw()
    save(ui.canvas, "03_compra_multiple_max.png")

    # ── 04-07: minijuegos ─────────────────────────────────────────────────
    minis = [
        ("04_minijuego_fiebre_dorada.png", TargetRush, 1.9),
        ("05_minijuego_lluvia_dorada.png", GoldRain,  2.2),
        ("06_minijuego_simon_dice.png",    SimonPlus, 1.5),
        ("07_minijuego_pulso_perfecto.png", PulseBar, 1.1),
    ]
    base_ui = GameUI(screen=screen)
    base_ui.game.points = 12_000
    base_ui.game.total_points = 30_000
    base_ui.game.buy_generator_n("worker", 5)
    for _ in range(20):
        base_ui._update()
    for name, cls, espera in minis:
        fx = FX()
        mw, mh = cls.MODAL
        rect = pygame.Rect((W - mw) // 2, (H - mh) // 2, mw, mh)
        mg = cls(rect, fx)
        t_end = time.time() + espera
        while time.time() < t_end:
            mg.update(time.time(), 0.016)
            time.sleep(0.016)
        base_ui._update(); base_ui._draw()
        ov = pygame.Surface((W, H), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 165))
        base_ui.canvas.blit(ov, (0, 0))
        mg.draw(base_ui.canvas, base_ui.F, rect.centerx, rect.centery + 60)
        save(base_ui.canvas, name)

    # ── 08: QTE en curso ──────────────────────────────────────────────────
    ui = GameUI(screen=screen)
    ui.game.points = 5_000
    ui.game.total_points = 9_000
    ui.game.buy_generator_n("worker", 3)
    ui._qte = _QTE(sequence=list("ASDFGHJK"))
    ui._qte.current = 3
    for _ in range(20):
        ui._update()
    ui._update(); ui._draw()
    save(ui.canvas, "08_evento_qte.png")

    # ── 09: boosts activos (minijuego + QTE) ──────────────────────────────
    ui = GameUI(screen=screen)
    ui.game.points = 22_000
    ui.game.total_points = 60_000
    ui.game.buy_generator_n("worker", 6)
    ui.game.activate_minigame(2.5, 45.0)
    ui._boost_total = 45.0
    ui.game.activate_qte_bonus(3.0, 60.0)
    ui._qte_total = 60.0
    for _ in range(20):
        ui._update()
    ui._update(); ui._draw()
    save(ui.canvas, "09_boosts_activos.png")

    # ── 10: pausa con volúmenes ───────────────────────────────────────────
    ui.paused = True
    ui._draw()
    save(ui.canvas, "10_pausa_volumenes.png")

    # ── 11: victoria ──────────────────────────────────────────────────────
    ui = GameUI(screen=screen)
    ui.game.prestige_count = 2
    ui.game.prestige_multiplier = 3.0
    ui.game.total_points = 600_000_000
    ui.game.high_score = 600_000_000
    ui.game.won = True
    ui.game.infinite_mode = True
    ui.fx.confetti_burst(W, 120)
    for _ in range(25):
        ui._update()
    ui._draw()
    save(ui.canvas, "11_victoria.png")

    pygame.quit()


# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    os.makedirs(SS_DIR, exist_ok=True)

    print("Suites de pruebas:")
    run_suite("tests/test_core.py", os.path.join(SS_DIR, "tests_tdd.png"),
              "TDD — Pruebas Unitarias  (pre-release/tests/test_core.py)")
    run_suite("tests/test_bdd.py", os.path.join(SS_DIR, "tests_bdd.png"),
              "BDD — Escenarios Gherkin  (pre-release/tests/test_bdd.py)")
    run_suite("tests/test_acceptance.py", os.path.join(SS_DIR, "tests_atdd.png"),
              "ATDD — Pruebas de Aceptación  (pre-release/tests/test_acceptance.py)")

    print("Capturas del juego:")
    game_screenshots()

    print("Listo.")
