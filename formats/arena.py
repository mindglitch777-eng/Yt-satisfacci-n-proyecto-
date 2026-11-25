"""Base común de los formatos "máquina vs bolitas" (ver formats/punch.py, el primero aprobado).

Lo que comparten todos (y que el usuario ya validó en PUNCH):
- aro blanco, arco de progreso, contador "N BALLS"
- todas las bolas del MISMO tamaño; cuando hay más, se achican todas juntas
- colores de olas (cada multiplicación = color nuevo); la primera bola grande con cara de brainrot
- cuando no entra nada más: "FULL!" → grietas → el aro se ROMPE y se sueltan todas → fin
Cada formato implementa: setup_machine / machine_step / draw_machine / textos.
"""
import math
import numpy as np
import pymunk
import skia

from engine.sim import Sim
from engine.gfx import W, H, rgb, draw_text, text_width
from characters import get as get_char

BALL = 4
TAU = 2 * math.pi

# colores vivos de las olas (como las referencias): los 3 primeros son los de los brainrots
WAVE_COLORS = [None, None, None, (0.55, 0.95, 0.2), (0.62, 0.35, 1.0), (1.0, 0.85, 0.15), (0.2, 0.9, 0.85)]


class Arena(Sim):
    SUBSTEPS = 3
    TXT = {}

    # ---------- setup ----------
    def setup(self):
        g = self.g
        self.L = self.TXT[g.get("lang", "en")]
        self.cx, self.cy, self.R = W / 2, 905, 455
        self.space.gravity = (0, g.get("gravity", 0))
        self.space.damping = g.get("damping", 0.5)
        self.space.iterations = 8
        self.space.use_spatial_hash(14, 14000)
        self.ring_segs = []
        segs = 120
        for i in range(segs):
            a0, a1 = TAU * i / segs, TAU * (i + 1) / segs
            rr = self.R + 6
            s = pymunk.Segment(self.space.static_body, (self.cx + rr * math.cos(a0), self.cy + rr * math.sin(a0)),
                               (self.cx + rr * math.cos(a1), self.cy + rr * math.sin(a1)), 6)
            s.elasticity, s.friction = g.get("wall_bounce", 0.6), 0.3
            self.space.add(s)
            self.ring_segs.append(s)
        self.chars = [get_char(k) for k in g["chars"]]
        self.colors = [c.color for c in self.chars] + [c for c in WAVE_COLORS[3:]]
        self.cur = 0
        self.bodies, self.col, self.rad = [], [], []
        self.r_big = g.get("r_big", 0.08) * self.R      # grandes (con cara) mientras entren cómodas
        self.r0 = self.r_big
        self.r_exp = g.get("r_exp", 0.3)
        self.r_min = g.get("r_min", 4.6)
        self.capacity = int(g.get("packing", 0.78) * (self.R / self.r_min) ** 2)
        self.broken_at, self.frags = None, []
        self.ring_on = True                    # un formato puede sacar el aro (derrame) sin "romperlo"
        self.pops, self.flashes, self.dust = [], [], []
        self.round = g.get("round", 2)
        self.n_max = 0
        self.setup_machine()

    # ---------- bolas ----------
    def r_for(self, n):
        from formats.sizing import target_r
        return target_r(n, self.R, self.r_big, self.r_min, self.g.get("crowd", 0.40))

    def add_ball(self, x, y, vx, vy, col):
        r = self.rad[0] if self.rad else self.r_for(1)
        b = pymunk.Body(1, pymunk.moment_for_circle(1, 0, r))
        b.position, b.velocity = (x, y), (vx, vy)
        s = pymunk.Circle(b, r)
        s.elasticity, s.friction, s.collision_type = self.g.get("ball_bounce", 0.55), 0.3, BALL
        self.space.add(b, s)
        self.bodies.append(b)
        self.col.append(col)
        self.rad.append(r)

    def remove_balls(self, idx):
        idx = set(int(i) for i in idx)
        if not idx:
            return
        kb, kc, kr = [], [], []
        for i, (b, c, r) in enumerate(zip(self.bodies, self.col, self.rad)):
            if i in idx:
                self.space.remove(b, *b.shapes)
            else:
                kb.append(b); kc.append(c); kr.append(r)
        self.bodies, self.col, self.rad = kb, kc, kr

    def resize_all(self):
        """todas del mismo tamaño: cuando hay más, se achican todas juntas."""
        r = self.r_for(len(self.bodies))
        if self.rad and abs(self.rad[0] - r) < 0.05:
            return r
        for b in self.bodies:
            for sh in b.shapes:
                sh.unsafe_set_radius(r)
        self.rad = [r] * len(self.bodies)
        return r

    def positions(self):
        return np.array([b.position for b in self.bodies], np.float64).reshape(-1, 2)

    def tension(self):
        return min(1.0, len(self.bodies) / max(1, self.capacity)) ** 1.2

    def crush_fx(self, idx, P):
        """bolas aplastadas: polvo del color que tenían."""
        for i in list(idx)[:500]:
            if self.rng.random() < 0.6:
                x, y = P[i]
                self.dust.append([x, y, self.rng.uniform(-120, 120), self.rng.uniform(-120, 120), 0.0, self.col[i]])

    # ---------- loop ----------
    def step(self):
        if self.broken_at is None and self.done_at is None:
            self.machine_step()
        from formats.sizing import smooth_sizes
        smooth_sizes(self)
        super().step()
        self.contain()

    def update(self):
        dt = self.dt
        for p in self.pops:
            p[3] += dt
        self.pops = [p for p in self.pops if p[3] < 1.0]
        for f in self.flashes:
            f[2] += dt
        self.flashes = [f for f in self.flashes if f[2] < 0.35]
        for d in self.dust:
            d[0] += d[2] * dt; d[1] += d[3] * dt; d[4] += dt
        self.dust = [d for d in self.dust if d[4] < 0.5]
        if self.frame % 6 == 0:
            self.audio.set_tension(self.t, self.tension())
        self.n_max = max(self.n_max, len(self.bodies))
        if self.g.get("climax_by_count", True) and self.done_at is None and len(self.bodies) >= self.capacity:
            self.climax()
        if self.done_at is not None and self.broken_at is None and self.t > self.done_at + 1.3:
            self.break_ring()
        if self.broken_at is not None:
            for f in self.frags:
                f[2] += f[4] * dt; f[3] += f[5] * dt; f[5] += 2300 * dt; f[6] += f[7] * dt
            if self.frame % 3 == 0 and self.bodies:
                P = self.positions()
                self.remove_balls(np.nonzero((P[:, 1] > H + 60) | (P[:, 0] < -80) | (P[:, 0] > W + 80))[0])
            if self.end_at is None and self.t > self.broken_at + 3.2:
                self.end_at = self.t

    def contain(self):
        if not self.bodies or self.broken_at is not None or not self.ring_on:
            return
        P = self.positions()
        rad = np.hypot(P[:, 0] - self.cx, P[:, 1] - self.cy)
        lim = self.R - np.array(self.rad)
        for i in np.nonzero(rad > lim)[0]:
            b = self.bodies[i]
            ux, uy = (P[i, 0] - self.cx) / rad[i], (P[i, 1] - self.cy) / rad[i]
            b.position = (self.cx + ux * (lim[i] - 0.5), self.cy + uy * (lim[i] - 0.5))
            vx, vy = b.velocity
            vn = vx * ux + vy * uy
            if vn > 0:
                b.velocity = (vx - 1.6 * vn * ux, vy - 1.6 * vn * uy)
                if vn > 160 and self.rng.random() < 0.08:
                    self.audio.hit(self.t, min(1, vn / 700), "clack", self.pan(P[i, 0]), self.tension())

    # ---------- final ----------
    def climax(self):
        self.done_at = self.t
        self.winner = self.cur
        self.audio.set_climax(self.t)
        self.audio.event(self.t - 0.3, "riser", 1.0)
        self.audio.event(self.t, "boom", 1.0)
        self.audio.event(self.t + 0.35, "crack", 1.0)
        self.cam.kick(0.8)
        self.on_climax()

    def break_ring(self):
        """no entra nada más: el aro se parte y se sueltan todas las bolas."""
        self.broken_at = self.t
        self.space.remove(*self.ring_segs)
        self.ring_segs = []
        self.on_break()
        self.space.gravity = (0, 2300)
        self.space.damping = 0.9
        for b in self.bodies:
            dx, dy = b.position.x - self.cx, b.position.y - self.cy
            d = math.hypot(dx, dy) or 1
            sp = self.rng.uniform(250, 900) * (0.4 + 0.6 * d / self.R)
            b.velocity = (dx / d * sp + self.rng.uniform(-80, 80), dy / d * sp - self.rng.uniform(100, 500))
        n = 16
        for i in range(n):
            a0 = TAU * i / n + self.rng.uniform(-0.05, 0.05)
            a1 = TAU * (i + 1) / n + self.rng.uniform(-0.05, 0.05)
            am = (a0 + a1) / 2
            sp = self.rng.uniform(300, 700)
            self.frags.append([a0, a1, 0.0, 0.0, math.cos(am) * sp, math.sin(am) * sp - 300, 0.0, self.rng.uniform(-4, 4)])
        self.audio.event(self.t, "shatter", 1.0)
        self.audio.event(self.t, "boom", 0.8)
        self.cam.kick(1.0)

    # ---------- dibujo ----------
    def draw_world(self, c):
        ring = skia.Paint(Color4f=rgb((0.95, 0.95, 0.97), 1.0), AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=8)
        rr6 = self.R + 6
        if self.broken_at is None and self.ring_on:
            c.drawCircle(self.cx, self.cy, rr6, ring)
            frac = min(1.0, len(self.bodies) / self.capacity)
            arc = skia.Paint(Color4f=rgb(self.pal["accent"]), AntiAlias=True, Style=skia.Paint.kStroke_Style,
                             StrokeWidth=9, StrokeCap=skia.Paint.kRound_Cap)
            rr = self.R + 22
            if frac > 0:
                c.drawArc(skia.Rect(self.cx - rr, self.cy - rr, self.cx + rr, self.cy + rr), -90, 360 * frac, False, arc)
            if self.done_at is not None:
                self.draw_cracks(c, min(1.0, (self.t - self.done_at) / 1.2))
        else:
            for a0, a1, dx, dy, _, _, rot, _ in self.frags:
                c.save(); c.translate(self.cx + dx, self.cy + dy); c.rotate(math.degrees(rot))
                c.drawArc(skia.Rect(-rr6, -rr6, rr6, rr6), math.degrees(a0), math.degrees(a1 - a0), False, ring)
                c.restore()
        self.draw_balls(c)
        if self.dust:
            for ci in set(d[5] for d in self.dust):
                col = self.colors[ci]
                pts = [skia.Point(d[0], d[1]) for d in self.dust if d[5] == ci]
                c.drawPoints(skia.Canvas.kPoints_PointMode, pts,
                             skia.Paint(Color4f=rgb([min(1, v * 0.7 + 0.35) for v in col], 0.9), AntiAlias=True,
                                        StrokeWidth=3.0, StrokeCap=skia.Paint.kRound_Cap))
        fade = 1.0 if self.broken_at is None else max(0.0, 1 - (self.t - self.broken_at) / 0.35)
        if fade > 0:
            if fade < 1:
                c.saveLayerAlpha(None, int(255 * fade))
            self.draw_machine(c)
            if fade < 1:
                c.restore()
        for f in self.flashes:
            x, y, age = f[:3]
            fc = f[3] if len(f) > 3 else (1, 1, 1)
            k = age / 0.35
            c.drawCircle(x, y, 30 + 120 * k, skia.Paint(Color4f=skia.Color4f(*fc, 0.85 * (1 - k)), AntiAlias=True,
                                                       MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 16)))
        self.particles.draw(c)
        for p in self.pops:
            x, y, s, age = p[:4]
            col = p[4] if len(p) > 4 else (1, 1, 1)
            pop = 1 + 0.35 * max(0, 0.15 - age) / 0.15
            draw_text(c, s, x, y + 20, 62 * pop, col, stroke=10, alpha=min(1, (1.0 - age) * 3), max_w=360)

    def draw_cracks(self, c, k):
        if not hasattr(self, "_crack_lines"):
            self._crack_lines = []
            for _ in range(7):
                a = self.rng.uniform(0, TAU)
                pts = [(a, 0.0)]
                for j in range(5):
                    pts.append((pts[-1][0] + self.rng.uniform(-0.05, 0.05), (j + 1) * self.rng.uniform(10, 22)))
                self._crack_lines.append(pts)
        p = skia.Paint(Color4f=skia.Color4f(1, 1, 1, 0.95), AntiAlias=True, Style=skia.Paint.kStroke_Style,
                       StrokeWidth=3, StrokeCap=skia.Paint.kRound_Cap)
        rr = self.R + 6
        for pts in self._crack_lines:
            m = max(1, int(len(pts) * k))
            path = skia.Path()
            for j, (a, off) in enumerate(pts[:m]):
                side = -1 if j % 2 else 1
                x, y = self.cx + (rr + side * off) * math.cos(a), self.cy + (rr + side * off) * math.sin(a)
                path.moveTo(x, y) if j == 0 else path.lineTo(x, y)
            c.drawPath(path, p)

    def draw_balls(self, c):
        """esfera sombreada (borde oscuro + núcleo + brillo); si son grandes, con la cara del brainrot."""
        if not self.bodies:
            return
        P = self.positions()
        col = np.array(self.col)
        r = self.rad[0]
        if r >= 16 and self.g.get("faces", True):
            for (x, y), ci in zip(P, col):
                ch = self.chars[ci] if ci < len(self.chars) else None
                if ch is not None:
                    img, half = ch.sprite(round(r * 2) / 2)
                    c.drawImage(img, float(x) - half, float(y) - half)
                else:
                    self._ball_pts(c, [skia.Point(float(x), float(y))], self.colors[ci], r)
            return
        for ci in np.unique(col):
            sel = P[col == ci]
            self._ball_pts(c, [skia.Point(float(x), float(y)) for x, y in sel], self.colors[ci], r)

    @staticmethod
    def _ball_pts(c, pts, base, r):
        """estilo de la referencia: esfera de color plena, brillo claro arriba-izquierda, SIN contorno oscuro."""
        mid = [min(1, v * 0.8 + 0.2) for v in base]
        light = [min(1, v * 0.35 + 0.65) for v in base]
        c.drawPoints(skia.Canvas.kPoints_PointMode, pts,
                     skia.Paint(Color4f=rgb(base), AntiAlias=True, StrokeWidth=2 * r, StrokeCap=skia.Paint.kRound_Cap))
        m = [skia.Point(p.fX - r * 0.15, p.fY - r * 0.18) for p in pts]
        c.drawPoints(skia.Canvas.kPoints_PointMode, m,
                     skia.Paint(Color4f=rgb(mid, 0.9), AntiAlias=True, StrokeWidth=2 * r * 0.62, StrokeCap=skia.Paint.kRound_Cap))
        hl = [skia.Point(p.fX - r * 0.32, p.fY - r * 0.36) for p in pts]
        c.drawPoints(skia.Canvas.kPoints_PointMode, hl,
                     skia.Paint(Color4f=rgb(light, 0.95), AntiAlias=True, StrokeWidth=max(1.2, r * 0.42),
                                StrokeCap=skia.Paint.kRound_Cap))

    def draw_hud(self, c):
        L, acc = self.L, self.pal["accent"]
        n = self.n_max if self.broken_at is not None else len(self.bodies)
        done = self.done_at is not None
        if not done:
            draw_text(c, L["t1"], W / 2, 170, 74, (1, 1, 1), stroke=12)
            draw_text(c, L["t2"], W / 2, 258, 74, acc, stroke=12)
        else:
            draw_text(c, L["almost"], W / 2, 250, 76, (1, 1, 1), stroke=12)
        y = self.cy + self.R + 150
        num = f"{n:,}"
        wn, wb = text_width(num, 112), text_width(L["balls"], 44)
        x0 = W / 2 - (wn + 18 + wb) / 2
        draw_text(c, num, x0, y, 112, (1, 1, 1), align="left", stroke=12)
        draw_text(c, L["balls"], x0 + wn + 18, y, 44, (0.75, 0.75, 0.8), align="left", stroke=8)
        if done:
            dt = self.t - self.done_at
            k = min(1.0, dt / 0.2)
            if self.broken_at is None:
                box = skia.RRect.MakeRectXY(skia.Rect(W / 2 - 270, self.cy - 105, W / 2 + 270, self.cy + 35), 34, 34)
                c.drawRRect(box, skia.Paint(Color4f=skia.Color4f(0.05, 0.05, 0.08, 0.85 * k), AntiAlias=True))
                draw_text(c, L["full"], W / 2, self.cy + 10, 160 * (0.7 + 0.3 * k), acc, stroke=14)
            else:
                db = self.t - self.broken_at
                kb = min(1.0, db / 0.25)
                draw_text(c, L["broke"], W / 2, self.cy - 40, 150 * (0.7 + 0.3 * kb), (1, 0.35, 0.3), stroke=16, glow=14)
                if db > 1.5:
                    draw_text(c, L["cta1"], W / 2, H - 150, 58, (1, 1, 1), stroke=10)
                    draw_text(c, L["cta2"].format(n=self.round) + "  >>", W / 2, H - 78, 52, acc, stroke=10)

    # ---------- a implementar ----------
    def setup_machine(self): ...
    def machine_step(self): ...
    def draw_machine(self, c): ...
    def on_climax(self): ...
    def on_break(self): ...
