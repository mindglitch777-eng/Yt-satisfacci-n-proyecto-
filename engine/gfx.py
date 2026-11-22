"""Render con skia sobre un buffer numpy (cero copias hacia ffmpeg)."""
import math
import numpy as np
import skia

W, H = 1080, 1920

_TF = {}


def typeface(bold=True):
    key = bold
    if key not in _TF:
        style = skia.FontStyle.Bold() if bold else skia.FontStyle.Normal()
        tf = None
        for fam in ("Anton", "Bebas Neue", "Montserrat", "DejaVu Sans", "Liberation Sans"):
            t = skia.Typeface(fam, style)
            if t and t.getFamilyName() == fam:
                tf = t
                break
        _TF[key] = tf or skia.Typeface.MakeDefault()
    return _TF[key]


def rgb(c, a=1.0):
    return skia.Color4f(c[0], c[1], c[2], a)


def hsv(h, s=0.85, v=1.0):
    i = int(h * 6) % 6
    f = h * 6 - int(h * 6)
    p, q, t = v * (1 - s), v * (1 - f * s), v * (1 - (1 - f) * s)
    return [(v, t, p), (q, v, p), (p, v, t), (p, q, v), (t, p, v), (v, p, q)][i]


class Frame:
    """Superficie 1080x1920 RGBA cuyo buffer se escribe directo al encoder."""

    def __init__(self):
        self.buf = np.zeros((H, W, 4), np.uint8)
        self.surface = skia.Surface(self.buf, colorType=skia.kRGBA_8888_ColorType)
        self.canvas = self.surface.getCanvas()


def text_width(s, size):
    return skia.Font(typeface(), size).measureText(s)


def fit_size(s, size, max_w):
    w = text_width(s, size)
    return size if w <= max_w else size * max_w / w


def draw_text(c, s, x, y, size, color=(1, 1, 1), align="center", stroke=0.0,
              stroke_color=(0, 0, 0), alpha=1.0, max_w=W - 90, glow=0.0):
    """Texto con contorno grueso (estilo Shorts). Nunca se sale del cuadro: se achica."""
    size = fit_size(s, size, max_w)
    font = skia.Font(typeface(), size)
    font.setEdging(skia.Font.Edging.kAntiAlias)
    w = font.measureText(s)
    tx = x - w / 2 if align == "center" else (x - w if align == "right" else x)
    blob = skia.TextBlob.MakeFromString(s, font)
    if glow:
        c.drawTextBlob(blob, tx, y, skia.Paint(Color4f=rgb(color, 0.55 * alpha), AntiAlias=True,
                       MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, glow)))
    if stroke:
        c.drawTextBlob(blob, tx, y, skia.Paint(Color4f=rgb(stroke_color, alpha), AntiAlias=True,
                       Style=skia.Paint.kStroke_Style, StrokeWidth=stroke,
                       StrokeJoin=skia.Paint.kRound_Join))
    c.drawTextBlob(blob, tx, y, skia.Paint(Color4f=rgb(color, alpha), AntiAlias=True))
    return size


def bake(w, h, fn):
    """Dibuja algo costoso una sola vez y lo devuelve como imagen."""
    s = skia.Surface(int(w), int(h))
    cv = s.getCanvas()
    cv.clear(skia.ColorTRANSPARENT)
    fn(cv)
    return s.makeImageSnapshot()


def background(pal):
    """Fondo con gradiente radial + viñeta + grano fino, horneado."""
    def fn(c):
        bg = pal["bg"]
        hi = [min(1, v * 2.6 + 0.05) for v in bg]
        sh = skia.GradientShader.MakeRadial((W / 2, H * 0.52), H * 0.75,
                                            [skia.Color4f(*hi, 1).toColor(), skia.Color4f(*bg, 1).toColor()])
        c.drawPaint(skia.Paint(Shader=sh))
        rng = np.random.default_rng(7)
        p = skia.Paint(AntiAlias=True)
        for _ in range(140):  # estrellitas / polvo
            x, y, r = rng.uniform(0, W), rng.uniform(0, H), rng.uniform(0.8, 2.4)
            p.setColor4f(skia.Color4f(1, 1, 1, float(rng.uniform(0.05, 0.22))))
            c.drawCircle(float(x), float(y), float(r), p)
    return bake(W, H, fn)


def neon_ring(r, width, hue0, sat=0.85):
    """Aro arcoíris con glow en capas, horneado (se rota al dibujar)."""
    size = int(2 * r + 160)
    cx = size / 2
    def fn(c):
        n = 180
        cols = [skia.Color4f(*hsv((hue0 + i / n) % 1, sat), 1).toColor() for i in range(n + 1)]
        sh = skia.GradientShader.MakeSweep(cx, cx, cols)
        for lw, blur, a in ((width * 5, 28, 0.35), (width * 2.2, 10, 0.7), (width, 0, 1.0), (width * 0.35, 0, 1.0)):
            p = skia.Paint(Shader=sh, AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=lw)
            p.setAlphaf(a)
            if blur:
                p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
            if lw == width * 0.35:
                p = skia.Paint(Color4f=skia.Color4f(1, 1, 1, 0.75), AntiAlias=True,
                               Style=skia.Paint.kStroke_Style, StrokeWidth=lw)
            c.drawCircle(cx, cx, r, p)
    return bake(size, size, fn), cx


class Camera:
    """Shake + zoom al clímax. Se aplica como transform del canvas."""

    def __init__(self, rng):
        self.rng = rng
        self.trauma = 0.0
        self.zoom = 1.0
        self.zoom_target = 1.0
        self.focus = (W / 2, H / 2)

    def kick(self, amount):
        self.trauma = min(1.0, self.trauma + amount)

    def update(self, dt):
        self.trauma = max(0.0, self.trauma - dt * 1.6)
        self.zoom += (self.zoom_target - self.zoom) * min(1, dt * 4)

    def apply(self, c):
        s = self.trauma ** 2
        dx = (self.rng.random() * 2 - 1) * 26 * s
        dy = (self.rng.random() * 2 - 1) * 26 * s
        rot = (self.rng.random() * 2 - 1) * 1.2 * s
        fx, fy = self.focus
        c.translate(fx + dx, fy + dy)
        c.rotate(rot)
        c.scale(self.zoom, self.zoom)
        c.translate(-fx, -fy)


class Particles:
    def __init__(self, rng, cap=900):
        self.rng, self.cap = rng, cap
        self.p = []  # x, y, vx, vy, life, max_life, color, size

    def burst(self, x, y, color, n=8, speed=420, size=5, life=0.55):
        if len(self.p) > self.cap:
            n = 2
        for _ in range(n):
            a = self.rng.uniform(0, 2 * math.pi)
            v = self.rng.uniform(0.3, 1.0) * speed
            l = life * self.rng.uniform(0.6, 1.2)
            self.p.append([x, y, v * math.cos(a), v * math.sin(a), l, l, color, size * self.rng.uniform(0.6, 1.3)])

    def update(self, dt, g=600):
        for q in self.p:
            q[0] += q[2] * dt
            q[1] += q[3] * dt
            q[3] += g * dt
            q[2] *= 0.985
            q[4] -= dt
        self.p = [q for q in self.p if q[4] > 0]

    def draw(self, c):
        paint = skia.Paint(AntiAlias=True)
        for x, y, vx, vy, life, ml, col, sz in self.p:
            k = life / ml
            paint.setColor4f(rgb(col, min(1.0, k * 1.5)))
            c.drawCircle(x, y, sz * (0.4 + 0.6 * k), paint)


class Popups:
    """"+N" que sube y se desvanece."""

    def __init__(self):
        self.items = []

    def add(self, x, y, s, color, size=46):
        self.items.append([x, y, s, color, 0.8, size])

    def update(self, dt):
        for it in self.items:
            it[1] -= 110 * dt
            it[4] -= dt
        self.items = [it for it in self.items if it[4] > 0][-40:]

    def draw(self, c):
        for x, y, s, col, life, size in self.items:
            pop = 1 + 0.35 * max(0, life - 0.6) / 0.2
            draw_text(c, s, x, y, size * pop, col, stroke=8, alpha=min(1, life * 2.5), max_w=400)
