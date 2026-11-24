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
from engine.gfx import rgb, W, H

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


SPEC_PATH = "reference/formats/crusher_jaws/spec.json"


def load_spec():
    import json, os
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(here, SPEC_PATH)) as f:
        return json.load(f)


class CrusherJaws(Arena):
    TXT = TXT

    def setup_machine(self):
        g = self.g
        sp = load_spec()
        self.spec = sp
        self.curve = np.array(sp["curva_conteo"], float)          # el Pacer sigue ESTA tabla
        self.cap_full = int(sp["bolas"]["capacidad_full"])
        self.capacity = self.cap_full
        self.t_spill = float(g.get("t_spill", 23.0))               # aro desaparece (ficha: final)
        self.spill_at = None
        # tamaño de la ficha: grandes hasta que no entran (~400), después se achican apenas
        self.r_big = self.r0 = sp["bolas"]["r_inicial_R"] * self.R
        self.r_min = sp["bolas"]["r_final_R"] * self.R
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
            # los brazos empujan solo mientras entran y cierran (φ > 0); al salir pasan por detrás del racimo
            # empujan mientras entran barriendo; desde que el rombo se forma (55°) lo de adentro queda encerrado
            # (no se escurre) hasta la "T"; al salir pasan por detrás del racimo
            solid = jaw["phi"] > math.radians(80)
            if solid != jaw.get("solid", True):
                jaw["solid"] = solid
                f = pymunk.ShapeFilter() if solid else pymunk.ShapeFilter(mask=0)
                for _, _, segs in jaw["arms"]:
                    for sh in segs:
                        sh.filter = f
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
    def r_for(self, n):
        if self.spill_at is not None:
            return 1e9                                # durante el derrame el tamaño lo maneja update()
        return super().r_for(n)

    def _spill(self):
        """final de la referencia: el aro desaparece y la masa se derrama fuera del círculo."""
        self.spill_at = self.t
        self.ring_on = False
        self.space.remove(*self.ring_segs)
        self.ring_segs = []
        self.spill_r0 = self.rad[0] if self.rad else self.r_min
        for b in self.bodies:
            dx, dy = b.position.x - self.cx, b.position.y - self.cy
            b.velocity = (b.velocity.x + dx * 0.04, b.velocity.y + dy * 0.04)   # se derrama despacio, en masa
        self.audio.set_climax(self.t)
        self.audio.event(self.t - 0.3, "riser", 1.0)
        self.audio.event(self.t, "boom", 0.9)
        self.cam.kick(0.5)

    def update(self):
        super().update()
        if self.spill_at is None:
            if self.t >= self.t_spill and len(self.bodies) >= 0.8 * self.cap_full:
                self._spill()
            return
        ds = self.t - self.spill_at
        if self.bodies and ds < 1.5:                 # sin el aro, las bolas se aflojan y se ven más grandes (ref)
            r = self.spill_r0 * (1 + 0.25 * ds / 1.5)
            for b in self.bodies:
                for sh in b.shapes:
                    sh.unsafe_set_radius(r)
            self.rad = [r] * len(self.bodies)
        if self.frame % 3 == 0 and self.bodies:
            P = self.positions()
            self.remove_balls(np.nonzero((P[:, 0] < -60) | (P[:, 0] > W + 60) | (P[:, 1] < -60) | (P[:, 1] > H + 60))[0])
        if self.end_at is None and (ds > 8.0 or (ds > 4.0 and len(self.bodies) < 3)):
            self.end_at = self.t                     # vacío: empalma con el frame 1

    def machine_step(self):
        self._update_phis()
        for jaw in self.jaws:
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
            if not jaw.get("solid", True):
                continue
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
        up, lo = self._arm_pts(jaw, math.radians(80))   # lo que encerró el rombo al formarse
        poly = [up[0], up[1], up[2], lo[2], lo[1]]
        path = skia.Path()
        path.moveTo(*poly[0])
        for q in poly[1:]:
            path.lineTo(*q)
        path.close()
        return np.array([path.contains(float(x), float(y)) for x, y in P], bool)

    def _lift(self):
        """altura a la que sale el racimo: corrige hacia arriba si la masa está baja y viceversa,
        para que la masa quede apenas por encima del centro (ref: 62% del tiempo arriba) en cualquier semilla."""
        if not self.bodies:
            return 0.1
        my = (float(np.mean([b.position.y for b in self.bodies])) - self.cy) / self.R
        return float(np.clip(self.g.get("lift_base", 0.1) + self.g.get("lift_gain", 4.0) * (my + self.g.get("lift_target", 0.025)), -0.1, 0.4))

    def _crush(self, jaw):
        self._last_side = jaw["side"]
        """aplastón: lo encerrado se pulveriza y renace ×mult en un racimo compacto de color nuevo."""
        up, lo = self._arm_pts(jaw)
        mouth = jaw
        hx = (up[2][0] + lo[2][0]) / 2
        hy = (up[2][1] + lo[2][1]) / 2
        ten = self.tension()
        pan = self.pan(hx)
        k = 0
        if self.bodies:
            P = self.positions()
            ins = np.nonzero(self._inside_jaw(P, mouth))[0]
            # Pacer: atrapa lo necesario para seguir la curva de la referencia (×4 de lo atrapado)
            n = len(self.bodies)
            want = float(np.interp(self.t + 2.1, self.curve[:, 0], self.curve[:, 1]))
            cap = max(1, int(math.ceil((want - n) / (self.mult - 1))))
            if n >= self.cap_full * 0.97 or self.spill_at is not None:
                cap = 10 ** 9                        # guerra de colores / vaciado: se lleva toda la mancha
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
        if self.spill_at is not None:
            n_new = 0                                # final: las pinzas vacían, ya no nace nada
        elif len(self.bodies) + k >= self.cap_full * 0.97:
            n_new = k                                # guerra de colores: la mancha cambia de color (no crece)
        else:
            n_new = min(k * self.mult, self.cap_full - len(self.bodies))
        self.gen += 1
        self.cur = self.gen % len(self.colors)
        if len(self.bodies) >= self.g.get("packed_n", 380) or self.spill_at is not None:
            self._paint_territory(cxm, cym, k, n_new)
        else:
            self._spawn_cluster(cxm, cym, n_new)
        self.flashes.append([cxm, cym, 0.0, self.colors[self.cur]])
        self.audio.hit(self.t + 0.003, min(1.0, 0.5 + k / 120), "squish", pan, ten)
        for i in range(int(min(9, 2 + 1.6 * math.log2(1 + n_new)))):
            self.audio.event(self.t + 0.05 + i * 0.03, "pop", 0.9 + 0.5 * ten + 0.07 * i)
        if n_new > k:
            self.pops.append([cxm, cym - 70, f"×{self.mult}" if k < 25 else f"+{n_new - k}", 0.0, self.colors[self.cur]])
        self.particles.burst(cxm, cym, self.colors[self.cur], n=22, speed=600, size=5)

    def _paint_territory(self, x0, y0, k, n_new):
        """círculo lleno: el aplastón convierte en el color nuevo una mancha compacta (×4 de lo aplastado) pegada a la
        pinza, y las bolitas extra llenan huecos con el color de su vecina → territorios sólidos, no confeti."""
        if n_new <= 0:
            return
        before = len(self.bodies)
        self._spawn_cluster(x0, y0, n_new, drift=False)            # en los huecos más cercanos, sin deslizarse
        P = self.positions()
        col = np.array(self.col)
        d2 = (P[:, 0] - x0) ** 2 + (P[:, 1] - y0) ** 2
        patch = np.argsort(d2)[: max(n_new, self.mult * k)]
        new_idx = np.arange(before, len(self.bodies))
        far_new = np.setdiff1d(new_idx, patch)
        old = np.setdiff1d(np.arange(before), patch)
        if len(far_new) and len(old):                              # las que cayeron lejos toman el color de su vecina
            for i in far_new:
                j = old[np.argmin((P[old, 0] - P[i, 0]) ** 2 + (P[old, 1] - P[i, 1]) ** 2)]
                self.col[i] = int(col[j]) if j < len(col) else self.col[j]
        for i in patch:
            self.col[i] = self.cur

    def _spawn_cluster(self, x0, y0, n, drift=True):
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
        # racimo compacto (los huecos libres más cercanos) que se desliza JUNTO y despacio hacia el rombo de la otra
        # pinza: todas con la MISMA velocidad (no se desarma), y el damping lo frena justo ahí (~1 s)
        other = next(j for j in self.jaws if j["side"] != self._last_side)
        up, lo = self._arm_pts(other, math.radians(55))
        tx = sum(q[0] for q in (up[0], up[1], up[2], lo[2], lo[1])) / 5
        ty = self.cy - self._lift() * self.R
        damp = -math.log(max(1e-3, self.space.damping))
        vx, vy = ((tx - x0) * damp, (ty - y0) * damp) if drift else (0.0, 0.0)
        for dist, x, y in cand[:n]:
            self.add_ball(x, y, vx, vy, self.cur)

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
