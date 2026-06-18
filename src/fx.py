"""Efectos visuales reutilizables.

Contiene: paleta, easing, fondo (gradiente, nebulosas, starfield parallax,
estrellas fugaces), sistema de partículas (chispas, textos flotantes,
confeti, anillos de choque, brasas), estelas, screen-shake, toasts,
números rodantes y helpers de dibujo
(botones brillantes, barras rayadas, moneda girando).
"""
import math
import random
import time

import pygame

# ═══════════════════════════════════════════════════════════════════════════════
# Paleta global
# ═══════════════════════════════════════════════════════════════════════════════
BG      = ( 10,  13,  24)
BG2     = ( 22,  15,  38)
PANEL   = ( 21,  26,  38)
PANEL2  = ( 30,  36,  52)
BORDER  = ( 52,  60,  78)
TXT     = (212, 220, 232)
MUTED   = (122, 132, 150)
ACCENT  = ( 88, 166, 255)
GOLD    = (255, 200,  60)
GOLD_D  = (166, 116,  20)
GREEN   = ( 63, 185,  80)
GREEN_D = ( 22,  80,  35)
RED     = (248,  81,  73)
RED_D   = ( 80,  25,  22)
ORANGE  = (255, 166,  87)
PURPLE  = (188, 140, 255)


# ═══════════════════════════════════════════════════════════════════════════════
# Utilidades
# ═══════════════════════════════════════════════════════════════════════════════
def clamp(v, a, b):
    return a if v < a else (b if v > b else v)


def lerp(a, b, t):
    return a + (b - a) * t


def lerp_color(c1, c2, t):
    t = clamp(t, 0.0, 1.0)
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def scale_color(c, f):
    return tuple(int(clamp(ch * f, 0, 255)) for ch in c)


def ease_out(t, p=3.0):
    return 1.0 - (1.0 - clamp(t, 0.0, 1.0)) ** p


def draw_text(surf, text, font, color, x, y, anchor="topleft", alpha=255):
    s = font.render(text, True, color)
    if alpha < 255:
        s.set_alpha(alpha)
    r = s.get_rect(**{anchor: (x, y)})
    surf.blit(s, r)
    return r


def vgradient(w, h, top, bottom):
    col = pygame.Surface((1, h))
    for y in range(h):
        col.set_at((0, y), lerp_color(top, bottom, y / max(1, h - 1)))
    return pygame.transform.scale(col, (w, h))


# ═══════════════════════════════════════════════════════════════════════════════
# Fondo: nebulosas
# ═══════════════════════════════════════════════════════════════════════════════
class Nebula:
    COLORS = [(36, 52, 110), (70, 38, 108), (20, 76, 92), (90, 50, 44)]

    def __init__(self, w, h):
        self.r = random.randint(130, 230)
        color  = random.choice(self.COLORS)
        d      = self.r * 2
        self.surf = pygame.Surface((d, d), pygame.SRCALPHA)
        steps = 22
        for i in range(steps):
            t   = i / (steps - 1)
            rad = max(2, int(self.r * (1.0 - t * 0.92)))
            pygame.draw.circle(self.surf, (*color, int(2 + 18 * t ** 2)),
                               (self.r, self.r), rad)
        self.cx  = random.uniform(0, w)
        self.cy  = random.uniform(0, h)
        self.ph  = random.uniform(0, math.tau)
        self.sp  = random.uniform(0.05, 0.16)
        self.amp = random.uniform(18, 46)

    def update(self, dt):
        self.ph += self.sp * dt

    def draw(self, surf):
        x = self.cx + math.cos(self.ph) * self.amp - self.r
        y = self.cy + math.sin(self.ph * 0.7) * self.amp - self.r
        surf.blit(self.surf, (x, y))


# ═══════════════════════════════════════════════════════════════════════════════
# Fondo: estrellas con parallax + fugaces
# ═══════════════════════════════════════════════════════════════════════════════
class _Star:
    def __init__(self, w, h, y=None):
        self._w, self._h = w, h
        self.depth = random.choice([0.35, 0.6, 1.0])
        self._spawn(y)

    def _spawn(self, y=None):
        self.x     = random.randint(0, self._w)
        self.y     = float(y if y is not None else self._h + 2)
        self.speed = random.uniform(4, 14) * self.depth
        self.base  = int(random.randint(30, 120) * (0.4 + 0.6 * self.depth))
        self.size  = 2 if (self.depth == 1.0 and random.random() < 0.3) else 1
        self.phase = random.uniform(0, math.tau)
        self.freq  = random.uniform(0.5, 2.2)

    def update(self, dt):
        self.y     -= self.speed * dt
        self.phase += self.freq * dt
        if self.y < -2:
            self._spawn()

    def draw(self, surf):
        b   = int(self.base * (0.6 + 0.4 * math.sin(self.phase)))
        col = (b, b, min(255, b + 22))
        ix, iy = int(self.x), int(self.y)
        if 0 <= ix < self._w and 0 <= iy < self._h:
            if self.size == 1:
                surf.set_at((ix, iy), col)
            else:
                pygame.draw.circle(surf, col, (ix, iy), self.size)


class _ShootingStar:
    def __init__(self, w, h):
        self.x  = random.uniform(w * 0.1, w * 0.9)
        self.y  = random.uniform(20, h * 0.4)
        ang     = random.uniform(math.radians(18), math.radians(38))
        sp      = random.uniform(480, 700)
        sgn     = random.choice([1, -1])
        self.vx = math.cos(ang) * sp * sgn
        self.vy = math.sin(ang) * sp
        self.born = time.time()
        self.life = random.uniform(0.5, 0.8)

    @property
    def alive(self):
        return (time.time() - self.born) < self.life

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt

    def draw(self, surf):
        rem = 1.0 - (time.time() - self.born) / self.life
        for k, f in ((0.05, 1.0), (0.09, 0.5), (0.13, 0.25)):
            c = scale_color((200, 220, 255), rem * f)
            pygame.draw.line(surf, c,
                             (self.x, self.y),
                             (self.x - self.vx * k, self.y - self.vy * k), 1)


class StarField:
    def __init__(self, w, h, n=120):
        self.w, self.h = w, h
        self.stars    = [_Star(w, h, random.randint(0, h)) for _ in range(n)]
        self.shooting: list[_ShootingStar] = []
        self._next_shoot = time.time() + random.uniform(3, 8)

    def update(self, dt):
        for s in self.stars:
            s.update(dt)
        now = time.time()
        if now >= self._next_shoot:
            self.shooting.append(_ShootingStar(self.w, self.h))
            self._next_shoot = now + random.uniform(5, 13)
        for s in self.shooting:
            s.update(dt)
        self.shooting = [s for s in self.shooting if s.alive]

    def draw(self, surf):
        for s in self.stars:
            s.draw(surf)
        for s in self.shooting:
            s.draw(surf)


# ═══════════════════════════════════════════════════════════════════════════════
# Sistema de partículas + screen shake
# ═══════════════════════════════════════════════════════════════════════════════
class FX:
    CONFETTI_COLORS = [GOLD, GREEN, ACCENT, PURPLE, ORANGE, RED, (240, 240, 255)]

    def __init__(self):
        self.sparks:   list[dict] = []
        self.texts:    list[dict] = []
        self.confetti: list[dict] = []
        self.rings:    list[dict] = []
        self.embers:   list[dict] = []
        self.trauma = 0.0

    # ── shake ──────────────────────────────────────────────────────────────
    def add_shake(self, amount):
        self.trauma = min(1.0, self.trauma + amount)

    def offset(self):
        if self.trauma <= 0.01:
            return (0, 0)
        m = (self.trauma ** 2) * 13
        return (random.uniform(-m, m), random.uniform(-m, m))

    # ── emisores ───────────────────────────────────────────────────────────
    def sparks_burst(self, x, y, color, n=14, speed=230):
        now = time.time()
        for _ in range(n):
            a  = random.uniform(0, math.tau)
            sp = random.uniform(speed * 0.3, speed)
            self.sparks.append({
                "x": x, "y": y,
                "vx": math.cos(a) * sp, "vy": math.sin(a) * sp - 60,
                "r": random.uniform(1.6, 3.6), "c": color,
                "born": now, "life": random.uniform(0.35, 0.85),
            })

    def float_text(self, x, y, text, color, big=False):
        self.texts.append({
            "x": x + random.uniform(-6, 6), "y": y, "t": text, "c": color,
            "big": big, "vx": random.uniform(-12, 12),
            "born": time.time(), "life": 1.5 if big else 1.0,
        })

    def ring(self, x, y, color, max_r=90, width=3, life=0.45):
        """Onda de choque expansiva (clic crítico, eventos)."""
        self.rings.append({"x": x, "y": y, "c": color, "max_r": max_r,
                           "w": width, "born": time.time(), "life": life})

    def ember_burst(self, x, y, color, n=8, spread=26):
        """Brasas que flotan hacia arriba (combos altos, fiebre dorada)."""
        now = time.time()
        for _ in range(n):
            self.embers.append({
                "x": x + random.uniform(-spread, spread),
                "y": y + random.uniform(-6, 6),
                "vy": -random.uniform(28, 75),
                "vx": random.uniform(-14, 14),
                "r": random.uniform(1.5, 3.2), "c": color,
                "born": now, "life": random.uniform(0.6, 1.3),
                "ph": random.uniform(0, math.tau),
            })

    def confetti_burst(self, w, n=90):
        now = time.time()
        for _ in range(n):
            self.confetti.append({
                "x": random.uniform(0, w), "y": random.uniform(-60, -8),
                "vx": random.uniform(-35, 35), "vy": random.uniform(110, 260),
                "rot": random.uniform(0, math.tau), "vrot": random.uniform(-7, 7),
                "w": random.randint(5, 9), "h": random.randint(3, 6),
                "c": random.choice(self.CONFETTI_COLORS),
                "born": now, "life": random.uniform(2.2, 4.0),
            })

    # ── ciclo ──────────────────────────────────────────────────────────────
    def update(self, dt):
        self.trauma = max(0.0, self.trauma - dt * 1.7)
        now = time.time()

        for p in self.sparks:
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            p["vy"] += 480 * dt
        self.sparks = [p for p in self.sparks if now - p["born"] < p["life"]]

        for p in self.texts:
            t = (now - p["born"]) / p["life"]
            p["x"] += p["vx"] * dt
            p["y"] -= (90 if p["big"] else 70) * dt * (1.0 - ease_out(t) * 0.7)
        self.texts = [p for p in self.texts if now - p["born"] < p["life"]]

        for p in self.confetti:
            p["x"]  += (p["vx"] + math.sin(p["rot"] * 2) * 26) * dt
            p["y"]  += p["vy"] * dt
            p["rot"] += p["vrot"] * dt
        self.confetti = [p for p in self.confetti if now - p["born"] < p["life"]]

        for p in self.embers:
            p["ph"] += dt * 5
            p["x"]  += (p["vx"] + math.sin(p["ph"]) * 16) * dt
            p["y"]  += p["vy"] * dt
        self.embers = [p for p in self.embers if now - p["born"] < p["life"]]
        self.rings  = [r for r in self.rings if now - r["born"] < r["life"]]

    def draw(self, surf, f_sm, f_lg):
        now = time.time()
        for r in self.rings:
            t = (now - r["born"]) / r["life"]
            rad = max(2, int(ease_out(t) * r["max_r"]))
            col = scale_color(r["c"], 1.0 - t * 0.8)
            pygame.draw.circle(surf, col, (int(r["x"]), int(r["y"])), rad,
                               max(1, int(r["w"] * (1.0 - t * 0.6))))

        for p in self.embers:
            t = (now - p["born"]) / p["life"]
            col = scale_color(p["c"], 1.0 - t * 0.85)
            pygame.draw.circle(surf, col, (int(p["x"]), int(p["y"])),
                               max(1, int(p["r"] * (1.0 - t * 0.5))))

        for p in self.sparks:
            t = (now - p["born"]) / p["life"]
            r = max(1, int(p["r"] * (1.0 - t)))
            pygame.draw.circle(surf, p["c"], (int(p["x"]), int(p["y"])), r)

        for p in self.texts:
            t = (now - p["born"]) / p["life"]
            a = int(255 * (1.0 - t ** 1.6))
            f = f_lg if p["big"] else f_sm
            s = f.render(p["t"], True, p["c"])
            s.set_alpha(max(0, a))
            surf.blit(s, (int(p["x"] - s.get_width() // 2), int(p["y"])))

        for p in self.confetti:
            t  = (now - p["born"]) / p["life"]
            if t > 0.999:
                continue
            hw, hh = p["w"] / 2, p["h"] / 2
            cs, sn = math.cos(p["rot"]), math.sin(p["rot"])
            pts = [(p["x"] + cs * dx - sn * dy, p["y"] + sn * dx + cs * dy)
                   for dx, dy in ((-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh))]
            col = scale_color(p["c"], 1.0 - 0.5 * t)
            pygame.draw.polygon(surf, col, pts)


# ═══════════════════════════════════════════════════════════════════════════════
# Estela (puntos que se desvanecen siguiendo un objeto en movimiento)
# ═══════════════════════════════════════════════════════════════════════════════
class Trail:
    def __init__(self, color=GOLD, life=0.45, max_r=4.0, min_dist=6.0):
        self.color    = color
        self.life     = life
        self.max_r    = max_r
        self.min_dist = min_dist
        self.points: list[dict] = []
        self._last = None

    def add(self, x, y):
        if self._last is not None:
            lx, ly = self._last
            if (x - lx) ** 2 + (y - ly) ** 2 < self.min_dist ** 2:
                return
        self._last = (x, y)
        self.points.append({"x": x, "y": y, "born": time.time()})

    def update(self, dt):
        now = time.time()
        self.points = [p for p in self.points if now - p["born"] < self.life]
        if not self.points:
            self._last = None

    def draw(self, surf):
        now = time.time()
        for p in self.points:
            t = (now - p["born"]) / self.life
            r = max(1, int(self.max_r * (1.0 - t)))
            pygame.draw.circle(surf, scale_color(self.color, 1.0 - t * 0.8),
                               (int(p["x"]), int(p["y"])), r)


# ═══════════════════════════════════════════════════════════════════════════════
# Toasts (mensajes deslizantes)
# ═══════════════════════════════════════════════════════════════════════════════
class Toasts:
    MAX = 4

    def __init__(self):
        self.items: list[dict] = []

    def add(self, msg, color=TXT, dur=3.0):
        self.items.append({"msg": msg, "c": color, "born": time.time(), "dur": dur})
        if len(self.items) > self.MAX:
            self.items = self.items[-self.MAX:]

    def draw(self, surf, font, x, bottom_y):
        now = time.time()
        self.items = [i for i in self.items if now - i["born"] < i["dur"]]
        y = bottom_y
        for it in reversed(self.items):
            t     = now - it["born"]
            slide = ease_out(min(1.0, t / 0.25))
            fade  = 1.0 if t < it["dur"] - 0.45 else max(0.0, (it["dur"] - t) / 0.45)
            ts    = font.render(it["msg"], True, it["c"])
            w, h  = ts.get_width() + 30, 28
            y    -= h + 6
            box = pygame.Surface((w, h), pygame.SRCALPHA)
            pygame.draw.rect(box, (14, 18, 30, int(225 * fade)),
                             box.get_rect(), border_radius=8)
            pygame.draw.rect(box, (*it["c"], int(200 * fade)),
                             box.get_rect(), 1, border_radius=8)
            ts.set_alpha(int(255 * fade))
            box.blit(ts, (15, (h - ts.get_height()) // 2))
            surf.blit(box, (int(x - 34 + 34 * slide), y))


# ═══════════════════════════════════════════════════════════════════════════════
# Números rodantes
# ═══════════════════════════════════════════════════════════════════════════════
class Roll:
    def __init__(self, v=0.0):
        self.v = float(v)

    def tick(self, target, dt):
        self.v += (target - self.v) * clamp(dt * 9.0, 0.0, 1.0)
        if abs(target - self.v) < max(0.05, abs(target) * 1e-4):
            self.v = target
        return self.v


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers de dibujo: botones, barras, moneda
# ═══════════════════════════════════════════════════════════════════════════════
_band_cache: dict = {}


def _shine_band(h):
    band = _band_cache.get(h)
    if band is None:
        bw = 34
        band = pygame.Surface((bw, h), pygame.SRCALPHA)
        for i in range(bw):
            a = int(46 * (1.0 - abs(i - bw / 2) / (bw / 2)))
            pygame.draw.line(band, (255, 255, 255, a), (i, 0), (i, h))
        _band_cache[h] = band
    return band


def shiny_button(surf, rect, base, border_c, *, hover=False, pressed=False,
                 glow=0.0, shine=False, now=0.0, radius=9):
    """Botón con relieve, brillo superior, glow opcional y destello animado."""
    r = rect.move(0, 1) if pressed else rect
    body = scale_color(base, 0.82) if pressed else \
           (scale_color(base, 1.28) if hover else base)

    if glow > 0.02:
        gs = pygame.Surface((r.width + 26, r.height + 26), pygame.SRCALPHA)
        for rad, a in ((9, 14), (6, 22), (3, 32)):
            pygame.draw.rect(gs, (*border_c, int(glow * a)),
                             pygame.Rect(13 - rad, 13 - rad,
                                         r.width + rad * 2, r.height + rad * 2),
                             3, border_radius=radius + rad)
        surf.blit(gs, (r.x - 13, r.y - 13))

    pygame.draw.rect(surf, body, r, border_radius=radius)

    sh_h = max(2, r.height // 2 - 3)
    sh = pygame.Surface((max(1, r.width - 6), sh_h), pygame.SRCALPHA)
    sh.fill((255, 255, 255, 38 if hover else 24))
    surf.blit(sh, (r.x + 3, r.y + 2))

    if shine:
        period = 2.4
        t      = (now % period) / period
        band   = _shine_band(r.height)
        bx     = r.x - band.get_width() + t * (r.width + band.get_width() * 2)
        clip   = surf.get_clip()
        surf.set_clip(r)
        surf.blit(band, (bx, r.y))
        surf.set_clip(clip)

    pygame.draw.rect(surf, border_c, r, 2 if hover else 1, border_radius=radius)
    return r


def striped_bar(surf, rect, frac, fg, bg=PANEL2, now=0.0, radius=5):
    """Barra de progreso con rayas diagonales animadas."""
    pygame.draw.rect(surf, bg, rect, border_radius=radius)
    frac = clamp(frac, 0.0, 1.0)
    if frac > 0:
        fill = rect.copy()
        fill.width = max(radius * 2, int(rect.width * frac))
        pygame.draw.rect(surf, fg, fill, border_radius=radius)
        clip = surf.get_clip()
        surf.set_clip(fill)
        off    = int(now * 30) % 16
        bright = scale_color(fg, 1.35)
        for sx in range(fill.x - fill.height - 16 + off, fill.right, 16):
            pygame.draw.line(surf, bright,
                             (sx, fill.bottom), (sx + fill.height, fill.top), 3)
        surf.set_clip(clip)
        sh = pygame.Surface((fill.width, max(2, fill.height // 3)), pygame.SRCALPHA)
        sh.fill((255, 255, 255, 34))
        surf.blit(sh, (fill.x, fill.y + 1))
    pygame.draw.rect(surf, BORDER, rect, 1, border_radius=radius)


def draw_sparkline(surf, rect, values, color=ACCENT, *, fill=True, now=0.0):
    """Mini-gráfico de líneas dentro de `rect` a partir de `values`.

    Escala automáticamente al mínimo/máximo. Con <2 puntos dibuja una guía
    plana. Un punto brillante marca el último valor (animación de pulso).
    """
    pygame.draw.rect(surf, (14, 18, 28), rect, border_radius=5)
    pygame.draw.rect(surf, BORDER, rect, 1, border_radius=5)
    vals = [float(v) for v in (values or [])]
    inx, iny = rect.x + 4, rect.y + 4
    inw, inh = rect.width - 8, rect.height - 8
    if len(vals) < 2:
        y = rect.centery
        pygame.draw.line(surf, scale_color(color, 0.5),
                         (inx, y), (inx + inw, y), 1)
        return
    lo, hi = min(vals), max(vals)
    span = hi - lo
    n = len(vals)
    pts = []
    for i, v in enumerate(vals):
        x = inx + inw * i / (n - 1)
        frac = 0.5 if span <= 0 else (v - lo) / span
        y = iny + inh * (1.0 - frac)
        pts.append((x, y))
    if fill:
        poly = pts + [(pts[-1][0], rect.bottom - 2), (pts[0][0], rect.bottom - 2)]
        shade = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.polygon(shade, (*color, 46),
                            [(px - rect.x, py - rect.y) for px, py in poly])
        surf.blit(shade, rect.topleft)
    pygame.draw.lines(surf, color, False, pts, 2)
    # punto final con pulso
    pr = 2 + int(1.5 * (0.5 + 0.5 * math.sin(now * 4.0)))
    pygame.draw.circle(surf, scale_color(color, 1.4),
                       (int(pts[-1][0]), int(pts[-1][1])), pr)


def draw_coin(surf, cx, cy, r, now, speed=1.6):
    """Moneda dorada girando (squash horizontal senoidal)."""
    squash = abs(math.sin(now * speed))
    w = max(4, int(r * 2 * (0.18 + 0.82 * squash)))
    rect = pygame.Rect(0, 0, w, r * 2)
    rect.center = (int(cx), int(cy))
    pygame.draw.ellipse(surf, GOLD_D, rect)
    inner = rect.inflate(-max(3, w // 5), -max(3, r // 3))
    if inner.width > 2 and inner.height > 2:
        pygame.draw.ellipse(surf, GOLD, inner)
        hi = inner.inflate(-inner.width // 3, -inner.height // 2)
        hi.move_ip(-inner.width // 8, -inner.height // 6)
        if hi.width > 2 and hi.height > 2:
            pygame.draw.ellipse(surf, (255, 235, 150), hi)
    pygame.draw.ellipse(surf, (120, 84, 12), rect, 2)
