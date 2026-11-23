"""PRENSA ×4 — lógica de la referencia nexusboxlab_press_x4.mp4 ("cada vez que aplastás una pelota, aparecen 4 más").
Ver reference/formats/press/SPEC.md.

Ciclo (~3 s, analizado a 10 fps):
1. ABIERTO: 4 barras forman un cuadrado girado 45° con huecos en las esquinas; las bolas vuelan y rebotan.
2. CIERRE: el cuadrado se achica hacia el centro empujando lo que tiene adentro; lo que ya no entra se aplasta.
3. GOLPE: las barras se cruzan en una X en el centro → todo lo atrapado queda aplastado (destello + polvo).
4. ×4: por cada bola aplastada salen 4 nuevas, en 4 masas de color nuevo disparadas por los 4 huecos (arriba, abajo, izq, der).
5. APERTURA: el cuadrado vuelve a abrirse y empuja todo hacia el borde; las bolas rebotan y vuelven al centro.
Lo que no estaba adentro del cuadrado no se multiplica y conserva su color.
"""
import math
import numpy as np
import pymunk
import skia

from formats.arena import Arena, TAU
from engine.gfx import rgb

TXT = {
    "en": {"t1": "EVERY CRUSHED BALL", "t2": "BECOMES 4 MORE", "balls": "BALLS", "full": "FULL!",
           "almost": "IT GETS THIS FULL...", "broke": "IT BROKE!",
           "cta1": "WHICH MACHINE IS NEXT?", "cta2": "SUBSCRIBE FOR PART {n}"},
    "es": {"t1": "CADA BOLA APLASTADA", "t2": "SE VUELVE 4 MÁS", "balls": "BOLAS", "full": "¡LLENO!",
           "almost": "SE LLENA ASÍ...", "broke": "¡SE ROMPIÓ!",
           "cta1": "¿QUÉ MÁQUINA SIGUE?", "cta2": "SUSCRIBITE PARA LA PARTE {n}"},
}


def ease_in(u):
    u = min(1.0, max(0.0, u))
    return 1 - math.cos(math.pi * u / 2)          # arranca suave, llega rápido (golpe)


def ease_out(u):
    u = min(1.0, max(0.0, u))
    return math.sin(math.pi * u / 2)              # sale rápido, frena suave


class Press(Arena):
    TXT = TXT

    def setup_machine(self):
        g = self.g
        self.d_open = g.get("d_open", 0.62) * self.R
        self.half = g.get("bar_half", 0.36) * self.R
        self.bar_w = 9
        self.mult = g.get("mult", 4)
        self.bars = []
        for k in range(4):
            a = math.radians(45 + 90 * k)
            u = (math.cos(a), math.sin(a))
            t = (-u[1], u[0])
            b = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
            b.position = (self.cx + u[0] * self.d_open, self.cy + u[1] * self.d_open)
            s = pymunk.Segment(b, (-t[0] * self.half, -t[1] * self.half), (t[0] * self.half, t[1] * self.half), self.bar_w)
            s.elasticity, s.friction = 0.4, 0.4
            self.space.add(b, s)
            self.bars.append((b, u, t))
        self.d = self.d_open
        self.phase, self.ph_t = "wait", 0.0
        self.T = dict(wait=g.get("t_wait", 0.6), close=g.get("t_close", 0.8), hold=0.3, open=g.get("t_open", 0.85))
        self.crushed = 0
        self.presses = 0
        # la primera bola: grande, con cara, ya en movimiento dentro del cuadrado
        self.add_ball(self.cx - 0.12 * self.R, self.cy - 0.1 * self.R, 160, 90, 0)

    # ---------- geometría ----------
    def inside(self, P, d):
        """bolas dentro del cuadrado (las 4 barras): distancia a lo largo de cada normal < d."""
        rel = P - np.array([self.cx, self.cy])
        ok = np.ones(len(P), bool)
        for _, u, _ in self.bars:
            ok &= (rel[:, 0] * u[0] + rel[:, 1] * u[1]) < d - self.bar_w * 0.5
        return ok

    def _set_d(self, d):
        for b, u, _ in self.bars:
            target = (self.cx + u[0] * d, self.cy + u[1] * d)
            b.velocity = ((target[0] - b.position.x) / self.dt, (target[1] - b.position.y) / self.dt)
        self.d_next = d

    def _pull_center(self):
        """atracción suave hacia el centro (en la referencia las sueltas derivan hacia adentro entre golpes)."""
        gc = self.g.get("center_pull", 160) * self.dt
        if gc <= 0 or not self.bodies or self.broken_at is not None:
            return
        P = self.positions()
        dx, dy = self.cx - P[:, 0], self.cy - P[:, 1]
        dist = np.maximum(np.hypot(dx, dy), 1.0)
        ax, ay = dx / dist * gc, dy / dist * gc
        for b, x, y in zip(self.bodies, ax, ay):
            v = b.velocity
            b.velocity = (v.x + x, v.y + y)

    def step(self):
        self._pull_center()
        super().step()
        # las barras quedan exactamente donde tienen que estar (cinemáticas)
        for b, u, _ in self.bars:
            b.position = (self.cx + u[0] * self.d, self.cy + u[1] * self.d)

    # ---------- ciclo ----------
    def machine_step(self):
        self.ph_t += self.dt
        T = self.T
        ph = self.phase
        if ph == "wait":
            d = self.d_open
            if self.ph_t >= T["wait"]:
                self.phase, self.ph_t = "close", 0.0
        elif ph == "close":
            u = self.ph_t / T["close"]
            d = self.d_open * (1 - ease_in(u))
            self._squeeze(d)
            if u >= 1:
                d = 0.0
                self._press()
                self.phase, self.ph_t = "hold", 0.0
        elif ph == "hold":
            d = 0.0
            if self.ph_t >= T["hold"]:
                self.phase, self.ph_t = "open", 0.0
        else:  # open
            u = self.ph_t / T["open"]
            d = self.d_open * ease_out(u)
            if u >= 1:
                d = self.d_open
                self.phase, self.ph_t = "wait", 0.0
        self._set_d(d)
        self.d = d
        if self.frame % 2 == 0:
            sp = abs(self.d_next - getattr(self, "_d_prev", self.d_next)) / (2 * self.dt)
            self._d_prev = self.d_next
            self.audio.rumble(self.t, min(1.0, 0.08 + sp / 900 * (0.3 + 0.7 * min(1, len(self.bodies) / 500))))

    def _squeeze(self, d):
        """lo que ya no entra en el cuadrado que se achica se aplasta (cuenta para el ×4)."""
        if not self.bodies:
            return
        P = self.positions()
        ins = np.nonzero(self.inside(P, d + self.rad[0]))[0]
        side = max(0.0, 2 * (d - self.bar_w))
        fits = int(side * side * 0.82 / (math.pi * self.rad[0] ** 2))
        if len(ins) > fits:
            rel = P[ins] - np.array([self.cx, self.cy])
            far = np.argsort(-np.max(np.abs(rel @ np.array([[0.7071, -0.7071], [0.7071, 0.7071]])), axis=1))
            gone = ins[far[: len(ins) - fits]]
            self.crush_fx(gone, P)
            self.crushed += len(gone)
            self.remove_balls(gone)

    def _press(self):
        """golpe: lo que quedó adentro se aplasta; por cada aplastada salen 4 en 4 masas por los huecos."""
        self.presses += 1
        k = self.crushed
        if self.bodies:
            P = self.positions()
            ins = np.nonzero(self.inside(P, self.rad[0] * 3 + self.bar_w))[0]
            self.crush_fx(ins, P)
            k += len(ins)
            self.remove_balls(ins)
        self.crushed = 0
        ten = self.tension()
        self.flashes.append([self.cx, self.cy, 0.0])
        self.cam.kick(0.2 + 0.4 * ten)
        self.audio.hit(self.t, min(1.0, 0.5 + k / 200), "punch", 0.0, ten)
        self.audio.event(self.t, "slam", 0.7)
        if k == 0:
            return
        n_new = min(k * self.mult, self.capacity + 50 - len(self.bodies))
        self.cur = (self.cur + 1) % len(self.colors)
        self.resize_all_for(len(self.bodies) + n_new)
        self._spawn_blobs(n_new)
        self.audio.hit(self.t + 0.003, min(1.0, 0.5 + k / 200), "squish", 0.0, ten)
        for i in range(int(min(9, 2 + 1.6 * math.log2(1 + n_new)))):
            self.audio.event(self.t + 0.05 + i * 0.028, "pop", 0.9 + 0.5 * ten + 0.07 * i)
        self.pops.append([self.cx, self.cy - 0.06 * self.R, f"×{self.mult}" if k < 30 else f"+{n_new}", 0.0])

    def resize_all_for(self, n):
        # el tamaño se achica solo y de a poco (formats/sizing.py); las nuevas nacen del tamaño actual
        self._r_spawn = self.rad[0] if self.rad else self.r_big

    def _spawn_blobs(self, n):
        """4 masas (arriba/abajo/izq/der) que salen disparadas por los huecos de la X."""
        r = self._r_spawn
        d = 2 * r * 1.03
        per = [n // 4 + (1 if i < n % 4 else 0) for i in range(4)]
        for q in range(4):
            a = math.radians(90 * q)
            ux, uy = math.cos(a), math.sin(a)
            tx, ty = -uy, ux
            m = per[q]
            if m == 0:
                continue
            # blob compacto (rejilla hexagonal) que arranca pegado al centro de la X
            rows = max(1, int(math.sqrt(m) + 0.5))
            placed = 0
            j = 0
            while placed < m:
                row, colk = divmod(j, rows)
                off_t = (colk - (rows - 1) / 2) * d + (d / 2 if row % 2 else 0)
                off_u = 0.16 * self.R + row * d * 0.87
                x = self.cx + ux * off_u + tx * off_t
                y = self.cy + uy * off_u + ty * off_t
                j += 1
                if math.hypot(x - self.cx, y - self.cy) > self.R - r - 2:
                    off_u = self.rng.uniform(0.16, 0.8) * self.R
                    off_t = self.rng.uniform(-0.25, 0.25) * self.R
                    x, y = self.cx + ux * off_u + tx * off_t, self.cy + uy * off_u + ty * off_t
                sp = self.rng.uniform(280, 560)
                spread = self.rng.uniform(-0.25, 0.25)
                vx = (ux * math.cos(spread) - uy * math.sin(spread)) * sp
                vy = (uy * math.cos(spread) + ux * math.sin(spread)) * sp
                self.add_ball(x, y, vx, vy, self.cur)
                placed += 1
        self.particles.burst(self.cx, self.cy, self.colors[self.cur], n=24, speed=700, size=5)

    # ---------- dibujo ----------
    def draw_machine(self, c):
        """4 barras metálicas con borde dorado (como la referencia)."""
        bw = self.bar_w * 2
        body = skia.Paint(Color4f=rgb((0.62, 0.63, 0.67)), AntiAlias=True, StrokeWidth=bw, StrokeCap=skia.Paint.kButt_Cap)
        hi = skia.Paint(Color4f=rgb((0.9, 0.9, 0.93)), AntiAlias=True, StrokeWidth=bw * 0.35, StrokeCap=skia.Paint.kButt_Cap)
        gold = skia.Paint(Color4f=rgb((0.95, 0.78, 0.25)), AntiAlias=True, StrokeWidth=2.5, StrokeCap=skia.Paint.kButt_Cap)
        for b, u, t in self.bars:
            x, y = self.cx + u[0] * self.d, self.cy + u[1] * self.d
            x0, y0 = x - t[0] * self.half, y - t[1] * self.half
            x1, y1 = x + t[0] * self.half, y + t[1] * self.half
            c.drawLine(x0, y0, x1, y1, body)
            o = -bw * 0.18
            c.drawLine(x0 + u[0] * o, y0 + u[1] * o, x1 + u[0] * o, y1 + u[1] * o, hi)
            gi = -bw * 0.5 + 1.5      # borde dorado del lado de adentro
            c.drawLine(x0 + u[0] * gi, y0 + u[1] * gi, x1 + u[0] * gi, y1 + u[1] * gi, gold)

    def on_break(self):
        for b, _, _ in self.bars:
            for sh in b.shapes:
                sh.filter = pymunk.ShapeFilter(mask=0)
