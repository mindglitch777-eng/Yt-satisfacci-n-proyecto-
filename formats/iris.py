"""IRIS — 7 cuchillas curvas con pivote en el aro que cierran juntas hasta el centro (diafragma) y se abren hasta
pegarse al aro. Lo que queda en el centro al cerrarse se aplasta y renace ×4 en un racimo de color nuevo.
Datos: reference/formats/iris/spec.json (Splitworks 4.1M)."""
import json, math, os
import numpy as np
import pymunk
import skia

from formats.arena import Arena, TAU
from engine.gfx import rgb

TXT = {
    "en": {"t1": "THE IRIS CRUSHES", "t2": "EVERY BALL INTO 4", "balls": "BALLS", "full": "FULL!",
           "almost": "IT GETS THIS FULL...", "broke": "IT BROKE!",
           "cta1": "WHICH MACHINE IS NEXT?", "cta2": "SUBSCRIBE FOR PART {n}"},
    "es": {"t1": "EL IRIS APLASTA", "t2": "CADA BOLA EN 4", "balls": "BOLAS", "full": "¡LLENO!",
           "almost": "SE LLENA ASÍ...", "broke": "¡SE ROMPIÓ!",
           "cta1": "¿QUÉ MÁQUINA SIGUE?", "cta2": "SUSCRIBITE PARA LA PARTE {n}"},
}
N_BLADES = 7


def smooth(u):
    u = min(1.0, max(0.0, u))
    return u * u * (3 - 2 * u)


class Iris(Arena):
    TXT = TXT

    def setup_machine(self):
        g = self.g
        here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        sp = json.load(open(os.path.join(here, "reference/formats/iris/spec.json")))
        self.curve = np.array(sp["curva_conteo"], float)
        self.capacity = int(sp["bolas"]["capacidad_full"])
        self.mult = 4
        mv = sp["maquina"]["movimiento"]
        self.T = dict(close=mv["cierre_s"], hold=0.12, open=mv["apertura_s"])
        self.T["wait"] = mv["periodo_s"] - sum(self.T.values())
        self.blade_w = 7
        # cuchilla en coords locales (origen = pivote, eje x apuntando al centro): arco que curva a la izquierda
        L, rc = 1.0 * self.R, 1.0 * self.R
        n = 10
        self.local = [(rc * math.sin(L / rc * i / n), rc * (1 - math.cos(L / rc * i / n))) for i in range(n + 1)]
        # ángulos de rotación: cerrado = la punta llega al centro; abierto = la cuchilla pegada al aro
        def pts(alpha):
            ca, sa = math.cos(alpha), math.sin(alpha)
            return [(x * ca - y * sa, x * sa + y * ca) for x, y in self.local]
        best_c, best_o = None, None
        for a in np.linspace(-math.pi, math.pi, 721):
            P = pts(a)
            tip = math.hypot(P[-1][0] - self.R, P[-1][1])                 # pivote en (R,0) relativo al centro (-R,0)
            dmin = min(math.hypot(x - self.R, y) for x, y in P[1:])
            if best_c is None or tip < best_c[0]:
                best_c = (tip, a)
            if dmin > self.R * 0.86 and (best_o is None or abs(a - best_c[1]) < abs(best_o - best_c[1])):
                best_o = a
        self.a_close, self.a_open = best_c[1], best_o if best_o is not None else best_c[1] + 1.4
        self.blades = []
        for k in range(N_BLADES):
            th = TAU * k / N_BLADES - math.pi / 2
            px, py = self.cx + self.R * math.cos(th), self.cy + self.R * math.sin(th)
            b = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
            b.position = (px, py)
            segs = []
            for (x0, y0), (x1, y1) in zip(self.local, self.local[1:]):
                s = pymunk.Segment(b, (x0, y0), (x1, y1), self.blade_w)
                s.elasticity, s.friction = 0.2, 0.3
                segs.append(s)
            self.space.add(b, *segs)
            self.blades.append((b, th, segs))
        self.phase, self.ph_t = "close", 0.2       # frame 1: ya cerrando
        self.alpha = self._alpha_at()
        self._place(self.alpha, 0.0)
        self.add_ball(self.cx + 0.25 * self.R, self.cy - 0.15 * self.R, -40, 25, 0)

    def _alpha_at(self):
        u = self.ph_t
        if self.phase == "close":
            k = smooth(u / self.T["close"])
        elif self.phase == "hold":
            k = 1.0
        elif self.phase == "open":
            k = 1 - smooth(u / self.T["open"])
        else:
            k = 0.0
        return self.a_open + (self.a_close - self.a_open) * k

    def _place(self, alpha, w):
        for b, th, _ in self.blades:
            # el eje x local apunta al centro: ángulo base = th + π
            b.angle = th + math.pi + alpha
            b.angular_velocity = w

    def machine_step(self):
        self.ph_t += self.dt
        T = self.T
        nxt = {"close": "hold", "hold": "open", "open": "wait", "wait": "close"}
        if self.ph_t >= T[self.phase]:
            if self.phase == "close":
                self._crush()
            self.phase, self.ph_t = nxt[self.phase], 0.0
        a = self._alpha_at()
        self._place(self.alpha, (a - self.alpha) / self.dt)
        self.alpha = a
        if self.frame % 2 == 0:
            moving = self.phase in ("close", "open")
            self.audio.rumble(self.t, 0.2 if moving else 0.06)

    def step(self):
        super().step()
        for b, th, _ in self.blades:
            b.angle = th + math.pi + self.alpha

    def _crush(self):
        """iris cerrado: lo que quedó en el centro se aplasta y renace ×4 (Pacer por la curva)."""
        P = self.positions() if self.bodies else np.zeros((0, 2))
        ins = []
        if len(P):
            # Pacer: el radio de captura crece hasta juntar lo necesario para seguir la curva (×4 de lo atrapado)
            dist = np.hypot(P[:, 0] - self.cx, P[:, 1] - self.cy)
            need = (float(np.interp(self.t + 3.7, self.curve[:, 0], self.curve[:, 1])) - len(P)) / self.mult
            order = np.argsort(dist)
            base = int(np.sum(dist < self.g.get("catch_R", 0.3) * self.R))
            take = max(base, min(int(math.ceil(need)), int(np.sum(dist < 0.75 * self.R))))
            ins = order[:take]
        k = len(ins)
        self.flashes.append([self.cx, self.cy, 0.0])
        self.cam.kick(0.15 + 0.3 * self.tension())
        self.audio.hit(self.t, min(1.0, 0.5 + k / 150), "punch", 0.0, self.tension())
        self.audio.event(self.t, "slam", 0.6)
        if k == 0:
            return
        self.crush_fx(ins, P)
        self.remove_balls(ins)
        want = float(np.interp(self.t + 3.7, self.curve[:, 0], self.curve[:, 1]))
        full = len(self.bodies) + k >= 0.97 * self.capacity
        n_new = (self.capacity - len(self.bodies)) if full else max(k, min(k * self.mult, int(want) - len(self.bodies)))
        n_new = max(0, min(n_new, self.capacity - len(self.bodies)))
        self.cur = (self.cur + 1) % len(self.colors)
        self.spawn_cluster(n_new)
        ten = self.tension()
        self.audio.hit(self.t + 0.003, min(1.0, 0.5 + k / 150), "squish", 0.0, ten)
        for i in range(int(min(9, 2 + 1.6 * math.log2(1 + n_new)))):
            self.audio.event(self.t + 0.05 + i * 0.03, "pop", 0.9 + 0.5 * ten + 0.07 * i)
        if n_new > k:
            self.pops.append([self.cx, self.cy - 60, f"×{self.mult}" if n_new == k * self.mult and k < 20 else f"+{n_new - k}", 0.0])

    def spawn_cluster(self, n):
        """racimo en el centro (huecos libres más cercanos), que se abre despacio hacia afuera."""
        if n <= 0:
            return
        r = self.rad[0] if self.rad else self.r_big
        d = 2 * r * 1.02
        occ = set((int(x // d), int(y // d)) for x, y in self.positions()) if self.bodies else set()
        span = int(self.R / d) + 1
        cand = []
        c0x, c0y = int(self.cx // d), int(self.cy // d)
        for i in range(-span, span + 1):
            for j in range(-span, span + 1):
                gx, gy = c0x + i, c0y + j
                x, y = (gx + 0.5) * d, (gy + 0.5) * d
                dd = math.hypot(x - self.cx, y - self.cy)
                if (gx, gy) in occ or dd > self.R - r - 2:
                    continue
                cand.append((dd, x, y))
        cand.sort()
        for dd, x, y in cand[:n]:
            a = math.atan2(y - self.cy, x - self.cx)
            v = 60 + 0.8 * dd
            self.add_ball(x, y, v * math.cos(a), v * math.sin(a), self.cur)

    def update(self):
        super().update()
        if self.done_at is None and self.t >= self.g.get("t_end_full", 25.0):
            self.climax()

    def draw_machine(self, c):
        bezel = skia.Paint(Color4f=rgb((0.35, 0.37, 0.42)), AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=22)
        c.drawCircle(self.cx, self.cy, self.R + 14, bezel)
        fill = skia.Paint(Color4f=rgb((0.82, 0.83, 0.86)), AntiAlias=True, Style=skia.Paint.kStroke_Style,
                          StrokeWidth=2 * self.blade_w + 4, StrokeCap=skia.Paint.kRound_Cap, StrokeJoin=skia.Paint.kRound_Join)
        hi = skia.Paint(Color4f=rgb((0.97, 0.97, 0.99)), AntiAlias=True, Style=skia.Paint.kStroke_Style,
                        StrokeWidth=4, StrokeCap=skia.Paint.kRound_Cap)
        dot = skia.Paint(Color4f=rgb((0.25, 0.26, 0.3)), AntiAlias=True)
        for b, th, _ in self.blades:
            ang = th + math.pi + self.alpha
            ca, sa = math.cos(ang), math.sin(ang)
            path = skia.Path()
            for i, (x, y) in enumerate(self.local):
                X, Y = b.position.x + x * ca - y * sa, b.position.y + x * sa + y * ca
                path.moveTo(X, Y) if i == 0 else path.lineTo(X, Y)
            c.drawPath(path, fill)
            c.drawPath(path, hi)
            c.drawCircle(b.position.x, b.position.y, 7, dot)

    def on_break(self):
        for _, _, segs in self.blades:
            for s in segs:
                s.filter = pymunk.ShapeFilter(mask=0)
