"""MARTILLO APLASTADOR — batalla de brainrots (ver reference/formats/hammer/SPEC.md).

El martillo APRIETA una ficha contra la pared → se aplasta → sobrevive y nacen +2 de su equipo.
La regla en pantalla es fija; el Pacer solo regula la velocidad del martillo y hace que algunas
fichas "se escurran" (near-miss) para cumplir el guion de líderes y el lleno entre el seg 44 y 52.
"""
import math
import pymunk
import skia

from engine.sim import Sim, MACHINE
from engine.gfx import W, H, rgb, draw_text, neon_ring, hsv
from engine.pacer import Pacer
from characters import get as get_char

TXT = {
    "en": {"hook1": "WHICH BRAINROT", "hook2": "FILLS THE CIRCLE?", "pick": "COMMENT YOUR PICK", "rule": "EVERY SQUASH = +{n}",
           "full": "FULL!", "wins": "WINS!", "close": "SO CLOSE!", "cta1": "WHO WINS NEXT ROUND?",
           "cta2": "SUBSCRIBE TO SEE", "lead": "LEADING"},
    "es": {"hook1": "¿QUÉ BRAINROT", "hook2": "LLENA EL CÍRCULO?", "pick": "COMENTÁ TU ELEGIDO", "rule": "CADA APLASTADA = +{n}",
           "full": "¡LLENO!", "wins": "¡GANA!", "close": "¡CASI!", "cta1": "¿QUIÉN GANA LA PRÓXIMA?",
           "cta2": "SUSCRIBITE PARA VERLO", "lead": "VA GANANDO"},
}


class Hammer(Sim):
    def setup(self):
        g = self.g
        self.L = TXT[g.get("lang", "en")]
        self.cx, self.cy, self.R = W / 2, g.get("arena_y", 1085), g.get("arena_r", 440)
        self.ring_walls(self.cx, self.cy, self.R)
        self.ring_img, self.ring_half = neon_ring(self.R + 8, 9, g["hue"])
        self.chars = [get_char(k) for k in g["chars"]]
        r_avg = g["chip_r"] * sum(c.size for c in self.chars) / len(self.chars)
        self.capacity = int(g.get("packing", 0.5) * (self.R / r_avg) ** 2)
        self.pacer = Pacer(g["target_t"], self.capacity, g["curve"], len(self.chars), g["winner"], self.rng)

        # martillo: brazo cinemático con N cabezas
        self.arm = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
        self.arm.position = (self.cx, self.cy)
        self.space.add(self.arm)
        self.heads = []
        hw, hh = g["head_w"], g["head_h"]
        # la cara del martillo queda a menos de un diámetro de la pared: la ficha no pasa, se aplasta
        L = self.R - 1.1 * g["chip_r"] - hh / 2
        for k in range(g["heads"]):
            a = 2 * math.pi * k / g["heads"]
            ca, sa = math.cos(a), math.sin(a)
            hx, hy = L * ca, L * sa
            pts = [(-hh / 2, -hw / 2), (hh / 2, -hw / 2), (hh / 2, hw / 2), (-hh / 2, hw / 2)]
            rot = [(hx + px * ca - py * sa, hy + px * sa + py * ca) for px, py in pts]
            s = pymunk.Poly(self.arm, rot, radius=2)
            s.elasticity, s.friction, s.collision_type = 1.0, 0.3, MACHINE
            rod = pymunk.Segment(self.arm, (0, 0), (hx * 0.85, hy * 0.85), 7)
            rod.elasticity, rod.collision_type = 0.9, MACHINE
            self.space.add(s, rod)
            self.heads.append((a, L))
        self.head_glow = 0.0
        self.counts = [0] * len(self.chars)
        self.pending = []
        self.squashes = []
        self.speed_k = 1.0
        self.last_voice = -9.0
        self.near_miss_shown = 0.0
        self.lead_flash = 0.0
        self.last_leader = None
        # arranque: 1 ficha por equipo, ya en movimiento (hook: algo se mueve en el frame 1)
        for i, ch in enumerate(self.chars):
            for j in range(g.get("start_n", 2)):
                a = -math.pi / 2 + (i - (len(self.chars) - 1) / 2) * 0.75 + (j - 0.5) * 0.22
                rr = (0.62 - 0.12 * j) * self.R
                x, y = self.cx + rr * math.cos(a), self.cy + rr * math.sin(a)
                self.add_chip(ch, i, x, y, self.rng.uniform(-420, 420), self.rng.uniform(-200, 100))
                self.counts[i] += 1

    # ---------- eventos ----------
    def on_hit(self, ch, arb):
        x, y = ch.body.position
        d = math.hypot(x - self.cx, y - self.cy)
        total = max(1, sum(self.counts))
        sh = self.pacer.shares(self.t)
        lagging = self.counts[ch.team] / total < sh[ch.team] * 0.8
        reach = 3.6 if lagging else 2.6        # al que va atrás se lo aplasta un poco más lejos de la pared
        if d < self.R - reach * ch.r:          # golpe en el aire: solo rebote
            self.audio.hit(self.t, 0.35, "metal", self.pan(x), self.tension())
            return
        if self.done_at is not None:
            return
        # near-miss guionado: solo se escurre si su equipo va MUY pasado del guion y otro va atrasado
        mine = self.counts[ch.team] / total
        behind = any(self.counts[i] / total < sh[i] * 0.85 for i in range(len(sh)) if i != ch.team)
        if self.counts[ch.team] > 5 and mine > sh[ch.team] * 1.15 and behind and self.rng.random() < 0.85:
            # se escurre: sale disparada hacia el centro (casi la aplastan)
            ux, uy = (self.cx - x) / d, (self.cy - y) / d
            ch.body.velocity = (ux * 900, uy * 900)
            ch.flash = 0.15
            self.audio.hit(self.t, 0.5, ch.char.sound["kind"], self.pan(x), self.tension())
            return
        self.pending.append(ch)

    def tension(self):
        return min(1.0, sum(self.counts) / self.capacity) ** 1.3

    def _squash(self, ch):
        """la ficha queda aplastada contra la pared, sobrevive y nacen +N detrás del martillo."""
        x, y = ch.body.position
        n = self.g["mult"] + (1 if ch.char.power == "split" else 0)
        n = max(0, min(n, self.capacity - sum(self.counts)))
        dx, dy = x - self.cx, y - self.cy
        d = math.hypot(dx, dy) or 1
        ux, uy = dx / d, dy / d
        tx, ty = -uy, ux                                   # tangente (sentido de giro +)
        sgn = -1 if self.arm.angular_velocity > 0 else 1    # detrás del martillo
        self.squashes.append([x, y, math.degrees(math.atan2(dy, dx)), ch.char, ch.r, 0.0])
        # la original sale disparada hacia adentro por detrás de la cabeza
        back = self.g["head_w"] / 2 + ch.r * 1.3
        ch.body.position = (x + tx * sgn * back - ux * ch.r * 0.6, y + ty * sgn * back - uy * ch.r * 0.6)
        ch.body.velocity = (-ux * 650 + tx * sgn * 250, -uy * 650 + ty * sgn * 250)
        ch.flash, ch.born = 0.2, self.t
        for i in range(n):
            k = i + 1
            px = x + tx * sgn * back - ux * ch.r * (0.6 + 2.15 * k)
            py = y + ty * sgn * back - uy * ch.r * (0.6 + 2.15 * k)
            sp = self.rng.uniform(450, 750) * (1.4 if ch.char.power == "double_bounce" else 1.0)
            a = math.atan2(-uy, -ux) + self.rng.uniform(-0.7, 0.7)
            self.add_chip(ch.char, ch.team, px, py, sp * math.cos(a), sp * math.sin(a))
            self.counts[ch.team] += 1
        col = ch.char.color
        self.particles.burst(x, y, col, n=16, speed=600)
        self.particles.burst(x, y, (1, 1, 1), n=6, speed=300, size=3)
        if n:
            self.popups.add(x - ux * 60, y - uy * 60 - 20, f"+{n}", col, 54)
        ten = self.tension()
        pan = self.pan(x)
        self.audio.hit(self.t, 0.9, "metal", pan, ten)
        self.audio.hit(self.t + 0.004, 0.85, "squish", pan, ten)
        for i in range(n):
            self.audio.event(self.t + 0.06 + 0.05 * i, "pop", 1.0 + 0.6 * ten + 0.12 * i)
        if self.t - self.last_voice > self.g.get("voice_gap", 2.4):
            self.audio.voice(self.t + 0.05, ch.char.key, "short", pan)
            self.last_voice = self.t
        if ch.char.power == "slam":   # onda expansiva: empuja a las vecinas
            for o in self.chips:
                ox, oy = o.body.position.x - x, o.body.position.y - y
                d2 = ox * ox + oy * oy
                if 1 < d2 < (ch.r * 6) ** 2:
                    dd = math.sqrt(d2)
                    o.body.velocity = (o.body.velocity.x + ox / dd * 380, o.body.velocity.y + oy / dd * 380)
            self.cam.kick(0.22)
        self.cam.kick(0.12)

    def update(self):
        g = self.g
        total = sum(self.counts)
        ratio = total / max(1.0, self.pacer.desired(self.t))
        target = 1.8 if ratio < 0.7 else (0.3 if ratio > 1.15 else (0.6 if ratio > 1.0 else 1.0 + 0.3 * self.tension()))
        if self.done_at is not None:
            target = 0.0
        self.speed_k += (target - self.speed_k) * min(1, self.dt * 1.5)
        boost = self.speed_k
        if g["motion"] == "spin":
            self.arm.angular_velocity = g["speed"] * boost
        else:   # péndulo
            self.arm.angular_velocity = g["speed"] * 2.4 * math.cos(self.t * g["speed"] * 1.3) * boost
        for ch in self.pending:
            if ch in self.chips:
                self._squash(ch)
        self.pending = []
        for sq in self.squashes:
            sq[5] += self.dt
        self.squashes = [sq for sq in self.squashes if sq[5] < 0.22]
        self.keep_alive(140)
        self.contain_circle(self.cx, self.cy, self.R)
        self.head_glow = max(0.0, self.head_glow - self.dt * 4)
        if self.frame % 6 == 0:
            self.audio.set_tension(self.t, self.tension())
        lead = max(range(len(self.counts)), key=lambda i: self.counts[i])
        if lead != self.last_leader and self.t > 3:
            self.lead_flash = 1.0
        self.last_leader = lead
        self.lead_flash = max(0.0, self.lead_flash - self.dt * 1.5)
        s = sorted(self.counts, reverse=True)
        if self.t > 15 and s[0] > 30 and (s[0] - s[1]) / s[0] < 0.04 and self.done_at is None:
            self.near_miss_shown = 1.2
        self.near_miss_shown = max(0.0, self.near_miss_shown - self.dt)

        # clímax
        if self.done_at is None and sum(self.counts) >= self.capacity:
            self.done_at = self.t
            self.winner = lead
            self.audio.set_climax(self.t)
            self.audio.event(self.t - 0.3, "riser", 1.0)
            self.audio.event(self.t, "boom", 1.0)
            self.audio.event(self.t + 0.05, "chord", 1.0)
            self.audio.voice(self.t + 1.0, self.chars[lead].key, "full", 0.0, 1.2)
            self.audio.set_tension(self.t, 1.0)
            self.cam.kick(1.0)
            self.cam.zoom_target = 1.08
            for k in range(6):
                a = 2 * math.pi * k / 6
                self.particles.burst(self.cx + 0.5 * self.R * math.cos(a), self.cy + 0.5 * self.R * math.sin(a),
                                     hsv(k / 6), n=40, speed=900, size=7, life=1.2)
        if self.done_at is not None and self.end_at is None and self.t > self.done_at + 5.0:
            self.end_at = self.t

    # ---------- dibujo ----------
    def draw_world(self, c):
        rot = (self.t * 25) % 360
        c.save(); c.translate(self.cx, self.cy); c.rotate(rot)
        c.drawImage(self.ring_img, -self.ring_half, -self.ring_half)
        c.restore()
        # piso de la arena (disco translúcido)
        c.drawCircle(self.cx, self.cy, self.R, skia.Paint(Color4f=rgb(self.pal["floor"], 0.35), AntiAlias=True))
        self.draw_chips(c)
        self.draw_squashes(c)
        self.draw_hammer(c)
        self.particles.draw(c)
        self.popups.draw(c)

    def draw_squashes(self, c):
        """ficha aplastada: se achata contra la pared y se ensancha (squash & stretch)."""
        for x, y, ang, char, r, age in self.squashes:
            k = age / 0.22
            sq = 0.35 + 0.65 * k
            img, half = char.sprite(r)
            p = skia.Paint(AntiAlias=True)
            p.setAlphaf(1 - k)
            c.save(); c.translate(x, y); c.rotate(ang)
            c.scale(sq, 1.0 / sq * 0.9)
            c.drawImage(img, -half, -half, paint=p)
            c.restore()
            ring = skia.Paint(Color4f=rgb(char.color, 0.8 * (1 - k)), AntiAlias=True,
                              Style=skia.Paint.kStroke_Style, StrokeWidth=6 * (1 - k) + 1)
            c.drawCircle(x, y, r * (1 + 2.5 * k), ring)

    def draw_hammer(self, c):
        hw, hh = self.g["head_w"], self.g["head_h"]
        metal = self.pal["hammer"]
        c.save(); c.translate(self.cx, self.cy); c.rotate(math.degrees(self.arm.angle))
        rod = skia.Paint(Color4f=rgb((0.82, 0.84, 0.9)), AntiAlias=True, StrokeWidth=14,
                         StrokeCap=skia.Paint.kRound_Cap, Style=skia.Paint.kStroke_Style)
        for a, L in self.heads:
            c.drawLine(0, 0, L * math.cos(a) * 0.85, L * math.sin(a) * 0.85, rod)
        for a, L in self.heads:
            c.save(); c.translate(L * math.cos(a), L * math.sin(a)); c.rotate(math.degrees(a))
            rect = skia.Rect(-hh / 2, -hw / 2, hh / 2, hw / 2)
            if self.head_glow > 0:
                c.drawRoundRect(rect.makeOutset(10, 10), 18, 18,
                                skia.Paint(Color4f=rgb(self.pal["accent"], 0.6 * self.head_glow), AntiAlias=True,
                                           MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 14)))
            sh = skia.GradientShader.MakeLinear([(-hh / 2, 0), (hh / 2, 0)],
                                                [rgb([min(1, v * 1.5) for v in metal]).toColor(),
                                                 rgb([v * 0.6 for v in metal]).toColor()])
            c.drawRoundRect(rect, 12, 12, skia.Paint(Shader=sh, AntiAlias=True))
            c.drawRoundRect(rect, 12, 12, skia.Paint(Color4f=rgb((1, 1, 1), 0.9), AntiAlias=True,
                                                     Style=skia.Paint.kStroke_Style, StrokeWidth=4))
            for yy in (-hw / 4, hw / 4):  # bandas
                c.drawLine(-hh / 2 + 6, yy, hh / 2 - 6, yy,
                           skia.Paint(Color4f=rgb((0, 0, 0), 0.25), StrokeWidth=5, AntiAlias=True))
            c.restore()
        c.drawCircle(0, 0, 26, skia.Paint(Color4f=rgb((0.92, 0.93, 0.97)), AntiAlias=True))
        c.drawCircle(0, 0, 11, skia.Paint(Color4f=rgb(self.pal["accent"]), AntiAlias=True))
        c.restore()

    def draw_hud(self, c):
        L, acc = self.L, self.pal["accent"]
        # hook (frame 1): pregunta grande
        draw_text(c, L["hook1"], W / 2, 150, 84, (1, 1, 1), stroke=14)
        draw_text(c, L["hook2"], W / 2, 245, 76, acc, stroke=14)
        if self.t < 3.0:
            a = 1.0 if self.t < 2.5 else (3.0 - self.t) / 0.5
            draw_text(c, L["pick"], W / 2, 318, 46, (1, 1, 1), stroke=8, alpha=a)
        else:
            draw_text(c, L["rule"].format(n=self.g["mult"]), W / 2, 318, 46, (1, 1, 1), stroke=8)
        # marcador: quién va ganando
        self.draw_scoreboard(c, 360)
        # contador total + barra de llenado
        total = sum(self.counts)
        y0 = self.cy + self.R + 120
        draw_text(c, f"{total:,} / {self.capacity:,}", W / 2, y0, 86, (1, 1, 1), stroke=12)
        frac = min(1.0, total / self.capacity)
        bx, bw, by = 150, W - 300, y0 + 40
        c.drawRoundRect(skia.Rect(bx, by, bx + bw, by + 26), 13, 13, skia.Paint(Color4f=rgb((1, 1, 1), 0.15), AntiAlias=True))
        x = bx
        for i, n in enumerate(self.counts):   # barra segmentada por equipo
            w = bw * frac * n / max(1, total)
            c.drawRect(skia.Rect(x, by, x + w, by + 26), skia.Paint(Color4f=rgb(self.chars[i].color), AntiAlias=True))
            x += w
        if self.done_at is None or self.t - self.done_at < 3.0:
            draw_text(c, f"{int(frac * 100)}%", W / 2, by + 90, 50, acc, stroke=8)

        if self.near_miss_shown > 0:
            pulse = 1 + 0.08 * math.sin(self.t * 30)
            draw_text(c, L["close"], W / 2, self.cy - self.R - 40, 70 * pulse, (1, 0.3, 0.3), stroke=12)
        if self.done_at is not None:
            dt = self.t - self.done_at
            k = min(1.0, dt / 0.25)
            w = self.chars[self.winner]
            draw_text(c, L["full"], W / 2, self.cy - 40, 190 * (0.6 + 0.4 * k), acc, stroke=22, glow=18)
            if dt > 0.8:
                a = min(0.55, (dt - 0.8) * 2)
                c.drawCircle(self.cx, self.cy, self.R, skia.Paint(Color4f=rgb((0, 0, 0), a), AntiAlias=True))
                draw_text(c, L["full"], W / 2, self.cy - 40, 190, acc, stroke=22, glow=18)
                img, half = w.sprite(110)
                c.drawImage(img, W / 2 - half, self.cy + 10)
                draw_text(c, f"{w.name} {L['wins']}", W / 2, self.cy + 300, 96, w.color, stroke=16, glow=12)
            if dt > 3.0:
                draw_text(c, L["cta1"], W / 2, H - 140, 62, (1, 1, 1), stroke=10)
                draw_text(c, L["cta2"] + "  >>", W / 2, H - 66, 54, acc, stroke=10)

    def draw_scoreboard(self, c, y):
        n = len(self.chars)
        total = max(1, sum(self.counts))
        lead = max(range(n), key=lambda i: self.counts[i])
        colw = (W - 80) / n
        for i, ch in enumerate(self.chars):
            x = 40 + colw * i + colw / 2
            big = i == lead
            r = 44 if big else 36
            if big:
                pulse = 1 + 0.15 * self.lead_flash
                c.drawRoundRect(skia.Rect(x - colw / 2 + 8, y - 8, x + colw / 2 - 8, y + 190), 26, 26,
                                skia.Paint(Color4f=rgb(ch.color, 0.18 + 0.25 * self.lead_flash), AntiAlias=True))
                c.drawRoundRect(skia.Rect(x - colw / 2 + 8, y - 8, x + colw / 2 - 8, y + 190), 26, 26,
                                skia.Paint(Color4f=rgb(ch.color, 0.9), AntiAlias=True, Style=skia.Paint.kStroke_Style,
                                           StrokeWidth=4 * pulse))
            img, half = ch.sprite(r)
            c.drawImage(img, x - half, y + 48 - half)
            draw_text(c, ch.name, x, y + 128, 38, ch.color, stroke=7, max_w=colw - 24)
            draw_text(c, f"{self.counts[i]}", x, y + 178, 44, (1, 1, 1), stroke=8, max_w=colw - 24)
