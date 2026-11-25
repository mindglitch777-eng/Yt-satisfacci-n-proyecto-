"""MARTILLO GIGANTE — lógica de la referencia neonbounce_hammer_fill.mp4 ("el martillo gigante aplastando, ¡mirá cómo
las pelotas se multiplican!"). Ver reference/formats/slam/SPEC.md.

- Hay gravedad: las bolas caen y se juntan en el piso.
- Un martillo-péndulo cuelga del centro (cabeza = bloque grande cerca del piso) y oscila de lado a lado.
- Dos yunques fijos, abajo a la izquierda y a la derecha. En cada pasada el martillo barre el piso hacia un yunque.
- Al golpear, lo que quedó apretado entre el martillo y el yunque se aplasta y sale ×N en CHORRO hacia arriba
  por la rendija, de un color nuevo; después cae y se apila. La pila sube hasta llenar el círculo → se rompe.
"""
import math
import numpy as np
import pymunk
import skia

from formats.arena import Arena, TAU
from engine.gfx import rgb

TXT = {
    "en": {"t1": "THE GIANT HAMMER", "t2": "MULTIPLIES EVERY BALL", "balls": "BALLS", "full": "FULL!",
           "almost": "IT GETS THIS FULL...", "broke": "IT BROKE!",
           "cta1": "WHICH MACHINE IS NEXT?", "cta2": "SUBSCRIBE FOR PART {n}"},
    "es": {"t1": "EL MARTILLO GIGANTE", "t2": "MULTIPLICA CADA BOLA", "balls": "BOLAS", "full": "¡LLENO!",
           "almost": "SE LLENA ASÍ...", "broke": "¡SE ROMPIÓ!",
           "cta1": "¿QUÉ MÁQUINA SIGUE?", "cta2": "SUSCRIBITE PARA LA PARTE {n}"},
}


def sector_pts(a0, a1, r_in, r_out, n=8):
    """polígono convexo ≈ sector anular (cuerda adentro, arco afuera)."""
    pts = [(r_in * math.cos(a0), r_in * math.sin(a0))]
    for i in range(n + 1):
        a = a0 + (a1 - a0) * i / n
        pts.append((r_out * math.cos(a), r_out * math.sin(a)))
    pts.append((r_in * math.cos(a1), r_in * math.sin(a1)))
    return pts


class Slam(Arena):
    TXT = TXT

    def setup_machine(self):
        g = self.g
        R = self.R
        self.r_in, self.r_out = g.get("block_in", 0.5) * R, R - 4
        # yunques fijos (ángulos con y hacia abajo: 90° = abajo)
        self.anvL = (math.radians(g.get("anvL0", 140)), math.radians(g.get("anvL1", 188)))
        self.anvR = (math.radians(g.get("anvR0", -8)), math.radians(g.get("anvR1", 40)))
        for a0, a1 in (self.anvL, self.anvR):
            pts = [(self.cx + x, self.cy + y) for x, y in sector_pts(a0, a1, self.r_in, self.r_out + 8)]
            s = pymunk.Poly(self.space.static_body, pts)
            s.elasticity, s.friction = 0.2, 0.6
            self.space.add(s)
            self.anvil_shapes = getattr(self, "anvil_shapes", []) + [s]
        # martillo: varilla + cabeza (sector de ancho w) colgando del centro
        self.hw = math.radians(g.get("head_w", 46))
        self.hammer = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
        self.hammer.position = (self.cx, self.cy)
        head = pymunk.Poly(self.hammer, sector_pts(-self.hw / 2, self.hw / 2, self.r_in, self.r_out - 3))
        rod = pymunk.Segment(self.hammer, (18, 0), (self.r_in, 0), 7)
        for s in (head, rod):
            s.elasticity, s.friction = 0.2, 0.6
        self.space.add(self.hammer, head, rod)
        # extremos del péndulo: la cabeza toca justo cada yunque
        self.ang_R = self.anvR[1] + self.hw / 2      # golpe contra el yunque derecho
        self.ang_L = self.anvL[0] - self.hw / 2      # golpe contra el izquierdo
        self.mid = (self.ang_R + self.ang_L) / 2
        self.amp = (self.ang_L - self.ang_R) / 2
        self.period = g.get("period", 3.0)
        import json, os
        sp = json.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                         "reference/formats/slam/spec.json")))
        self.curve = np.array(sp["curva_conteo"], float)
        self.capacity = int(sp["bolas"]["capacidad_full"])
        self.phase0 = -math.pi / 2                   # arranca del lado derecho
        self.ang = self._angle(0.0)
        self.hammer.angle = self.ang
        self.mult = g.get("mult", 4)
        self.crushed = {"L": 0, "R": 0}
        self.hit_armed = {"L": True, "R": True}
        self.hits = 0
        # dos bolas en el piso, como la referencia ("2 BALLS")
        for x in (-0.12, 0.05):
            self.add_ball(self.cx + x * R, self.cy + 0.8 * R, 0, 0, 0)

    def _angle(self, t):
        # péndulo suave (seno) que se queda un instante apretado contra cada yunque
        s = math.sin(TAU * t / self.period + self.phase0)
        s = max(-1.0, min(1.0, 1.08 * s))
        return self.mid + self.amp * s

    # ---------- movimiento + aplastado ----------
    def machine_step(self):
        new = self._angle(self.t + self.dt)
        self.hammer.angular_velocity = (new - self.ang) / self.dt
        self._prev_ang = self.ang
        self.ang = new
        self._squeeze()
        if self.frame % 2 == 0:
            sp = abs(self.hammer.angular_velocity)
            self.audio.rumble(self.t, min(1.0, 0.08 + sp * 0.35 * (0.3 + 0.7 * min(1, len(self.bodies) / 500))))

    def step(self):
        super().step()
        self.hammer.angle = self.ang

    def _gap(self, side):
        """ángulo libre entre la cabeza del martillo y el yunque de ese lado."""
        if side == "R":
            return (self.ang - self.hw / 2) - self.anvR[1]
        return self.anvL[0] - (self.ang + self.hw / 2)

    def _squeeze(self):
        for side in ("L", "R"):
            gap = self._gap(side)
            if gap > math.radians(25):
                self.hit_armed[side] = True
                continue
            if not self.bodies:
                continue
            P = self.positions()
            rel = P - np.array([self.cx, self.cy])
            rad = np.hypot(rel[:, 0], rel[:, 1])
            phi = np.arctan2(rel[:, 1], rel[:, 0])
            if side == "R":
                lo, hi = self.anvR[1], self.ang - self.hw / 2
            else:
                lo, hi = self.ang + self.hw / 2, self.anvL[0]
            r = self.rad[0]
            pad = r / np.maximum(rad, 1)
            inz = ((phi > lo - pad - math.radians(4)) & (phi < hi + pad + math.radians(4)) & (rad > self.r_in - 6 * r))
            idx = np.nonzero(inz)[0]
            # lo que ya no entra en la rendija se aplasta (cuenta para el golpe)
            width = max(0.0, hi - lo)
            area = 0.5 * width * (self.r_out ** 2 - self.r_in ** 2)
            fits = int(area * 0.8 / (math.pi * r * r))
            # la rendija tiene capacidad fija: lo que no cabe ahí no se aplasta (se escurre por arriba)
            gap_cap = max(1, int(0.5 * math.radians(self.g.get("gap_deg", 6.0)) * (self.r_out ** 2 - self.r_in ** 2)
                                 * 0.8 / (math.pi * r * r)))
            room = gap_cap - self.crushed[side]
            if gap <= math.radians(2.0) and room > 0 and len(idx):
                fits = 0                                     # el golpe: todo lo que quedó en la rendija se aplasta
            if len(idx) > fits and room > 0:
                gone = idx[np.argsort(-rad[idx])][: min(len(idx) - fits, room)] if fits else idx[:room]
                self.crush_fx(gone, P)
                self.crushed[side] += len(gone)
                self.remove_balls(gone)
            if gap <= math.radians(0.6) and self.hit_armed[side]:
                self.hit_armed[side] = False
                self._hit(side)

    def _hit(self, side):
        """golpe contra el yunque: lo aplastado sale ×N en chorro hacia arriba por la rendija."""
        self.hits += 1
        k = self.crushed[side]
        self.crushed[side] = 0
        a = self.anvR[1] if side == "R" else self.anvL[0]
        hx, hy = self.cx + (self.r_in + self.r_out) / 2 * math.cos(a), self.cy + (self.r_in + self.r_out) / 2 * math.sin(a)
        ten = self.tension()
        pan = self.pan(hx)
        self.flashes.append([hx, hy, 0.0])
        self.cam.kick(0.15 + 0.3 * ten)
        self.audio.hit(self.t, min(1.0, 0.55 + k / 150), "punch", pan, ten)
        self.audio.event(self.t, "slam", 0.8)
        if k == 0:
            return
        want = float(np.interp(self.t + self.period / 2, self.curve[:, 0], self.curve[:, 1]))
        # lo aplastado ya salió de la física: renace ×2 (k·2), o menos si el contador va adelantado (nunca menos de k)
        n_new = max(k, min(k * self.mult, int(want) - len(self.bodies)))
        n_new = min(n_new, self.capacity - len(self.bodies))
        self.cur = (self.cur + 1) % len(self.colors)
        r = self.rad[0] if self.rad else self.r_big      # se achican de a poco (formats/sizing.py)
        # chorro: sale por la rendija (entre martillo y yunque) hacia el centro y para arriba
        ox, oy = self.cx + self.r_in * 0.92 * math.cos(a), self.cy + self.r_in * 0.92 * math.sin(a)
        jx, jy = self.cx - ox, (self.cy - 0.35 * self.R) - oy
        jl = math.hypot(jx, jy) or 1
        jx, jy = jx / jl, jy / jl
        for i in range(n_new):
            sp = self.rng.uniform(700, 1300)
            sx = self.rng.uniform(-0.22, 0.22)
            vx = (jx * math.cos(sx) - jy * math.sin(sx)) * sp
            vy = (jy * math.cos(sx) + jx * math.sin(sx)) * sp
            back = self.rng.uniform(0, 3.5) * r * (1 + i // 40)
            self.add_ball(ox - jx * back + self.rng.uniform(-r, r), oy - jy * back + self.rng.uniform(-r, r), vx, vy, self.rng.randrange(len(self.colors)))   # confeti
        self.particles.burst(hx, hy, self.colors[self.cur], n=20, speed=650, size=5)
        self.audio.hit(self.t + 0.003, min(1.0, 0.5 + k / 150), "squish", pan, ten)
        for i in range(int(min(9, 2 + 1.6 * math.log2(1 + n_new)))):
            self.audio.event(self.t + 0.05 + i * 0.03, "pop", 0.9 + 0.5 * ten + 0.07 * i)
        if n_new > k:
            self.pops.append([ox + jx * 120, oy + jy * 120, f"×{self.mult}" if n_new == k * self.mult and k < 25 else f"+{n_new - k}", 0.0])

    # ---------- dibujo ----------
    def draw_machine(self, c):
        fill = skia.Paint(Color4f=rgb((0.66, 0.67, 0.71)), AntiAlias=True)
        edge = skia.Paint(Color4f=rgb((0.86, 0.86, 0.9)), AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=3)
        line = skia.Paint(Color4f=rgb((0.35, 0.35, 0.4)), AntiAlias=True, StrokeWidth=3, StrokeCap=skia.Paint.kRound_Cap)

        def block(a0, a1, r_out, rot=0.0):
            path = skia.Path()
            pts = sector_pts(a0 + rot, a1 + rot, self.r_in, r_out, 12)
            path.moveTo(self.cx + pts[0][0], self.cy + pts[0][1])
            for x, y in pts[1:]:
                path.lineTo(self.cx + x, self.cy + y)
            path.close()
            c.drawPath(path, fill)
            c.drawPath(path, edge)
            am = (a0 + a1) / 2 + rot
            for k in (0.62, 0.72):     # rayitas como en la referencia
                rr = self.r_in + (r_out - self.r_in) * k
                tx, ty = -math.sin(am), math.cos(am)
                x, y = self.cx + rr * math.cos(am), self.cy + rr * math.sin(am)
                c.drawLine(x - tx * 28, y - ty * 28, x + tx * 28, y + ty * 28, line)

        for a0, a1 in (self.anvL, self.anvR):
            block(a0, a1, self.r_out)
        # varilla + cabeza del martillo
        rod = skia.Paint(Color4f=rgb((0.62, 0.63, 0.67)), AntiAlias=True, StrokeWidth=14, StrokeCap=skia.Paint.kRound_Cap)
        c.drawLine(self.cx, self.cy, self.cx + self.r_in * math.cos(self.ang), self.cy + self.r_in * math.sin(self.ang), rod)
        block(-self.hw / 2, self.hw / 2, self.r_out - 3, self.ang)
        c.drawCircle(self.cx, self.cy, 18, skia.Paint(Color4f=rgb((0.85, 0.86, 0.9)), AntiAlias=True))
        c.drawCircle(self.cx, self.cy, 18, skia.Paint(Color4f=rgb((0.3, 0.3, 0.35)), AntiAlias=True,
                                                      Style=skia.Paint.kStroke_Style, StrokeWidth=3))

    def on_break(self):
        self.space.remove(*self.anvil_shapes)
        for s in self.hammer.shapes:
            s.filter = pymunk.ShapeFilter(mask=0)
