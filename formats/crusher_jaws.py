"""CRUSHER JAWS — referencia nexusboxlab_crusher_9.6M.mp4 (9.6M, el más visto del nicho que multiplica).
Ver reference/formats/MEDIDAS_TOP5.md y reference/formats/crusher_jaws/target.json (detector --machine jaws).

Medido en la referencia (0-12 s, cuadro a cuadro a 10 fps):
- Dos pinzas montadas en engranajes sobre el aro, a las 9 y a las 3. Se ALTERNAN: entra una, aplasta, se retira, entra la otra.
- Una entrada cada 2.1 s; la pinza entra hasta 0.30R del centro en 0.6 s, queda adentro 1.8 s; nunca las dos a la vez.
- Cada pinza: dos brazos de 2 tramos. Reposo = ">" pegado al aro. Entra con la boca abierta ("⊏" mirando al centro),
  cierra la boca formando un rombo que encierra bolas, colapsa (aplastón) y se retira.
- Sin gravedad: las bolas flotan donde quedaron. Lo aplastado renace multiplicado (1 → 4 → 13 …) en un racimo
  compacto de color nuevo que se expande como una mancha.
- Final (regla del canal): FULL → grietas → el aro se rompe.
"""
import math
import numpy as np
import pymunk
import skia

from formats.arena import Arena, TAU
from engine.gfx import rgb

TXT = {
    "en": {"t1": "EVERY CRUSHED BALL", "t2": "BECOMES 4", "balls": "BALLS", "full": "FULL!",
           "almost": "IT GETS THIS FULL...", "broke": "IT BROKE!",
           "cta1": "WHICH MACHINE IS NEXT?", "cta2": "SUBSCRIBE FOR PART {n}"},
    "es": {"t1": "CADA BOLA APLASTADA", "t2": "SE VUELVE 4", "balls": "BOLAS", "full": "¡LLENO!",
           "almost": "SE LLENA ASÍ...", "broke": "¡SE ROMPIÓ!",
           "cta1": "¿QUÉ MÁQUINA SIGUE?", "cta2": "SUSCRIBITE PARA LA PARTE {n}"},
}

# poses de UN brazo (el de arriba; el de abajo es espejo), en unidades de R, coords locales:
# x = hacia el centro desde el engranaje, y = perpendicular. (codo, punta)
POSE = {
    "rest":   ((0.10, 0.44), (0.02, 0.74)),   # ">" pegado al aro
    "mouth":  ((0.25, 0.30), (0.67, 0.23)),   # boca abierta mirando al centro
    "deep":   ((0.27, 0.29), (0.72, 0.21)),   # empuja un poco más antes de cerrar (máximo alcance, un solo pico)
    "closed": ((0.30, 0.20), (0.52, 0.015)),  # rombo colapsado: puntas juntas (aplastón)
}
# guion de UNA entrada (s): ver measure jaw_in_s=0.6, jaw_active_s=1.8, jaw_cycle_s=2.1
KEYS = [(0.0, "rest"), (0.75, "mouth"), (1.0, "deep"), (1.3, "closed"), (1.55, "closed"), (2.05, "rest")]


def smooth(u):
    u = min(1.0, max(0.0, u))
    return u * u * (3 - 2 * u)


def lerp(a, b, k):
    return (a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k)


def pose_at(t):
    """(codo, punta) del brazo superior en el instante t de la entrada (0..cycle)."""
    for (t0, p0), (t1, p1) in zip(KEYS, KEYS[1:]):
        if t <= t1:
            k = smooth((t - t0) / (t1 - t0)) if t1 > t0 else 1.0
            e0, q0 = POSE[p0]
            e1, q1 = POSE[p1]
            return lerp(e0, e1, k), lerp(q0, q1, k)
    return POSE["rest"]


class CrusherJaws(Arena):
    TXT = TXT

    def setup_machine(self):
        g = self.g
        self.cycle = g.get("jaw_cycle", 2.1)
        self.mult = g.get("mult", 4)
        self.arm_w = 9
        self.sides = [-1, 1]                      # -1 = izquierda (9 h), +1 = derecha (3 h)
        self.jaws = []
        for s in self.sides:
            b = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
            b.position = (self.cx + s * self.R, self.cy)
            self.space.add(b)
            self.jaws.append({"side": s, "body": b, "shapes": [], "pose": POSE["rest"]})
        self.active = 0                           # arranca la izquierda
        self.t_jaw = -g.get("first_delay", 0.25)
        self.crushed_now = False
        self.gen = 0
        self._set_shapes()
        # una bola roja grande flotando cerca del centro, en el camino de la primera pinza
        self.add_ball(self.cx - 0.42 * self.R, self.cy + 0.03 * self.R, 12, -6, 0)

    # ---------- geometría ----------
    def _world(self, side, p):
        """local (x hacia el centro, y) en R → píxeles."""
        return (self.cx + side * self.R * (1 - p[0]), self.cy + self.R * p[1])

    def _arm_pts(self, jaw):
        (ex, ey), (tx, ty) = jaw["pose"]
        s = jaw["side"]
        g0 = self._world(s, (0.0, 0.0))
        up = [g0, self._world(s, (ex, ey)), self._world(s, (tx, ty))]
        lo = [g0, self._world(s, (ex, -ey)), self._world(s, (tx, -ty))]
        return up, lo

    def _set_shapes(self):
        for jaw in self.jaws:
            if jaw["shapes"]:
                self.space.remove(*jaw["shapes"])
            b = jaw["body"]
            bx, by = b.position
            segs = []
            for arm in self._arm_pts(jaw):
                for a, c in zip(arm, arm[1:]):
                    sg = pymunk.Segment(b, (a[0] - bx, a[1] - by), (c[0] - bx, c[1] - by), self.arm_w)
                    sg.elasticity, sg.friction = 0.3, 0.4
                    if getattr(self, "broken_at", None) is not None:
                        sg.filter = pymunk.ShapeFilter(mask=0)
                    segs.append(sg)
            self.space.add(*segs)
            jaw["shapes"] = segs

    # ---------- ciclo ----------
    def machine_step(self):
        self.t_jaw += self.dt
        if self.t_jaw >= self.cycle:
            self.t_jaw -= self.cycle
            self.active = 1 - self.active
            self.crushed_now = False
        for i, jaw in enumerate(self.jaws):
            jaw["pose"] = pose_at(self.t_jaw) if (i == self.active and self.t_jaw >= 0) else POSE["rest"]
        self._push_out()
        self._set_shapes()
        if not self.crushed_now and self.t_jaw >= KEYS[3][0]:   # aplastón cuando la boca colapsa
            self.crushed_now = True
            self._crush(self.jaws[self.active])
        if self.frame % 2 == 0:
            moving = 0.0 < self.t_jaw < 2.05
            self.audio.rumble(self.t, 0.25 if moving else 0.06)

    def _push_out(self):
        """anti-tunneling: las bolas que quedaron adentro del hueso de un brazo salen hacia el lado libre."""
        if not self.bodies:
            return
        P = self.positions()
        r = self.rad[0]
        for jaw in self.jaws:
            for arm in self._arm_pts(jaw):
                for a, c in zip(arm, arm[1:]):
                    ax, ay = a; vx, vy = c[0] - ax, c[1] - ay
                    L2 = vx * vx + vy * vy or 1.0
                    u = np.clip(((P[:, 0] - ax) * vx + (P[:, 1] - ay) * vy) / L2, 0, 1)
                    qx, qy = ax + u * vx, ay + u * vy
                    dx, dy = P[:, 0] - qx, P[:, 1] - qy
                    dd = np.hypot(dx, dy)
                    hit = np.nonzero(dd < self.arm_w + r)[0]
                    for i in hit:
                        k = (self.arm_w + r + 0.5) / max(dd[i], 1e-3)
                        if dd[i] < 1e-3:
                            dx[i], dy[i], k = -vy, vx, (self.arm_w + r + 0.5) / math.sqrt(L2)
                        b = self.bodies[i]
                        b.position = (qx[i] + dx[i] * k, qy[i] + dy[i] * k)
                        P[i] = b.position

    def _inside_jaw(self, P, jaw):
        """bolas dentro del rombo formado por los dos brazos (polígono engranaje-codo-punta-punta-codo)."""
        up, lo = self._arm_pts(jaw)
        poly = [up[0], up[1], up[2], lo[2], lo[1]]
        path = skia.Path()
        path.moveTo(*poly[0])
        for q in poly[1:]:
            path.lineTo(*q)
        path.close()
        return np.array([path.contains(float(x), float(y)) for x, y in P], bool)

    def _crush(self, jaw):
        """aplastón: lo encerrado se pulveriza y renace ×mult en un racimo compacto de color nuevo."""
        up, lo = self._arm_pts(jaw)
        # la región que encierra la boca justo antes de colapsar
        mouth = dict(jaw)
        mouth["pose"] = POSE["deep"]
        hx = (up[2][0] + lo[2][0]) / 2
        hy = (up[2][1] + lo[2][1]) / 2
        ten = self.tension()
        pan = self.pan(hx)
        k = 0
        if self.bodies:
            P = self.positions()
            ins = np.nonzero(self._inside_jaw(P, mouth))[0]
            cap = self.g.get("jaw_cap", 10 ** 9)
            if len(ins) > cap:
                ins = ins[np.argsort(np.abs(P[ins, 1] - self.cy))][:cap]
            k = len(ins)
            if k:
                cxm, cym = P[ins].mean(axis=0)
                self.crush_fx(ins, P)
                self.remove_balls(ins)
        self.cam.kick(0.15 + 0.3 * ten)
        self.audio.hit(self.t, min(1.0, 0.5 + k / 120), "punch", pan, ten)
        self.audio.event(self.t, "slam", 0.6)
        if k == 0:
            return
        n_new = min(k * self.mult, self.capacity - len(self.bodies))
        self.gen += 1
        self.cur = self.gen % len(self.colors)
        self._spawn_cluster(cxm, cym, n_new)
        self.flashes.append([cxm, cym, 0.0, self.colors[self.cur]])
        self.audio.hit(self.t + 0.003, min(1.0, 0.5 + k / 120), "squish", pan, ten)
        for i in range(int(min(9, 2 + 1.6 * math.log2(1 + n_new)))):
            self.audio.event(self.t + 0.05 + i * 0.03, "pop", 0.9 + 0.5 * ten + 0.07 * i)
        self.pops.append([cxm, cym - 70, f"×{self.mult}" if k < 25 else f"+{n_new}", 0.0, self.colors[self.cur]])
        self.particles.burst(cxm, cym, self.colors[self.cur], n=22, speed=600, size=5)

    def _spawn_cluster(self, x0, y0, n):
        """racimo compacto: ocupa los huecos libres más cercanos al punto del aplastón (se ve como una mancha que crece)."""
        if n <= 0:
            return
        r = self.rad[0] if self.rad else self.r_big
        d = 2 * r * 1.02
        occ = set()
        if self.bodies:
            for x, y in self.positions():
                occ.add((int(x // d), int(y // d)))
        cand = []
        span = int(self.R / d) + 2
        cx0, cy0 = int(x0 // d), int(y0 // d)
        for i in range(-span, span + 1):
            for j in range(-span, span + 1):
                gx, gy = cx0 + i, cy0 + j
                x, y = (gx + 0.5) * d, (gy + 0.5) * d
                if (gx, gy) in occ or math.hypot(x - self.cx, y - self.cy) > self.R - r - 1:
                    continue
                cand.append((math.hypot(x - x0, y - y0), x, y))
        cand.sort()
        # el racimo sale despedido hacia la OTRA pinza (en la referencia el racimo cruza el centro y queda
        # flotando donde entra la siguiente) y a la vez se expande
        nxt = self.jaws[1 - self.active]["side"]
        tx, ty = self.cx + nxt * self.g.get("drift_to", 0.42) * self.R, self.cy + (-self.g.get("drift_amp", 0.05) if (self.gen % self.g.get("drift_n", 7)) < self.g.get("drift_up_k", 4) else self.g.get("drift_amp", 0.05)) * self.R
        # cada racimo queda a otra altura: 4 de cada 7 un poco arriba (sin gravedad la masa queda centrada; ref 62% arriba)
        damp = -math.log(max(1e-3, self.space.damping))
        vcx = (tx - x0) * damp
        vcy = (ty - y0) * damp
        for dist, x, y in cand[:n]:
            a = math.atan2(y - y0, x - x0)
            sp = 40 + 0.8 * dist
            self.add_ball(x + self.rng.uniform(-0.5, 0.5), y + self.rng.uniform(-0.5, 0.5),
                          vcx + sp * math.cos(a), vcy + sp * math.sin(a), self.cur)

    # ---------- dibujo ----------
    def draw_machine(self, c):
        arm = skia.Paint(Color4f=rgb((0.60, 0.61, 0.65)), AntiAlias=True, StrokeWidth=2 * self.arm_w,
                         StrokeCap=skia.Paint.kRound_Cap, StrokeJoin=skia.Paint.kRound_Join, Style=skia.Paint.kStroke_Style)
        hi = skia.Paint(Color4f=rgb((0.78, 0.78, 0.82)), AntiAlias=True, StrokeWidth=self.arm_w * 0.6,
                        StrokeCap=skia.Paint.kRound_Cap, Style=skia.Paint.kStroke_Style)
        for jaw in self.jaws:
            for pts in self._arm_pts(jaw):
                path = skia.Path()
                path.moveTo(*pts[0])
                for q in pts[1:]:
                    path.lineTo(*q)
                c.drawPath(path, arm)
                c.drawPath(path, hi)
            self._gear(c, *self._world(jaw["side"], (0.0, 0.0)))

    def _gear(self, c, x, y, r=26, teeth=12):
        rot = self.t * 2.0
        path = skia.Path()
        for i in range(teeth * 2):
            a = rot + math.pi * i / teeth
            rr = r if i % 2 == 0 else r * 0.78
            px, py = x + rr * math.cos(a), y + rr * math.sin(a)
            path.moveTo(px, py) if i == 0 else path.lineTo(px, py)
        path.close()
        c.drawPath(path, skia.Paint(Color4f=rgb((0.72, 0.73, 0.77)), AntiAlias=True))
        c.drawCircle(x, y, r * 0.35, skia.Paint(Color4f=rgb((0.35, 0.35, 0.4)), AntiAlias=True))

    def on_break(self):
        for jaw in self.jaws:
            for sh in jaw["shapes"]:
                sh.filter = pymunk.ShapeFilter(mask=0)
