"""PUNCH FILL — lógica exacta de ref05 (ver reference/formats/punch/SPEC.md y reference/sheets/ref05_clap_*.png).

Ciclo (≈2.3 s):
1. BARRIDO: un brazo da la vuelta completa alrededor del pivote. Las varillas y guantes son PAREDES:
   el brazo empuja toda la pila delante de él y la comprime contra el otro brazo (la cuña se cierra).
2. Las bolas que se escapan por detrás del brazo quedan en la zona barrida y se tiñen del color del PRÓXIMO golpe.
3. COMPRESIÓN: cuando la cuña ya no tiene lugar, las bolas que sobran se pulverizan (polvo).
4. GOLPE: los guantes chocan → destello, toda la masa atrapada se pulveriza → "+N".
5. APERTURA: los brazos se abren y la cuña escupe la masa renacida (atrapadas + N) del color nuevo, que inunda el círculo.
El Pacer elige N (honesto: se muestra "+N"; al principio N = lo atrapado → "×2") y el ritmo.
"""
import math
import numpy as np
import pymunk
import skia

from engine.sim import Sim
from engine.gfx import W, H, rgb, draw_text, text_width
from characters import get as get_char

BALL, ARM = 4, 5
TAU = 2 * math.pi

TXT = {
    "en": {"t1": "CAN 1 BALL REFILL IT", "t2": "IN 60 SECONDS?", "balls": "BALLS", "full": "FULL!",
           "almost": "IT GETS THIS FULL...", "taking": "IS TAKING OVER", "wins": "WINS!",
           "cta1": "WHICH BRAINROT WINS NEXT?", "cta2": "SUBSCRIBE FOR ROUND {n}"},
    "es": {"t1": "¿PUEDE 1 BOLA LLENARLO", "t2": "EN 60 SEGUNDOS?", "balls": "BOLAS", "full": "¡LLENO!",
           "almost": "SE LLENA ASÍ...", "taking": "VA GANANDO", "wins": "¡GANA!",
           "cta1": "¿QUÉ BRAINROT GANA LA PRÓXIMA?", "cta2": "SUSCRIBITE PARA LA RONDA {n}"},
}


def wrap(a):
    return (a + math.pi) % TAU - math.pi


class Punch(Sim):
    SUBSTEPS = 6

    def setup(self):
        g = self.g
        self.L = TXT[g.get("lang", "en")]
        self.cx, self.cy, self.R = W / 2, 905, 455
        self.r = g["ball_r"]
        self.capacity = int(g.get("packing", 0.86) * (self.R / self.r) ** 2)
        self.space.gravity = (0, g["gravity"])
        self.space.iterations = 10
        self.space.use_spatial_hash(self.r * 2.2, 9000)
        segs = 120
        for i in range(segs):
            a0, a1 = TAU * i / segs, TAU * (i + 1) / segs
            rr = self.R + 6
            s = pymunk.Segment(self.space.static_body, (self.cx + rr * math.cos(a0), self.cy + rr * math.sin(a0)),
                               (self.cx + rr * math.cos(a1), self.cy + rr * math.sin(a1)), 6)
            s.elasticity, s.friction = 0.2, 0.4
            self.space.add(s)
        # brazos: varilla (pared) + guante (pared) — kinemáticos
        self.hw, self.hh = g["head_w"], g["head_h"]
        self.arm_len = self.R - self.hh / 2 - 4
        self.arms = []
        for k in range(2):
            b = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
            b.position = (self.cx, self.cy)
            L, hw, hh = self.arm_len, self.hw, self.hh
            rod = pymunk.Segment(b, (14, 0), (L - hh / 2, 0), 6)
            head = pymunk.Poly(b, [(L - hh / 2, -hw / 2), (L + hh / 2, -hw / 2), (L + hh / 2, hw / 2),
                                   (L - hh / 2, hw / 2)], radius=3)
            for s in (rod, head):
                s.elasticity, s.friction, s.collision_type = 0.1, 0.6, ARM
            self.space.add(b, rod, head)
            self.arms.append(b)
        hub = pymunk.Circle(self.space.static_body, 16, (self.cx, self.cy))
        self.space.add(hub)
        # ángulo mínimo de la cuña: los guantes se tocan
        self.clap_gap = 2 * math.atan2(self.hw / 2 + 2, self.arm_len)
        # estado del ciclo
        self.ang = [g["start_angle"], g["start_angle"] + self.clap_gap]
        self.mover, self.dirn = 1, 1          # qué brazo barre y en qué sentido
        self.phase = "sweep"
        self.ph_t = 0.0
        self.cycle = g.get("cycle", 2.3)
        self.drift = g.get("drift", 0.35)     # el brazo fijo también se mueve un poco (el golpe cambia de lugar)
        for b, a in zip(self.arms, self.ang):
            b.angle = a
        self.bodies, self.col = [], []        # col = índice de brainrot de cada bola
        self.chars = [get_char(k) for k in g["chars"]]
        self.cur = 0                          # color de la masa
        self.reborn = 0                       # bolas por renacer en la cuña al abrir
        self.pops, self.flashes, self.dust = [], [], []
        self.last_voice = -9
        self.round = g.get("round", 2)
        self.winner = 0
        self._add(self.cx + 40, self.cy + 200, 0, 0, 0)
        self._start_sweep(self.ang, first=True)

    # ---------- bolas ----------
    def _add(self, x, y, vx, vy, col):
        b = pymunk.Body(1, pymunk.moment_for_circle(1, 0, self.r))
        b.position, b.velocity = (x, y), (vx, vy)
        s = pymunk.Circle(b, self.r)
        s.elasticity, s.friction, s.collision_type = 0.15, 0.3, BALL
        self.space.add(b, s)
        self.bodies.append(b)
        self.col.append(col)

    def _remove(self, idx):
        idx = set(int(i) for i in idx)
        keep_b, keep_c = [], []
        for i, (b, c) in enumerate(zip(self.bodies, self.col)):
            if i in idx:
                self.space.remove(b, *b.shapes)
            else:
                keep_b.append(b); keep_c.append(c)
        self.bodies, self.col = keep_b, keep_c

    def positions(self):
        return np.array([b.position for b in self.bodies], np.float64).reshape(-1, 2)

    def tension(self):
        return min(1.0, len(self.bodies) / self.capacity) ** 1.2

    def nxt(self):
        return (self.cur + 1) % len(self.chars)

    # ---------- geometría de la cuña ----------
    def _wedge(self):
        """cuña = sector delante del brazo que barre, hasta el brazo fijo. Devuelve (inicio, ancho) en sentido de barrido."""
        m, f = self.ang[self.mover], self.ang[1 - self.mover]
        width = (f - m) * self.dirn % TAU
        return m, width

    def _rel(self, P, start):
        phi = np.arctan2(P[:, 1] - self.cy, P[:, 0] - self.cx)
        return ((phi - start) * self.dirn) % TAU

    # ---------- Pacer: cuánto suma cada golpe ----------
    def _want(self, t):
        g = self.g
        return self.capacity * min(1.0, max(0.0, t) / g["target_t"]) ** g["curve"]

    # ---------- ciclo ----------
    def update(self):
        g, dt = self.g, self.dt
        self.ph_t += dt
        P = self.positions() if self.bodies else np.zeros((0, 2))
        rad = np.hypot(P[:, 0] - self.cx, P[:, 1] - self.cy) if len(P) else np.zeros(0)
        new_ang = list(self.ang)
        fixed = 1 - self.mover
        new_ang[fixed] += self.drift * dt * self.dirn     # el fijo se corre en el mismo sentido (el golpe cambia de lugar)
        if self.done_at is not None:
            for k in range(2):
                self.arms[k].angular_velocity = 0
            self._tick_fx(P)
            return

        if self.phase == "sweep":
            # el brazo recorre la vuelta: arranca suave y llega acelerando al golpe
            T = self.cycle
            u = min(1.0, self.ph_t / T)
            prog = (u ** 1.45)
            width_now = self.clap_gap + self.sweep_total * (1 - prog)
            new_ang[self.mover] = new_ang[fixed] - self.dirn * width_now
            swept = (self.sweep_total + self.clap_gap) - width_now + (new_ang[fixed] - self.sweep_fixed0) * self.dirn
            start, width = self._wedge_from(new_ang)
            if len(P):
                rel = self._rel(P, start)
                inside = (rel < width) & (rad < self.R + 2)
                # anti-tunneling: las que quedaron "detrás" del brazo pero muy pegadas, vuelven adelante
                moved = abs(wrap(new_ang[self.mover] - self.ang[self.mover])) * 1.6 + 0.03
                crossed = (rel > TAU - moved - self.r / np.maximum(rad, 30)) & (rad > 20) & (rad < self.R)
                fixed_idx = np.nonzero(crossed)[0][:400]
                for i in fixed_idx:
                    b = self.bodies[i]
                    a = new_ang[self.mover] + self.dirn * (self.r / max(rad[i], 30) + 0.02)
                    b.position = (self.cx + rad[i] * math.cos(a), self.cy + rad[i] * math.sin(a))
                    b.velocity = (b.velocity.x * 0.3, b.velocity.y * 0.3)
                # zona barrida: las que se escapan se tiñen del color del próximo golpe
                col = np.array(self.col)
                behind = (TAU - rel) < swept      # zona que el brazo ya barrió
                behind[fixed_idx] = False
                dye = np.nonzero(behind & ~inside & (col == self.cur))[0]
                for i in dye:
                    self.col[i] = self.nxt()
                # compresión: si la cuña ya no tiene lugar, las que sobran se pulverizan
                area = 0.5 * width * (self.R ** 2 - 20 ** 2)
                fits = int(area * 0.84 / (math.pi * self.r ** 2))
                idx = np.nonzero(inside)[0]
                if len(idx) > fits and width < 1.2:
                    over = len(idx) - fits
                    order = idx[np.argsort(-rel[idx])][:over]   # las más cercanas al vértice que se cierra
                    self._crush(order, P)
            if u >= 1.0:
                self._clap(new_ang)
        elif self.phase == "open":
            # se abren los brazos y la cuña escupe la masa renacida
            T = self.open_T
            u = min(1.0, self.ph_t / T)
            open_w = self.clap_gap + (self.open_gap - self.clap_gap) * (1 - (1 - u) ** 2.2)
            new_ang[self.mover] = self.ang_fixed_at_clap - self.dirn * open_w
            start, width = self._wedge_from(new_ang)
            # renacimiento: se llena la cuña abierta a medida que hay lugar
            if self.reborn > 0:
                area = 0.5 * width * (self.R ** 2 - 25 ** 2)
                cap_now = int(area * 0.8 / (math.pi * self.r ** 2))
                inside = 0
                if len(P):
                    rel = self._rel(P, start)
                    inside = int(np.sum((rel < width) & (rad < self.R)))
                room = max(0, cap_now - inside)
                n = min(self.reborn, room, 320)
                self.reborn -= self._spawn_in(start, width, n)
            if u >= 1.0 and self.reborn <= 0:
                self._start_sweep(new_ang)
            elif u >= 1.0:
                # la cuña ya está abierta: lo que falta sale por cualquier hueco libre (de afuera hacia adentro)
                self.reborn -= self._spawn_in(start, TAU * 0.999, min(self.reborn, 320))
                if self.ph_t > T + 1.5:
                    self.reborn = 0

        for k in range(2):
            self.arms[k].angular_velocity = wrap(new_ang[k] - self.ang[k]) / dt
        self.ang = new_ang
        if self.bodies:
            P = self.positions()
            rad = np.hypot(P[:, 0] - self.cx, P[:, 1] - self.cy)
            self._contain(P, rad)
        self._tick_fx(P)
        if self.frame % 6 == 0:
            self.audio.set_tension(self.t, self.tension())
        if self.frame % 2 == 0:
            # retumbe: velocidad del brazo que barre x cuánta masa se mueve
            wv = abs(self.arms[self.mover].angular_velocity)
            mass = min(1.0, len(self.bodies) / 600)
            self.audio.rumble(self.t, min(1.0, 0.12 + 0.25 * wv * (0.25 + 0.75 * mass)))

    def _wedge_from(self, ang):
        m, f = ang[self.mover], ang[1 - self.mover]
        return m, ((f - m) * self.dirn) % TAU

    def _start_sweep(self, ang, first=False):
        # a veces barre el otro brazo (el golpe cambia de lugar); siempre por el lado LARGO (empuja toda la pila)
        if not first and self.rng.random() < 0.35:
            self.mover = 1 - self.mover
        best = None
        for d in (1, -1):
            self.dirn = d
            w = self._wedge_from(ang)[1]
            if best is None or w > best[1]:
                best = (d, w)
        self.dirn, width = best
        self.sweep_from = ang[self.mover]
        self.sweep_fixed0 = ang[1 - self.mover]
        self.sweep_total = max(0.5, width - self.clap_gap)
        self.phase, self.ph_t = "sweep", 0.0
        n = len(self.bodies)
        # el Pacer acelera o frena la vuelta
        ratio = n / max(1.0, self._want(self.t))
        base = self.g.get("cycle", 2.3)
        k = 0.6 if ratio < 0.5 else (0.8 if ratio < 0.8 else (1.2 if ratio > 1.15 else 1.0))
        self.cycle = base * k * self.rng.uniform(0.92, 1.08)

    def _clap(self, ang):
        """golpe: toda la masa atrapada se pulveriza y renace del color nuevo, +N."""
        start, width = self._wedge_from(ang)
        P = self.positions() if self.bodies else np.zeros((0, 2))
        k = 0
        if len(P):
            rad = np.hypot(P[:, 0] - self.cx, P[:, 1] - self.cy)
            rel = self._rel(P, start)
            col = np.array(self.col)
            # la cuña incluye las caras de los dos guantes (lo que queda apretado entre ellos)
            margin = (self.hw / 2 + 2 * self.r) / np.maximum(rad, 60)
            inside = np.nonzero(((rel < width + margin) | (rel > TAU - margin)) & (rad < self.R + 2))[0]
            k = len(inside) + self.crushed_since_sweep
            self._crush(inside, P, count=False)
        else:
            k = self.crushed_since_sweep
        self.crushed_since_sweep = 0
        n_now = len(self.bodies)
        # +N: al principio duplica; después lo que pida la curva (siempre visible y honesto)
        want = self._want(self.t + self.cycle)
        cap_mult = 2 if n_now + k < 300 else 1      # al principio puede triplicar (como 4→13 en ref05)
        delta = int(max(0, min(k * cap_mult, want - (n_now + k))))
        if k > 0 and delta == 0 and n_now + k < self.capacity:
            delta = max(1, k // 25)
        delta = min(delta, self.capacity - (n_now + k))
        self.reborn = k + delta
        mid = start + self.dirn * width / 2
        hx, hy = self.cx + self.arm_len * math.cos(mid), self.cy + self.arm_len * math.sin(mid)
        lx, ly = self.cx + 0.6 * self.arm_len * math.cos(mid), self.cy + 0.6 * self.arm_len * math.sin(mid)
        self.cur = self.nxt()
        self.col = [self.cur] * len(self.bodies)
        self.flashes.append([hx, hy, 0.0])
        if k > 0:
            lab = "×2" if delta == k else ("×3" if delta == 2 * k else f"+{delta}")
            self.pops.append([lx, ly, lab, 0.0])
        self.cam.kick(0.25 + 0.35 * self.tension())
        ten, pan = self.tension(), self.pan(hx)
        e = min(1.0, 0.45 + k / 400)
        self.audio.hit(self.t, e, "punch", pan, ten)
        self.audio.hit(self.t + 0.002, e, "squish", pan, ten)
        for i in range(int(min(9, 2 + 1.6 * math.log2(1 + max(delta, 1))))):
            self.audio.event(self.t + 0.05 + i * 0.03, "pop", 0.9 + 0.5 * ten + 0.07 * i)
        if self.t - self.last_voice > self.g.get("voice_gap", 2.4):
            self.audio.voice(self.t + 0.1, self.chars[self.cur].key, "short", pan)
            self.last_voice = self.t
        self.ang_fixed_at_clap = ang[1 - self.mover]
        self.phase, self.ph_t = "open", 0.0
        # el brazo vuelve barriendo hacia atrás casi toda la vuelta: la masa nueva sale en abanico detrás de él
        # vuelve hasta quedar pegado al otro brazo por el lado de atrás (la "V" chica de ref05)
        self.open_gap = TAU - self.clap_gap - self.rng.uniform(0.12, 0.35)
        self.open_T = self.rng.uniform(1.0, 1.25)

    crushed_since_sweep = 0

    def _crush(self, idx, P, count=True):
        if len(idx) == 0:
            return
        for i in idx[:400]:
            x, y = P[i]
            if self.rng.random() < 0.5:
                self.dust.append([x, y, self.rng.uniform(-90, 90), self.rng.uniform(-90, 90), 0.0, self.col[i]])
        if count:
            self.crushed_since_sweep += len(idx)
        self._remove(idx)
        if len(self.dust) > 1500:
            self.dust = self.dust[-1500:]

    def _spawn_in(self, start, width, n):
        """renacen densas dentro de la cuña abierta: rejilla hexagonal sobre huecos libres (grilla de ocupación)."""
        if n <= 0:
            return 0
        rng = self.rng
        d = 2 * self.r * 1.04
        cell = d
        occ = set()
        if self.bodies:
            P = self.positions()
            for x, y in P:
                occ.add((int(x // cell), int(y // cell)))
        placed = 0
        rr = self.R - self.r - 1
        out = -self.dirn
        while rr > 26 and placed < n:      # de afuera hacia adentro: la masa sale por el borde de la cuña
            steps = max(1, int(width * rr / d))
            js = list(range(steps))
            for j in js:
                if placed >= n:
                    break
                a = start + self.dirn * (j + 0.5) * width / steps
                x, y = self.cx + rr * math.cos(a), self.cy + rr * math.sin(a)
                key = (int(x // cell), int(y // cell))
                if key in occ:
                    continue
                occ.add(key)
                self._add(x + rng.uniform(-1, 1), y + rng.uniform(-1, 1),
                          rng.uniform(-30, 30) + 90 * math.cos(a + out * 1.3),
                          rng.uniform(-30, 30) + 90 * math.sin(a + out * 1.3), self.cur)
                placed += 1
            rr -= d * 0.87
        if len(self.bodies) >= self.capacity * 0.97 and self.done_at is None:
            self._climax()
        return placed

    def _climax(self):
        self.done_at = self.t
        self.winner = self.cur
        self.audio.set_climax(self.t)
        self.audio.event(self.t - 0.3, "riser", 1.0)
        self.audio.event(self.t, "boom", 1.0)
        self.audio.event(self.t + 0.05, "chord", 1.0)
        self.audio.voice(self.t + 0.9, self.chars[self.cur].key, "full", 0.0, 1.2)
        self.cam.kick(0.8)

    def _contain(self, P, rad):
        if not len(P):
            return
        lim = self.R - self.r
        for i in np.nonzero(rad > lim)[0]:
            b = self.bodies[i]
            ux, uy = (P[i, 0] - self.cx) / rad[i], (P[i, 1] - self.cy) / rad[i]
            b.position = (self.cx + ux * (lim - 0.5), self.cy + uy * (lim - 0.5))
            vx, vy = b.velocity
            vn = vx * ux + vy * uy
            if vn > 0:
                b.velocity = (vx - 1.2 * vn * ux, vy - 1.2 * vn * uy)
        # golpecitos contra el aro (muestreados)
        if self.frame % 4 == 0:
            for i in np.nonzero(rad > lim - 1)[0][:1]:
                self.audio.hit(self.t + self.rng.uniform(0, self.dt), 0.2 + 0.3 * self.rng.random(), "clack",
                               self.pan(P[i, 0]), self.tension())

    def _tick_fx(self, P):
        dt = self.dt
        for p in self.pops:
            p[3] += dt
        self.pops = [p for p in self.pops if p[3] < 1.1]
        for f in self.flashes:
            f[2] += dt
        self.flashes = [f for f in self.flashes if f[2] < 0.35]
        for d in self.dust:
            d[0] += d[2] * dt; d[1] += d[3] * dt; d[4] += dt
        self.dust = [d for d in self.dust if d[4] < 0.6]
        if self.done_at is not None and self.end_at is None and self.t > self.done_at + 5.0:
            self.end_at = self.t

    # ---------- dibujo ----------
    def draw_world(self, c):
        ring = skia.Paint(Color4f=rgb((1, 1, 1), 0.85), AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=4)
        c.drawCircle(self.cx, self.cy, self.R + 6, ring)
        frac = min(1.0, len(self.bodies) / self.capacity)
        if frac > 0:
            arc = skia.Paint(Color4f=rgb(self.pal["accent"]), AntiAlias=True, Style=skia.Paint.kStroke_Style,
                             StrokeWidth=9, StrokeCap=skia.Paint.kRound_Cap)
            rr = self.R + 22
            c.drawArc(skia.Rect(self.cx - rr, self.cy - rr, self.cx + rr, self.cy + rr), -90, 360 * frac, False, arc)
        self.draw_balls(c)
        if self.dust:
            for ci in set(d[5] for d in self.dust):
                col = self.chars[ci].color
                pts = [skia.Point(d[0], d[1]) for d in self.dust if d[5] == ci]
                c.drawPoints(skia.Canvas.kPoints_PointMode, pts,
                             skia.Paint(Color4f=rgb([min(1, v * 0.7 + 0.35) for v in col], 0.85), AntiAlias=True,
                                        StrokeWidth=3.2, StrokeCap=skia.Paint.kRound_Cap))
        self.draw_arms(c)
        for x, y, age in self.flashes:
            k = age / 0.35
            c.drawCircle(x, y, 30 + 110 * k, skia.Paint(Color4f=skia.Color4f(1, 1, 1, 0.85 * (1 - k)), AntiAlias=True,
                                                       MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 16)))
        for x, y, s, age in self.pops:
            pop = 1 + 0.35 * max(0, 0.15 - age) / 0.15
            draw_text(c, s, x, y + 20, 66 * pop, (1, 1, 1), stroke=10, alpha=min(1, (1.1 - age) * 3), max_w=360)

    def draw_balls(self, c):
        if not self.bodies:
            return
        P = self.positions()
        col = np.array(self.col)
        r = self.r
        for ci in np.unique(col):
            base = self.chars[ci].color
            sel = P[col == ci]
            pts = [skia.Point(float(x), float(y)) for x, y in sel]
            dark = [v * 0.5 for v in base]
            light = [min(1, v * 0.55 + 0.5) for v in base]
            c.drawPoints(skia.Canvas.kPoints_PointMode, pts,
                         skia.Paint(Color4f=rgb(dark), AntiAlias=True, StrokeWidth=2 * r, StrokeCap=skia.Paint.kRound_Cap))
            c.drawPoints(skia.Canvas.kPoints_PointMode, pts,
                         skia.Paint(Color4f=rgb(base), AntiAlias=True, StrokeWidth=2 * r - 2.6, StrokeCap=skia.Paint.kRound_Cap))
            hl = [skia.Point(p.fX - r * 0.3, p.fY - r * 0.32) for p in pts]
            c.drawPoints(skia.Canvas.kPoints_PointMode, hl,
                         skia.Paint(Color4f=rgb(light, 0.95), AntiAlias=True, StrokeWidth=r * 0.7, StrokeCap=skia.Paint.kRound_Cap))

    def draw_arms(self, c):
        L, hw, hh = self.arm_len, self.hw, self.hh
        rod = skia.Paint(Color4f=rgb((0.62, 0.63, 0.67)), AntiAlias=True, StrokeWidth=13, StrokeCap=skia.Paint.kRound_Cap)
        rod_hi = skia.Paint(Color4f=rgb((0.9, 0.9, 0.93)), AntiAlias=True, StrokeWidth=5, StrokeCap=skia.Paint.kRound_Cap)
        for b in self.arms:
            c.save(); c.translate(self.cx, self.cy); c.rotate(math.degrees(b.angle))
            c.drawLine(0, 0, L - hh / 2, 0, rod)
            c.drawLine(0, -2, L - hh / 2, -2, rod_hi)
            c.translate(L, 0)
            _glove(c, hw, hh)
            c.restore()
        c.drawCircle(self.cx, self.cy, 18, skia.Paint(Color4f=rgb((0.85, 0.86, 0.9)), AntiAlias=True))
        c.drawCircle(self.cx, self.cy, 18, skia.Paint(Color4f=rgb((0.3, 0.3, 0.35)), AntiAlias=True,
                                                      Style=skia.Paint.kStroke_Style, StrokeWidth=3))
        c.drawCircle(self.cx, self.cy, 6, skia.Paint(Color4f=rgb((0.3, 0.3, 0.35)), AntiAlias=True))

    def draw_hud(self, c):
        L, acc = self.L, self.pal["accent"]
        n = len(self.bodies)
        done = self.done_at is not None
        if done and self.t - self.done_at > 0.3:
            draw_text(c, L["almost"], W / 2, 250, 76, (1, 1, 1), stroke=12)
        else:
            draw_text(c, L["t1"], W / 2, 170, 78, (1, 1, 1), stroke=12)
            draw_text(c, L["t2"], W / 2, 260, 78, acc, stroke=12)
        y = self.cy + self.R + 150
        num = f"{n:,}"
        wn, wb = text_width(num, 112), text_width(L["balls"], 44)
        x0 = W / 2 - (wn + 18 + wb) / 2
        draw_text(c, num, x0, y, 112, (1, 1, 1), align="left", stroke=12)
        draw_text(c, L["balls"], x0 + wn + 18, y, 44, (0.75, 0.75, 0.8), align="left", stroke=8)
        ch = self.chars[self.cur]
        label = f"{ch.name} {L['taking']}"
        tw = min(text_width(label, 46), 760)
        img, half = ch.sprite(40)
        x0 = W / 2 - (tw + 100) / 2
        c.drawImage(img, x0 - half + 40, y + 96 - half)
        draw_text(c, label, x0 + 100, y + 112, 46, ch.color, align="left", stroke=8, max_w=760)
        if done:
            dt = self.t - self.done_at
            k = min(1.0, dt / 0.2)
            c.drawCircle(self.cx, self.cy, self.R, skia.Paint(Color4f=skia.Color4f(0, 0, 0, min(0.5, dt)), AntiAlias=True))
            box = skia.RRect.MakeRectXY(skia.Rect(W / 2 - 290, self.cy - 120, W / 2 + 290, self.cy + 40), 34, 34)
            c.drawRRect(box, skia.Paint(Color4f=skia.Color4f(0.05, 0.05, 0.08, 0.88 * k), AntiAlias=True))
            draw_text(c, L["full"], W / 2, self.cy + 10, 170 * (0.7 + 0.3 * k), acc, stroke=14)
            if dt > 1.0:
                w = self.chars[self.winner]
                img, half = w.sprite(95)
                c.drawImage(img, W / 2 - half, self.cy + 70)
                draw_text(c, f"{w.name} {L['wins']}", W / 2, self.cy + 330, 92, w.color, stroke=14)
            if dt > 2.8:
                draw_text(c, L["cta1"], W / 2, H - 150, 58, (1, 1, 1), stroke=10)
                draw_text(c, L["cta2"].format(n=self.round) + "  >>", W / 2, H - 78, 52, acc, stroke=10)


def _glove(c, hw, hh):
    """guante gris metálico como el de la referencia: cuerpo, puño, pulgar y nudillos."""
    outline = skia.Paint(Color4f=rgb((0.25, 0.25, 0.28)), AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=4)
    sh = skia.GradientShader.MakeLinear([(0, -hw / 2), (0, hw / 2)],
                                        [rgb((0.9, 0.9, 0.92)).toColor(), rgb((0.55, 0.56, 0.6)).toColor()])
    fill = skia.Paint(Shader=sh, AntiAlias=True)
    body = skia.RRect.MakeRectXY(skia.Rect(-hh / 2, -hw / 2, hh * 0.32, hw / 2), 18, 18)
    c.drawRRect(body, fill); c.drawRRect(body, outline)
    cuff = skia.RRect.MakeRectXY(skia.Rect(hh * 0.22, -hw * 0.42, hh / 2, hw * 0.42), 8, 8)
    c.drawRRect(cuff, fill); c.drawRRect(cuff, outline)
    thumb = skia.RRect.MakeRectXY(skia.Rect(-hh * 0.25, hw * 0.28, hh * 0.15, hw * 0.62), 10, 10)
    c.drawRRect(thumb, fill); c.drawRRect(thumb, outline)
    line = skia.Paint(Color4f=rgb((0.38, 0.38, 0.42)), AntiAlias=True, StrokeWidth=3)
    for k in (-0.22, 0.0, 0.22):
        c.drawLine(-hh / 2 + 6, k * hw, -hh * 0.05, k * hw, line)
    c.drawLine(hh * 0.3, -hw * 0.3, hh * 0.3, hw * 0.3, line)
