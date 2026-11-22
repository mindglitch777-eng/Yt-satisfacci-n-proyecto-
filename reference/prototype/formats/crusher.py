"""CAN 1 BALL FILL IT IN 60 SECONDS? — brazo/martillo giratorio; cada golpe = xN bolas."""
import math, pymunk
from engine.core import BaseSim, Pacer, CX, CY, W, H, HIT_CT, BALL_CT, hsv


class Crusher(BaseSim):
    def setup(self):
        c = self.cfg
        self.ring(self.R)
        self.arm = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
        L = self.R * c["arm_len"]; self.L = L
        self.heads = []; self.space.add(self.arm)
        for k in range(c["heads"]):
            a = 2 * math.pi * k / c["heads"]
            hx, hy = L * math.cos(a), L * math.sin(a)
            hw, hh = c["head_w"], c["head_h"]
            pts = [(-hw / 2, -hh / 2), (hw / 2, -hh / 2), (hw / 2, hh / 2), (-hw / 2, hh / 2)]
            rot = [(hx + px * math.cos(a) - py * math.sin(a), hy + px * math.sin(a) + py * math.cos(a)) for px, py in pts]
            s = pymunk.Poly(self.arm, rot); s.elasticity, s.collision_type = 1.0, HIT_CT
            self.heads.append(rot)
            rod = pymunk.Segment(self.arm, (0, 0), (hx * .8, hy * .8), 5); rod.elasticity = .9
            self.space.add(s, rod)
        self.space.on_collision(BALL_CT, HIT_CT, begin=self.hit)
        self.pacer = Pacer(c["target_t"], self.capacity, c["curve"])
        self.add_ball(0, -self.R * .6, self.rng.uniform(-200, 200), 0)
        self.pops, self.hits, self._pending = [], 0, []

    def hit(self, arb, space, data):
        ball = arb.shapes[0]
        if self.t - ball.cool < .35 or self.done_at is not None:
            return
        ball.cool = self.t
        n = self.pacer.spawn(self.t, len(self.balls), self.cfg["mult"] - 1)
        if n <= 0:
            return
        self._pending.append((ball.body.position, ball.body.velocity, n, ball.color))

    def update(self):
        c = self.cfg
        if c["motion"] == "spin":
            self.arm.angular_velocity = c["speed"] * (1 + .6 * min(1, self.t / 40))
        else:  # péndulo (como el video de 1.2M)
            self.arm.angular_velocity = c["speed"] * 2.2 * math.cos(self.t * c["speed"] * 1.4)
        for pos, vel, n, col in self._pending:
            for i in range(n):
                if len(self.balls) >= self.capacity: break
                a = self.rng.uniform(0, 6.28)
                self.add_ball(pos.x + 6 * math.cos(a), pos.y + 6 * math.sin(a),
                              vel.x * .5 + 300 * math.cos(a), vel.y * .5 + 300 * math.sin(a), col)
            self.burst(pos.x, pos.y, col, 5)
            self.pops.append([pos.x, pos.y, f"+{n}", .7])
            self.hits += 1
            step = int(len(self.balls) / self.capacity * 14)  # pitch sube con el llenado
            self.audio.note(self.t, step + (self.hits % 3), vol=.22)
        self._pending = []
        if len(self.balls) % 7 == 0: self.audio.pop(self.t, .05)
        if self.done_at is None and len(self.balls) >= self.capacity * .97:
            self.done_at = self.t; self.audio.boom(self.t)
        for p in self.pops: p[3] -= 1 / 30
        self.pops = [p for p in self.pops if p[3] > 0]

    def draw(self, cr):
        self.draw_base(cr)
        self.glow_ring(cr, self.R + 8, self.cfg["hue"], t=self.t)
        self.draw_balls(cr)
        a = self.arm.angle
        cr.save(); cr.translate(CX, CY); cr.rotate(a)
        cr.set_source_rgb(.75, .75, .8); cr.set_line_width(10)
        for (pts) in self.heads:
            hx = sum(p[0] for p in pts) / 4; hy = sum(p[1] for p in pts) / 4
            cr.move_to(0, 0); cr.line_to(hx, hy); cr.stroke()
        for pts in self.heads:
            cr.move_to(*pts[0]); [cr.line_to(*p) for p in pts[1:]]; cr.close_path()
            cr.set_source_rgb(*self.pal["hammer"]); cr.fill_preserve()
            cr.set_source_rgb(1, 1, 1); cr.set_line_width(3); cr.stroke()
        cr.arc(0, 0, 18, 0, 6.3); cr.set_source_rgb(.9, .9, .95); cr.fill()
        cr.restore()
        for x, y, s, life in self.pops:
            cr.select_font_face("DejaVu Sans", 0, 1); cr.set_font_size(40)
            cr.set_source_rgba(1, 1, 1, min(1, life * 2)); cr.move_to(CX + x, CY + y - (0.7 - life) * 80); cr.show_text(s)
        # HUD
        self.text(cr, self.cfg["title_top"], 250, 62, (1, 1, 1))
        self.text(cr, self.cfg["title_bot"], 335, 66, self.pal["accent"])
        n = len(self.balls)
        self.text(cr, f"{n:,} BALLS", CY + self.R + 140, 92)
        frac = min(1, n / self.capacity)
        cr.set_source_rgba(1, 1, 1, .15); cr.rectangle(190, CY + self.R + 180, 700, 16); cr.fill()
        cr.set_source_rgb(*self.pal["accent"]); cr.rectangle(190, CY + self.R + 180, 700 * frac, 16); cr.fill()
        if self.done_at is not None:
            self.text(cr, "FULL!", CY + 30, 170, self.pal["accent"], box=(0, 0, 0))
