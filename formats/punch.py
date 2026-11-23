"""PUNCH FILL — calcado de la referencia ref05 (SatisfiedBounce, 1.2M y 2.8M vistas).

Ver reference/formats/punch/SPEC.md. Lógica:
- Dos brazos con guante giran alrededor del pivote central, cada uno a su velocidad.
- Cuando los guantes chocan (CLAP), las bolas atrapadas en la cuña entre los dos brazos se DUPLICAN.
  Nada se multiplica por existir: si la cuña está vacía, el golpe no suma nada.
- Cada golpe trae un color nuevo (un brainrot) que se propaga por la pila como una ola.
- Después del golpe los brazos rebotan y se abren; el próximo choque ocurre en otro lado.
- El Pacer solo regula la velocidad de los brazos (la regla "cada golpe duplica" nunca cambia).
"""
import math
import numpy as np
import pymunk
import skia

from engine.sim import Sim
from engine.gfx import W, H, rgb, draw_text, hsv, text_width
from characters import get as get_char

BALL, ARM = 4, 5

TXT = {
    "en": {"t1": "CAN 1 BALL REFILL IT", "t2": "IN 60 SECONDS?", "balls": "BALLS", "full": "FULL!",
           "almost": "IT GETS THIS FULL...", "taking": "IS TAKING OVER", "wins": "WINS!",
           "cta1": "WHICH BRAINROT WINS NEXT?", "cta2": "SUBSCRIBE FOR ROUND {n}"},
    "es": {"t1": "¿PUEDE 1 BOLA LLENARLO", "t2": "EN 60 SEGUNDOS?", "balls": "BOLAS", "full": "¡LLENO!",
           "almost": "SE LLENA ASÍ...", "taking": "VA GANANDO", "wins": "¡GANA!",
           "cta1": "¿QUÉ BRAINROT GANA LA PRÓXIMA?", "cta2": "SUSCRIBITE PARA LA RONDA {n}"},
}


def _ang(a):
    return (a + math.pi) % (2 * math.pi) - math.pi


class Punch(Sim):
    SUBSTEPS = 3

    def setup(self):
        g = self.g
        self.L = TXT[g.get("lang", "en")]
        self.cx, self.cy, self.R = W / 2, 905, 455
        self.r = g["ball_r"]
        self.capacity = int(g.get("packing", 0.74) * (self.R / self.r) ** 2)
        self.space.gravity = (0, g["gravity"])
        self.space.iterations = 8
        self.space.use_spatial_hash(self.r * 2.2, 9000)
        # aro
        segs = 120
        for i in range(segs):
            a0, a1 = 2 * math.pi * i / segs, 2 * math.pi * (i + 1) / segs
            rr = self.R + 6
            s = pymunk.Segment(self.space.static_body, (self.cx + rr * math.cos(a0), self.cy + rr * math.sin(a0)),
                               (self.cx + rr * math.cos(a1), self.cy + rr * math.sin(a1)), 6)
            s.elasticity, s.friction = 0.5, 0.3
            self.space.add(s)
        # brazos: varilla + guante
        self.arm_len = self.R - g["head_h"] / 2 - 6
        self.arms = []
        for k in range(2):
            b = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
            b.position = (self.cx, self.cy)
            b.angle = g["start_angles"][k]
            L, hw, hh = self.arm_len, g["head_w"], g["head_h"]
            # como en ref05: la varilla NO choca con las bolas (las atraviesa); solo el guante golpea
            head = pymunk.Poly(b, [(L - hh / 2, -hw / 2), (L + hh / 2, -hw / 2), (L + hh / 2, hw / 2), (L - hh / 2, hw / 2)],
                               radius=4)
            head.elasticity, head.friction, head.collision_type = 0.4, 0.4, ARM
            self.space.add(b, head)
            self.arms.append(b)
        # ciclo de aplauso: los brazos se abren alrededor de un centro y se cierran barriendo las bolas
        self.cyc_t0, self.cyc_T = 0.0, 1.4
        self.cyc_from = self.cyc_to = math.pi / 2       # centro del aplauso (abajo = donde caen las bolas)
        self.cyc_open = 1.6
        self.clapped = False
        self.speed_k = 1.0
        # ángulo de choque: los guantes se tocan cuando la cuña mide ~ el ancho del guante
        self.clap_angle = 2 * math.atan2(g["head_w"] / 2 + 4, self.arm_len)
        half0 = self.clap_angle / 2
        self.arms[0].angle, self.arms[1].angle = math.pi / 2 - 1.6, math.pi / 2 + 1.6
        self.bodies, self.wave_of = [], []
        self.chars = [get_char(k) for k in g["chars"]]
        self.waves = []   # (cx, cy, t0, char_idx)
        self.cur = 0
        self.popups_txt = []
        self.flashes = []
        self.last_voice = -9
        self.claps = 0
        self.round = g.get("round", 2)
        self._add_ball(self.cx + 60, self.cy - 250, 220, 0, 0)
        self.waves.append((self.cx, self.cy, -10.0, 0))

    # ---------- bolas (sin objetos Python por bola: velocidad) ----------
    def _add_ball(self, x, y, vx, vy, wave):
        b = pymunk.Body(1, pymunk.moment_for_circle(1, 0, self.r))
        b.position, b.velocity = (x, y), (vx, vy)
        s = pymunk.Circle(b, self.r)
        s.elasticity, s.friction, s.collision_type = 0.45, 0.25, BALL
        self.space.add(b, s)
        self.bodies.append(b)
        self.wave_of.append(wave)

    def positions(self):
        return np.array([b.position for b in self.bodies], np.float64).reshape(-1, 2)

    def tension(self):
        return min(1.0, len(self.bodies) / self.capacity) ** 1.2

    # ---------- clap ----------
    def _clap(self):
        a0, a1 = self.arms[0].angle, self.arms[1].angle
        mid = a0 + _ang(a1 - a0) / 2
        half = abs(_ang(a1 - a0)) / 2 + 0.06
        P = self.positions()
        dx, dy = P[:, 0] - self.cx, P[:, 1] - self.cy
        rad = np.hypot(dx, dy)
        phi = np.arctan2(dy, dx)
        inside = (np.abs((phi - mid + np.pi) % (2 * np.pi) - np.pi) < half) & (rad < self.R)
        idx = np.nonzero(inside)[0]
        k = len(idx)
        hx = self.cx + self.arm_len * math.cos(mid)
        hy = self.cy + self.arm_len * math.sin(mid)
        self.claps += 1
        ten = self.tension()
        pan = self.pan(hx)
        self.flashes.append([hx, hy, 0.0])
        self.cam.kick(0.18 + 0.25 * min(1, k / 200))
        if k == 0 or self.done_at is not None:   # golpe vacío: no suma nada
            self.audio.hit(self.t, 0.5, "punch", pan, ten)
            self.audio.hit(self.t, 0.4, "metal", pan, ten)
            return
        room = self.capacity - len(self.bodies)
        n_new = min(k, room)
        self.cur = (self.cur + 1) % len(self.chars)
        wave = len(self.waves)
        self.waves.append((hx, hy, self.t, self.cur))
        for i in idx:
            self.wave_of[i] = wave
        # las nuevas nacen dentro de la cuña (densas) y salen despedidas al abrirse los brazos
        rng = self.rng
        for j in range(n_new):
            src = self.bodies[idx[j % k]]
            px, py = src.position
            a = rng.uniform(0, 2 * math.pi)
            off = rng.uniform(0.3, 1.0) * self.r
            vx, vy = src.velocity
            self._add_ball(px + off * math.cos(a), py + off * math.sin(a),
                           vx * 0.3 - math.cos(mid) * rng.uniform(60, 220),
                           vy * 0.3 - math.sin(mid) * rng.uniform(60, 220), wave)
        cxw = self.cx + 0.62 * self.arm_len * math.cos(mid)
        cyw = self.cy + 0.62 * self.arm_len * math.sin(mid)
        self.popups_txt.append([cxw, cyw, "×2" if k <= 3 else f"+{n_new}", 0.0])
        self.particles.burst(hx, hy, (1, 1, 1), n=18, speed=700, size=4, life=0.4)
        self.particles.burst(hx, hy, self.chars[self.cur].color, n=14, speed=500, size=5)
        # sonido: golpe + aplastado + cascada de pops (más bolas = más pops, nunca saturación)
        e = min(1.0, 0.4 + k / 150)
        self.audio.hit(self.t, e, "punch", pan, ten)
        self.audio.hit(self.t + 0.003, e, "squish", pan, ten)
        pops = int(min(10, 2 + 2 * math.log2(1 + k)))
        for i in range(pops):
            self.audio.event(self.t + 0.04 + i * 0.028, "pop", 0.9 + 0.5 * ten + 0.07 * i)
        if self.t - self.last_voice > self.g.get("voice_gap", 2.6):
            self.audio.voice(self.t + 0.08, self.chars[self.cur].key, "short", pan)
            self.last_voice = self.t

    def _want(self, t):
        g = self.g
        return self.capacity * min(1.0, max(0.0, t) / g["target_t"]) ** g["curve"]

    def _plan(self, T):
        """elige centro y apertura del próximo aplauso para que barra ~ lo que pide la curva.
        La regla (duplica lo atrapado) no se toca: solo se elige DÓNDE golpear."""
        n = len(self.bodies)
        k_star = max(1.0, min(n, self._want(self.t + T) - n))
        if n < 12:   # al principio: va a buscar a las bolas
            P = self.positions()
            j = self.rng.randrange(n)
            return math.atan2(P[j, 1] - self.cy, P[j, 0] - self.cx) + self.rng.uniform(-0.3, 0.3), self.rng.uniform(1.0, 1.8)
        P = self.positions()
        phi = np.arctan2(P[:, 1] - self.cy, P[:, 0] - self.cx)
        h, _ = np.histogram(phi, bins=72, range=(-np.pi, np.pi))
        cum = np.concatenate([[0], np.cumsum(np.concatenate([h, h, h]))])
        best, best_err = None, 1e18
        for half in (0.6, 0.9, 1.2, 1.5, 1.8, 2.1, 2.4):
            hb = int(round(half / (2 * np.pi / 72)))
            for cbin in range(72):
                lo, hi = 72 + cbin - hb, 72 + cbin + hb + 1
                cnt = cum[hi] - cum[lo]
                err = abs(cnt - k_star) - 0.02 * k_star * half + self.rng.random() * 0.05 * k_star
                if err < best_err:
                    best_err, best = err, (-np.pi + (cbin + 0.5) * 2 * np.pi / 72, half)
        return best

    def _arm_motion(self):
        T = self.cyc_T
        u = (self.t - self.cyc_t0) / T
        half_c = self.clap_angle / 2 * 0.98
        if u >= 1.0:
            if not self.clapped:
                self._clap()
            self.clapped = False
            self.cyc_t0 = self.t
            self.cyc_from = self.cyc_to
            base = self.g.get("cycle", 1.5)
            self.cyc_T = base / self.speed_k * self.rng.uniform(0.85, 1.15)
            self.cyc_to = self.cyc_from
            self.cyc_open = self.rng.uniform(1.4, 2.0)
            self.planned = False
            u = 0.0
        # centro se desplaza suave hacia el objetivo; apertura: abre rápido, cierra acelerando (golpe)
        if u >= 0.3 and not getattr(self, "planned", True):
            # se planifica con las recién nacidas ya caídas: centro y apertura del cierre
            self.planned = True
            tgt, half = self._plan(self.cyc_T * 0.7)
            self.plan_from_center = self.cyc_from
            self.cyc_to = self.cyc_from + _ang(tgt - self.cyc_from)
            self.close_open = half
        v = min(1.0, max(0.0, (u - 0.3) / 0.22))   # el centro viaja SOLO con los brazos abiertos (sin "arado")
        e = v * v * (3 - 2 * v)
        center = self.cyc_from + (self.cyc_to - self.cyc_from) * e
        open_k = math.sin(math.pi * min(1.0, u / 0.3) / 2) if u < 0.52 else 1 - ((u - 0.52) / 0.48) ** 2.2
        peak = self.cyc_open if u < 0.3 else self.cyc_open + (getattr(self, "close_open", self.cyc_open) - self.cyc_open) * v
        half = half_c + (peak - half_c) * max(0.0, open_k)
        targets = [center - half, center + half]
        for b, a in zip(self.arms, targets):
            cur = b.angle
            b.angular_velocity = _ang(a - cur) / self.dt
        if u > 0.97 and not self.clapped:
            self.clapped = True
            self._clap()

    # ---------- update ----------
    def update(self):
        g = self.g
        n = len(self.bodies)
        # Pacer: regula la velocidad de los brazos para llegar lleno al objetivo
        # curva medida en ref05: ~3% a los 10s, ~16% a los 22s, ~27% a los 34s, lleno al final
        want = self._want(self.t)
        ratio = n / max(1.0, want)
        self.ratio = ratio
        tgt = 1.4 if ratio < 0.6 else (0.3 if ratio > 1.4 else (0.6 if ratio > 1.05 else 1.0))
        if self.done_at is not None:
            tgt = 0.25
        self.speed_k += (tgt - self.speed_k) * min(1, self.dt * 1.2)
        self._arm_motion()
        # contención dura (anti-tunneling) vectorizada: solo se tocan las que se salieron
        if n:
            P = self.positions()
            d = np.hypot(P[:, 0] - self.cx, P[:, 1] - self.cy)
            lim = self.R - self.r
            out = np.nonzero(d > lim)[0]
            for i in out:
                b = self.bodies[i]
                ux, uy = (P[i, 0] - self.cx) / d[i], (P[i, 1] - self.cy) / d[i]
                b.position = (self.cx + ux * (lim - 0.5), self.cy + uy * (lim - 0.5))
                vx, vy = b.velocity
                vn = vx * ux + vy * uy
                if vn > 0:
                    b.velocity = (vx - 1.5 * vn * ux, vy - 1.5 * vn * uy)
            # golpecitos contra el aro -> "lluvia" de clacks (muestreada, nunca satura)
            if self.frame % 2 == 0:
                hits = np.nonzero(d > lim - 1.5)[0]
                for i in hits[: 3]:
                    self.audio.hit(self.t + self.rng.uniform(0, self.dt), 0.25 + 0.4 * self.rng.random(), "clack",
                                   self.pan(P[i, 0]), self.tension())
        # olas de color (infección): cada bola toma el color de la última ola que la alcanzó
        if self.waves and n:
            P = self.positions()
            wo = np.array(self.wave_of)
            for wi in range(max(0, len(self.waves) - 3), len(self.waves)):
                ox, oy, t0, _ = self.waves[wi]
                age = self.t - t0
                if 0 <= age < 3.5:
                    reach = 120 + 520 * age
                    hit = (np.hypot(P[:, 0] - ox, P[:, 1] - oy) < reach) & (wo < wi)
                    wo[hit] = wi
            self.wave_of = wo.tolist()
        if self.frame % 6 == 0:
            self.audio.set_tension(self.t, self.tension())
        for p in self.popups_txt:
            p[3] += self.dt
        self.popups_txt = [p for p in self.popups_txt if p[3] < 0.9]
        for f in self.flashes:
            f[2] += self.dt
        self.flashes = [f for f in self.flashes if f[2] < 0.3]
        # clímax
        if self.done_at is None and n >= self.capacity:
            self.done_at = self.t
            self.winner = self.cur
            self.audio.set_climax(self.t)
            self.audio.event(self.t - 0.3, "riser", 1.0)
            self.audio.event(self.t, "boom", 1.0)
            self.audio.event(self.t + 0.05, "chord", 1.0)
            self.audio.voice(self.t + 0.9, self.chars[self.cur].key, "full", 0.0, 1.2)
            self.cam.kick(0.9)
        if self.done_at is not None and self.end_at is None and self.t > self.done_at + 5.0:
            self.end_at = self.t

    # ---------- dibujo ----------
    def draw_world(self, c):
        # aro blanco fino + arco amarillo de progreso (como la referencia)
        ring = skia.Paint(Color4f=rgb((1, 1, 1), 0.85), AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=4)
        c.drawCircle(self.cx, self.cy, self.R + 6, ring)
        frac = min(1.0, len(self.bodies) / self.capacity)
        if frac > 0:
            arc = skia.Paint(Color4f=rgb(self.pal["accent"]), AntiAlias=True, Style=skia.Paint.kStroke_Style,
                             StrokeWidth=9, StrokeCap=skia.Paint.kRound_Cap)
            rr = self.R + 22
            c.drawArc(skia.Rect(self.cx - rr, self.cy - rr, self.cx + rr, self.cy + rr), -90, 360 * frac, False, arc)
        self.draw_balls(c)
        self.draw_arms(c)
        for x, y, age in self.flashes:
            k = age / 0.3
            c.drawCircle(x, y, 40 + 120 * k, skia.Paint(Color4f=skia.Color4f(1, 1, 1, 0.7 * (1 - k)), AntiAlias=True,
                                                       MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 18)))
        self.particles.draw(c)
        for x, y, s, age in self.popups_txt:
            pop = 1 + 0.4 * max(0, 0.15 - age) / 0.15
            draw_text(c, s, x, y + 18, 64 * pop, (1, 1, 1), stroke=9, alpha=min(1, (0.9 - age) * 4), max_w=360)

    def draw_balls(self, c):
        if not self.bodies:
            return
        P = self.positions()
        wo = np.array(self.wave_of)
        r = self.r
        for wi in np.unique(wo):
            col = self.chars[self.waves[wi][3]].color
            sel = P[wo == wi]
            pts = [skia.Point(float(x), float(y)) for x, y in sel]
            dark = [v * 0.55 for v in col]
            light = [min(1, v * 0.6 + 0.45) for v in col]
            c.drawPoints(skia.Canvas.kPoints_PointMode, pts,
                         skia.Paint(Color4f=rgb(dark), AntiAlias=True, StrokeWidth=2 * r, StrokeCap=skia.Paint.kRound_Cap))
            c.drawPoints(skia.Canvas.kPoints_PointMode, pts,
                         skia.Paint(Color4f=rgb(col), AntiAlias=True, StrokeWidth=2 * r - 2.4, StrokeCap=skia.Paint.kRound_Cap))
            hl = [skia.Point(p.fX - r * 0.33, p.fY - r * 0.33) for p in pts]
            c.drawPoints(skia.Canvas.kPoints_PointMode, hl,
                         skia.Paint(Color4f=rgb(light, 0.9), AntiAlias=True, StrokeWidth=r * 0.75, StrokeCap=skia.Paint.kRound_Cap))

    def draw_arms(self, c):
        g = self.g
        L, hw, hh = self.arm_len, g["head_w"], g["head_h"]
        rod = skia.Paint(Color4f=rgb((0.72, 0.73, 0.76)), AntiAlias=True, StrokeWidth=11, StrokeCap=skia.Paint.kRound_Cap)
        rod_hi = skia.Paint(Color4f=rgb((0.93, 0.93, 0.95)), AntiAlias=True, StrokeWidth=4, StrokeCap=skia.Paint.kRound_Cap)
        for b in self.arms:
            c.save(); c.translate(self.cx, self.cy); c.rotate(math.degrees(b.angle))
            c.drawLine(0, 0, L - hh / 2, 0, rod)
            c.drawLine(0, -2, L - hh / 2, -2, rod_hi)
            c.translate(L, 0)
            self._glove(c, hw, hh)
            c.restore()
        # pivote
        c.drawCircle(self.cx, self.cy, 15, skia.Paint(Color4f=rgb((0.85, 0.86, 0.9)), AntiAlias=True))
        c.drawCircle(self.cx, self.cy, 15, skia.Paint(Color4f=rgb((0.3, 0.3, 0.35)), AntiAlias=True,
                                                      Style=skia.Paint.kStroke_Style, StrokeWidth=3))
        c.drawCircle(self.cx, self.cy, 5, skia.Paint(Color4f=rgb((0.3, 0.3, 0.35)), AntiAlias=True))

    @staticmethod
    def _glove(c, hw, hh):
        """guante/martillo gris metálico (cuerpo + puño + nudillos), como el de la referencia."""
        outline = skia.Paint(Color4f=rgb((0.22, 0.22, 0.25)), AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=4)
        sh = skia.GradientShader.MakeLinear([(0, -hw / 2), (0, hw / 2)],
                                            [rgb((0.88, 0.88, 0.9)).toColor(), rgb((0.55, 0.56, 0.6)).toColor()])
        body = skia.RRect.MakeRectXY(skia.Rect(-hh / 2, -hw / 2, hh * 0.32, hw / 2), 16, 16)
        c.drawRRect(body, skia.Paint(Shader=sh, AntiAlias=True)); c.drawRRect(body, outline)
        cuff = skia.RRect.MakeRectXY(skia.Rect(hh * 0.22, -hw * 0.42, hh / 2, hw * 0.42), 8, 8)
        c.drawRRect(cuff, skia.Paint(Shader=sh, AntiAlias=True)); c.drawRRect(cuff, outline)
        thumb = skia.RRect.MakeRectXY(skia.Rect(-hh * 0.25, hw * 0.28, hh * 0.15, hw * 0.62), 10, 10)
        c.drawRRect(thumb, skia.Paint(Shader=sh, AntiAlias=True)); c.drawRRect(thumb, outline)
        line = skia.Paint(Color4f=rgb((0.35, 0.35, 0.4)), AntiAlias=True, StrokeWidth=3)
        for k in (-0.22, 0.0, 0.22):  # nudillos
            c.drawLine(-hh / 2 + 6, k * hw, -hh * 0.05, k * hw, line)
        c.drawLine(hh * 0.3, -hw * 0.3, hh * 0.3, hw * 0.3, line)

    def draw_hud(self, c):
        L, acc = self.L, self.pal["accent"]
        n = len(self.bodies)
        done = self.done_at is not None
        if done and self.t - self.done_at > 0.3:
            draw_text(c, L["almost"], W / 2, 250, 76, (1, 1, 1), stroke=12)
        else:
            draw_text(c, L["t1"], W / 2, 170, 78, (1, 1, 1), stroke=12)
            draw_text(c, L["t2"], W / 2, 260, 78, acc, stroke=12)
        # contador grande "N BALLS"
        y = self.cy + self.R + 150
        num = f"{n:,}"
        size = 112
        wn, wb = text_width(num, size), text_width(L["balls"], 44)
        x0 = W / 2 - (wn + 18 + wb) / 2
        draw_text(c, num, x0, y, size, (1, 1, 1), align="left", stroke=12)
        draw_text(c, L["balls"], x0 + wn + 18, y, 44, (0.75, 0.75, 0.8), align="left", stroke=8)
        # quién está dominando (brainrot del color actual)
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
