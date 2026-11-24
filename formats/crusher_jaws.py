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

# Mecánica real (reference/formats/TOP5_LOGICA_REAL.md, hojas en reference/sheets/top5/):
# cada pinza = 2 brazos en L articulados en un engranaje SOBRE el aro. Los brazos giran SIEMPRE en el mismo sentido
# (el de arriba horario, el de abajo antihorario = tijera) y atraviesan el aro: afuera abiertos, adentro forman
# "⊐" → rombo → "T" (aplastón) y siguen de largo hacia afuera. Las dos pinzas a la vez, en contrafase.
ARM_A, ARM_B = 0.42, 0.52          # largo del brazo y del antebrazo (en R)
# perfil de giro de UNA vuelta (s, φ en grados), medido en la referencia (reach por lado, 0-12 s):
# entra (0.6 s hasta el máximo alcance), barre y aplasta en la "T" (φ=0), sale, y queda plegada afuera ~2.3 s.
PROFILE = [(0.0, 125), (0.7, 55), (1.3, 0), (1.6, -30), (2.05, -125), (4.2, -235)]
P_IN = 1.3 / 4.2                   # fase del aplastón


def _build_table(n=2000, smooth_s=0.18):
    T = PROFILE[-1][0]
    t = np.linspace(0, T, n, endpoint=False)
    ts, ph = zip(*PROFILE)
    w = np.gradient(np.interp(t, ts, ph), t)             # velocidad angular por tramos
    k = max(1, int(smooth_s / T * n))
    w = np.convolve(np.r_[w[-k:], w, w[:k]], np.ones(k) / k, "same")[k:-k]   # suave, sin tirones
    phi = PROFILE[0][1] + np.cumsum(w) * (T / n)
    phi = PROFILE[0][1] + (phi - PROFILE[0][1]) * (-360 / (phi[-1] - PROFILE[0][1]))  # vuelta exacta
    return phi


_PHI = _build_table()


def phi_at(p):
    """ángulo del brazo superior (0 = apuntando al centro, 90° = a lo largo del aro) para la fase p∈[0,1)."""
    p %= 1.0
    return math.radians(float(_PHI[int(p * len(_PHI)) % len(_PHI)]))


class CrusherJaws(Arena):
    TXT = TXT

    def setup_machine(self):
        g = self.g
        self.cycle = g.get("jaw_cycle", 4.2)        # una vuelta completa por pinza (aplastón cada 2.1 s, alternado)
        self.mult = g.get("mult", 4)
        self.arm_w = 9
        self.jaws = []
        for k, s in enumerate((-1, 1)):            # -1 izquierda (9 h), +1 derecha (3 h); contrafase 0.5
            self.jaws.append({"side": s, "off": 0.5 * k, "phi": 0.0, "prev": 0.0, "armed": False})
        self.p0 = g.get("p0", 0.02)                 # la izquierda arranca entrando
        self.gen = 0
        self._update_phis()
        self._update_phis()
        self._build_arms()
        self._drive_arms(final=True)
        self.add_ball(self.cx - 0.45 * self.R, self.cy + 0.04 * self.R, 10, -5, 0)

    # ---------- geometría ----------
    def _world(self, side, x, y):
        """local (x hacia el centro, y hacia arriba) en R → píxeles."""
        return (self.cx + side * self.R * (1 - x), self.cy - self.R * y)

    def _arm_pts(self, jaw, phi=None):
        f = jaw["phi"] if phi is None else phi
        s = jaw["side"]
        out = []
        for m in (1, -1):                          # brazo de arriba (m=1) y espejo de abajo
            ux, uy = math.cos(f), m * math.sin(f)
            fx, fy = math.sin(f), -m * math.cos(f)  # antebrazo: perpendicular, hacia el eje
            ex, ey = ARM_A * ux, ARM_A * uy
            out.append([self._world(s, 0, 0), self._world(s, ex, ey), self._world(s, ex + ARM_B * fx, ey + ARM_B * fy)])
        return out

    def _build_arms(self):
        """cada brazo en L = cuerpo rígido cinemático que gira sobre el engranaje (se crea una sola vez)."""
        A, B = ARM_A * self.R, ARM_B * self.R
        for jaw in self.jaws:
            s = jaw["side"]
            gx, gy = self.cx + s * self.R, self.cy
            jaw["arms"] = []
            for m in (1, -1):
                b = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
                b.position = (gx, gy)
                elbow = (-s * A, 0.0)
                segs = [pymunk.Segment(b, (0, 0), elbow, self.arm_w),
                        pymunk.Segment(b, elbow, (elbow[0], m * B), self.arm_w)]
                for sg in segs:
                    sg.elasticity, sg.friction = 0.3, 0.4
                self.space.add(b, *segs)
                jaw["arms"].append((b, s * m, segs))

    def _drive_arms(self, final=False):
        for jaw in self.jaws:
            for b, k, _ in jaw["arms"]:
                if final:
                    b.angle = k * jaw["phi"]
                    b.angular_velocity = 0
                else:
                    b.angle = k * jaw["prev"]
                    b.angular_velocity = k * (jaw["phi"] - jaw["prev"]) / self.dt

    def _update_phis(self):
        for jaw in self.jaws:
            p = (self.t / self.cycle + self.p0 + jaw["off"]) % 1.0
            jaw["prev"] = jaw["phi"]
            jaw["phi"] = phi_at(p)
            jaw["p"] = p

    # ---------- ciclo ----------
    def machine_step(self):
        self._update_phis()
        catch = math.radians(self.g.get("catch_deg", 88))
        for jaw in self.jaws:
            if jaw["armed"] and jaw.get("held") is None and jaw["prev"] > catch >= jaw["phi"]:
                self._grab(jaw)
            if 0.05 < jaw["p"] < P_IN - 0.03:
                jaw["armed"] = True
            if jaw["armed"] and jaw["phi"] <= 0:              # la "T": aplastón
                jaw["armed"] = False
                self._crush(jaw)
        self._drive_arms()
        self._push_out()
        if self.frame % 2 == 0:
            inside = any(jaw["p"] < 2.05 / 4.2 for jaw in self.jaws)
            self.audio.rumble(self.t, 0.22 if inside else 0.08)

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
        up, lo = self._arm_pts(jaw, math.radians(self.g.get("catch_deg", 88)))
        poly = [up[0], up[1], up[2], lo[2], lo[1]]
        path = skia.Path()
        path.moveTo(*poly[0])
        for q in poly[1:]:
            path.lineTo(*q)
        path.close()
        return np.array([path.contains(float(x), float(y)) for x, y in P], bool)

    def count(self):
        return len(self.bodies) + sum(len(j.get("held") or []) for j in self.jaws)

    def _grab(self, jaw):
        """el rombo se cerró: lo que quedó adentro queda atrapado y se aprieta con la pinza (no se escapa)."""
        jaw["held"] = []
        if not self.bodies:
            return
        P = self.positions()
        ins = np.nonzero(self._inside_jaw(P, jaw))[0]
        cap = self.g.get("jaw_cap", 10 ** 9)
        if len(ins) > cap:
            ins = ins[np.argsort(np.abs(P[ins, 1] - self.cy))][:cap]
        jaw["held"] = [(float(P[i, 0]), float(P[i, 1]), self.col[i]) for i in ins]
        self.remove_balls(ins)

    def _held_pos(self, jaw):
        """posición dibujada de las atrapadas: se juntan hacia el punto de aplastón a medida que la pinza cierra."""
        up, lo = self._arm_pts(jaw)
        hx, hy = (up[1][0] + lo[1][0] + up[2][0] + lo[2][0]) / 4, (up[1][1] + lo[1][1] + up[2][1] + lo[2][1]) / 4
        catch = math.radians(self.g.get("catch_deg", 88))
        k = min(1.0, max(0.0, 1 - jaw["phi"] / catch)) ** 1.5
        return [(x + (hx - x) * k * 0.85, y + (hy - y) * k * 0.85, c) for x, y, c in jaw["held"]], (hx, hy)

    def _lift(self):
        """altura a la que sale el racimo: corrige hacia arriba si la masa está baja y viceversa,
        para que la masa quede apenas por encima del centro (ref: 62% del tiempo arriba) en cualquier semilla."""
        if len(self.bodies) < 300:
            return 0.0                                   # al principio el racimo va derecho a la otra pinza
        my = (float(np.mean([b.position.y for b in self.bodies])) - self.cy) / self.R
        return float(np.clip(self.g.get("lift_base", 0.1) + self.g.get("lift_gain", 4.0) * (my + self.g.get("lift_target", 0.025)), -0.15, 0.3))

    def _crush(self, jaw):
        self._last_side = jaw["side"]
        """aplastón: lo encerrado se pulveriza y renace ×mult en un racimo compacto de color nuevo."""
        up, lo = self._arm_pts(jaw)
        mouth = jaw
        hx = (up[2][0] + lo[2][0]) / 2
        hy = (up[2][1] + lo[2][1]) / 2
        ten = self.tension()
        pan = self.pan(hx)
        held = jaw.get("held") or []
        jaw["held"] = None
        k = len(held)
        if k:
            pts, (cxm, cym) = self._held_pos(dict(jaw, held=held))
            for x, y, c in pts[:400]:
                if self.rng.random() < 0.6:
                    self.dust.append([x, y, self.rng.uniform(-120, 120), self.rng.uniform(-120, 120), 0.0, c])
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
        """racimo de color nuevo en los huecos libres más cercanos; sale despacio hacia el centro,
        un poco corrido hacia la otra pinza (como en la referencia)."""
        # destino = centro del rombo que va a formar la OTRA pinza (calculado con su geometría)
        other = next(j for j in self.jaws if j["side"] != self._last_side)
        up, lo = self._arm_pts(other, math.radians(self.g.get("catch_deg", 88)))
        poly = [up[0], up[1], up[2], lo[2], lo[1]]
        tx = sum(q[0] for q in poly) / 5
        ty = self.cy - self._lift() * self.R
        k = -math.log(max(1e-3, self.space.damping))      # con este damping llega justo al punto
        self.spawn_free(x0, y0, n, self.cur, drift=((tx - x0) * k, (ty - y0) * k))

    # ---------- dibujo ----------
    def draw_machine(self, c):
        r = self.rad[0] if self.rad else self.r_big
        for jaw in self.jaws:
            if jaw.get("held"):
                pts, _ = self._held_pos(jaw)
                for ci in set(p[2] for p in pts):
                    self._ball_pts(c, [skia.Point(x, y) for x, y, cc in pts if cc == ci], self.colors[ci], r)
        self._draw_arms(c)

    def _draw_arms(self, c):
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
            self._gear(c, *self._world(jaw["side"], 0, 0))

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

    def step(self):
        super().step()
        if self.broken_at is None and self.done_at is None:
            self._drive_arms(final=True)

    def on_break(self):
        for jaw in self.jaws:
            for _, _, segs in jaw["arms"]:
                for sh in segs:
                    sh.filter = pymunk.ShapeFilter(mask=0)
