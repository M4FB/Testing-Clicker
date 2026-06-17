import curses
import time
import random
from src.game import GameState
from src.config import GENERATORS, CLICK_UPGRADES, MODE, MINIGAME_COOLDOWN


# ── Formato numérico ─────────────────────────────────────────────────────────

def fmt(n: float) -> str:
    if n >= 1_000_000_000:
        return f"{n / 1_000_000_000:.2f}B"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.2f}M"
    if n >= 1_000:
        return f"{n / 1_000:.2f}K"
    return f"{n:.1f}"


def fmt_time(s: float) -> str:
    s = int(s)
    if s >= 3600:
        return f"{s//3600}h {(s%3600)//60}m"
    if s >= 60:
        return f"{s//60}m {s%60}s"
    return f"{s}s"


# ── Minijuego simple (adivina el número) ────────────────────────────────────

class Minigame:
    def __init__(self):
        self.active = False
        self.answer = 0
        self.input_buf = ""
        self.result_msg = ""
        self.result_timer = 0.0

    def start(self):
        self.active = True
        self.answer = random.randint(1, 9)
        self.input_buf = ""
        self.result_msg = ""

    def submit(self) -> bool:
        try:
            guess = int(self.input_buf)
        except ValueError:
            return False
        if guess == self.answer:
            self.result_msg = "¡CORRECTO! Multiplicador x2 activo 30s"
            self.active = False
            return True
        self.result_msg = f"Fallaste (era {self.answer}). Sin recompensa."
        self.active = False
        return False


# ── Bucle principal ──────────────────────────────────────────────────────────

def run_game(stdscr):
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.timeout(50)

    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_YELLOW,  -1)   # título / oro
    curses.init_pair(2, curses.COLOR_GREEN,   -1)   # asequible / ok
    curses.init_pair(3, curses.COLOR_RED,     -1)   # no asequible / error
    curses.init_pair(4, curses.COLOR_CYAN,    -1)   # estadísticas
    curses.init_pair(5, curses.COLOR_BLACK,   curses.COLOR_WHITE)  # botón clic
    curses.init_pair(6, curses.COLOR_BLACK,   curses.COLOR_YELLOW) # botón prestige
    curses.init_pair(7, curses.COLOR_MAGENTA, -1)   # minijuego
    curses.init_pair(8, curses.COLOR_WHITE,   -1)   # bloqueado

    game = GameState()
    mini = Minigame()

    status_msg = ""
    status_timer = 0.0
    start_time = time.time()
    next_minigame = time.time() + MINIGAME_COOLDOWN
    minigame_available = False

    def safe_addstr(y, x, text, attr=curses.A_NORMAL):
        h, w = stdscr.getmaxyx()
        if y < 0 or y >= h:
            return
        if x < 0 or x >= w:
            return
        max_len = w - x - 1
        if max_len <= 0:
            return
        try:
            stdscr.addstr(y, x, text[:max_len], attr)
        except curses.error:
            pass

    def hline(y, ch="─"):
        h, w = stdscr.getmaxyx()
        if 0 <= y < h:
            try:
                stdscr.addstr(y, 0, ch * (w - 1))
            except curses.error:
                pass

    while True:
        game.tick()
        victory_triggered = game.check_victory()
        now = time.time()

        if not minigame_available and now >= next_minigame:
            minigame_available = True

        h, w = stdscr.getmaxyx()
        stdscr.erase()

        # ── Encabezado ───────────────────────────────────────────────────────
        mode_tag = f"[{MODE.upper()}]"
        title = "CLICKER GAME"
        tag_line = f" {mode_tag} {title} "
        if game.infinite_mode:
            tag_line += "  *** MODO INFINITO ***"
        safe_addstr(0, (w - len(tag_line)) // 2, tag_line, curses.color_pair(1) | curses.A_BOLD)
        hline(1)

        # ── Stats ────────────────────────────────────────────────────────────
        elapsed = fmt_time(now - start_time)
        safe_addstr(2, 2,  f"Puntos:    {fmt(game.points):<14}", curses.color_pair(4))
        safe_addstr(2, 30, f"Por clic:  {fmt(game.click_value * game.prestige_multiplier * game.minigame_multiplier)}", curses.color_pair(4))
        safe_addstr(3, 2,  f"PPS:       {fmt(game.pps()):<14}", curses.color_pair(4))
        safe_addstr(3, 30, f"Total:     {fmt(game.total_points)}", curses.color_pair(4))
        safe_addstr(4, 2,  f"Reinicios: {game.prestige_count}/2", curses.color_pair(4))
        safe_addstr(4, 30, f"Tiempo:    {elapsed}", curses.color_pair(4))

        # Barra de progreso hacia prestige/victoria
        bar_w = min(50, w - 20)
        pct = game.prestige_progress_pct()
        filled = int(bar_w * pct / 100)
        bar = "█" * filled + "░" * (bar_w - filled)
        next_label = "VICTORIA" if game.prestige_count == 2 else f"PRESTIGE {game.prestige_count + 1}"
        safe_addstr(5, 2, f"→ {next_label}: [{bar}] {pct:.1f}%", curses.color_pair(1))
        hline(6)

        # ── Botón de clic ────────────────────────────────────────────────────
        btn_text = "  [ESPACIO]  ¡ C L I C !  "
        btn_attr = curses.color_pair(5) | curses.A_BOLD
        if game.minigame_active:
            safe_addstr(7, 2, f"★ BOOST x{game.minigame_multiplier:.0f} ACTIVO — {game.minigame_seconds_left():.0f}s restantes ★",
                        curses.color_pair(7) | curses.A_BOLD)
        safe_addstr(8, (w - len(btn_text)) // 2, btn_text, btn_attr)

        # Botón prestige
        if game.can_prestige():
            prestige_text = f"  [P]  PRESTIGE {game.prestige_count + 1}  (x{'1.5' if game.prestige_count==0 else '2.0'})  "
            safe_addstr(9, (w - len(prestige_text)) // 2, prestige_text, curses.color_pair(6) | curses.A_BOLD)
        elif game.prestige_count < 2:
            remaining = game.prestige_threshold() - game.total_points
            safe_addstr(9, 2, f"  Faltan {fmt(remaining)} pts para Prestige {game.prestige_count + 1}", curses.color_pair(8))

        hline(10)

        # ── Minijuego disponible ─────────────────────────────────────────────
        if mini.active:
            safe_addstr(11, 2, "MINIJUEGO — Adivina el número (1-9):", curses.color_pair(7) | curses.A_BOLD)
            safe_addstr(12, 2, f"Tu respuesta: {mini.input_buf}_  [ENTER confirmar]", curses.color_pair(7))
            hline(13)
            status_row = 14
        elif minigame_available and not mini.active:
            safe_addstr(11, 2, "¡MINIJUEGO DISPONIBLE!  [M] para jugar  (recompensa: x2 por 30s)",
                        curses.color_pair(7) | curses.A_BOLD)
            hline(12)
            status_row = 13
        elif mini.result_msg and now < status_timer:
            safe_addstr(11, 2, mini.result_msg, curses.color_pair(2))
            hline(12)
            status_row = 13
        else:
            cd_left = max(0.0, next_minigame - now)
            safe_addstr(11, 2, f"Siguiente minijuego en {fmt_time(cd_left)}", curses.color_pair(8))
            hline(12)
            status_row = 13

        # ── Mensaje de estado ────────────────────────────────────────────────
        if status_msg and now < status_timer:
            safe_addstr(status_row, 2, status_msg, curses.color_pair(2) | curses.A_BOLD)
            status_row += 1

        hline(status_row)
        col_r = w // 2

        # ── Generadores ──────────────────────────────────────────────────────
        safe_addstr(status_row + 1, 2, "GENERADORES", curses.A_BOLD | curses.A_UNDERLINE)
        safe_addstr(status_row + 1, col_r, "MEJORAS DE CLIC", curses.A_BOLD | curses.A_UNDERLINE)

        for i, gen in enumerate(GENERATORS):
            row = status_row + 2 + i
            if row >= h - 2:
                break
            if not game.generator_unlocked(gen["id"]):
                safe_addstr(row, 2, f"  {i+1}. ???  [bloqueado]", curses.color_pair(8))
                continue
            owned = game.generators[gen["id"]]
            cost = game.generator_cost(gen["id"])
            pps_contrib = gen["pps"] * owned * game.prestige_multiplier
            can = game.can_buy_generator(gen["id"])
            color = curses.color_pair(2) if can else curses.color_pair(3)
            line = f"  {i+1}. {gen['name']:<12} x{owned:<3}  [{fmt(cost)}]  +{fmt(pps_contrib)}/s"
            safe_addstr(row, 2, line, color)

        for i, upg in enumerate(CLICK_UPGRADES):
            row = status_row + 2 + i
            if row >= h - 2:
                break
            if not game.click_upgrade_unlocked(upg["id"]):
                safe_addstr(row, col_r, f"  {i+4}. ???  [bloqueado]", curses.color_pair(8))
                continue
            bought = game.click_upgrades[upg["id"]]
            if bought:
                safe_addstr(row, col_r, f"  {i+4}. {upg['name']:<12} ✓ COMPRADO", curses.color_pair(2))
            else:
                cost = game.click_upgrade_cost(upg["id"])
                can = game.points >= cost
                color = curses.color_pair(2) if can else curses.color_pair(3)
                safe_addstr(row, col_r, f"  {i+4}. {upg['name']:<12} [{fmt(cost)}]  +{upg['bonus']*100}/clic", color)

        # ── Pie ──────────────────────────────────────────────────────────────
        footer_row = h - 2
        hline(footer_row)
        safe_addstr(footer_row + 1, 2,
                    "1-4: comprar generador | 5-7: mejora clic | M: minijuego | P: prestige | Q: salir")

        # ── Pantalla victoria ────────────────────────────────────────────────
        if victory_triggered:
            stdscr.erase()
            lines = [
                "",
                "  ╔══════════════════════════════════╗",
                "  ║       ¡ V I C T O R I A !        ║",
                "  ╠══════════════════════════════════╣",
                f"  ║  Tiempo total: {fmt_time(now - start_time):<17} ║",
                f"  ║  Puntuación:   {fmt(game.high_score):<17} ║",
                f"  ║  Reinicios:    {game.prestige_count:<17} ║",
                "  ╠══════════════════════════════════╣",
                "  ║  MODO INFINITO desbloqueado.     ║",
                "  ║  Presiona cualquier tecla...     ║",
                "  ╚══════════════════════════════════╝",
            ]
            for idx, line in enumerate(lines):
                safe_addstr(h // 2 - 5 + idx, (w - 40) // 2, line, curses.color_pair(1) | curses.A_BOLD)
            stdscr.refresh()
            stdscr.nodelay(False)
            stdscr.getch()
            stdscr.nodelay(True)

        stdscr.refresh()

        # ── Input ────────────────────────────────────────────────────────────
        key = stdscr.getch()
        if key == curses.ERR:
            continue

        if mini.active:
            if key == ord('\n') or key == curses.KEY_ENTER:
                won_mini = mini.submit()
                status_timer = time.time() + 3.0
                if won_mini:
                    game.activate_minigame(multiplier=2.0, duration=30.0)
            elif key == curses.KEY_BACKSPACE or key == 127:
                mini.input_buf = mini.input_buf[:-1]
            elif ord('0') <= key <= ord('9') and len(mini.input_buf) < 1:
                mini.input_buf += chr(key)
            continue

        if key == ord('q') or key == ord('Q'):
            break
        elif key == ord(' '):
            game.click()
        elif ord('1') <= key <= ord('4'):
            idx = key - ord('1')
            if idx < len(GENERATORS):
                gen = GENERATORS[idx]
                if game.buy_generator(gen["id"]):
                    status_msg = f"¡{gen['name']} comprado! (x{game.generators[gen['id']]})"
                else:
                    status_msg = "Sin fondos o bloqueado."
                status_timer = time.time() + 1.5
        elif ord('5') <= key <= ord('7'):
            idx = key - ord('5')
            if idx < len(CLICK_UPGRADES):
                upg = CLICK_UPGRADES[idx]
                if game.buy_click_upgrade(upg["id"]):
                    status_msg = f"¡{upg['name']} desbloqueado!"
                else:
                    status_msg = "Sin fondos, bloqueado o ya comprado."
                status_timer = time.time() + 1.5
        elif key == ord('m') or key == ord('M'):
            if minigame_available and not mini.active:
                mini.start()
                minigame_available = False
                next_minigame = time.time() + MINIGAME_COOLDOWN
        elif key == ord('p') or key == ord('P'):
            if game.can_prestige():
                prestige_n = game.prestige_count + 1
                game.prestige()
                status_msg = f"¡Prestige {prestige_n} completado! Multiplicador: x{game.prestige_multiplier:.1f}"
                status_timer = time.time() + 3.0


def main():
    curses.wrapper(run_game)
