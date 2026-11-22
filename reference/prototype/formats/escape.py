"""EVERY ESCAPE = 3 NEW BALLS — aro giratorio con hueco; cada bola que escapa spawnea N."""
import math
from engine.core import BaseSim, Pacer, CX, CY, W, H, hsv
import pymunk


class Escape(BaseSim):
    CONTAIN = False
    def setup(self):
        c = self.cfg
        self.rot = pymunk.Body(body_type=pymunk.Body.KINEMATIC); self.space.add(self.rot)
        self.ring(self.R, gap_deg=c["gap_deg"], gap_at=0, body=self.rot)
        self.pacer = Pacer(c["target_t"], self.capacity, c["curve"])
        self.add_ball(0, 0, self.rng.uniform(-400, 400), -300)
        self.escapes, self.flash = 0, 0

    def update(self):
        c = self.cfg
        self.rot.angular_velocity = c["speed"] * (1 if (self.t // c["flip_every"]) % 2 == 0 else -1)
        lim2 = (self.R + 25) ** 2
        gone = [s for s in self.balls if s.body.position.get_length_sqrd() > lim2]
        for s in gone:
            x, y = s.body.position
            self.space.remove(s.body, s); self.balls.remove(s)
            self.burst(x, y, s.color, 8); self.escapes += 1; self.flash = .25
            if self.done_at is None:
                n = self.pacer.spawn(self.t, len(self.balls), c["mult"]) or 1
                for _ in range(n):
                    if len(self.balls) >= self.capacity: break
                    a = self.rng.uniform(0, 6.28)
                    self.add_ball(30 * math.cos(a), 30 * math.sin(a), 350 * math.cos(a), 350 * math.sin(a))
                self.audio.note(self.t, int(len(self.balls) / self.capacity * 12) + self.escapes % 2, .25)
        self.flash = max(0, self.flash - 1 / 30)
        if self.done_at is None and len(self.balls) >= self.capacity * .9:
            self.done_at = self.t; self.audio.boom(self.t)

    def draw(self, cr):
        self.draw_base(cr)
        a, gap = self.rot.angle, math.radians(self.cfg["gap_deg"])
        n = 140
        for i in range(n):
            a0 = a + gap / 2 + (2 * math.pi - gap) * i / n
            a1 = a + gap / 2 + (2 * math.pi - gap) * (i + 1) / n + .01
            col = hsv((self.cfg["hue"] + i / n) % 1)
            for lw, al in ((30, .08), (15, .2), (8, 1)):
                cr.set_source_rgba(*col, al); cr.set_line_width(lw); cr.arc(CX, CY, self.R, a0, a1); cr.stroke()
        self.draw_balls(cr)
        if self.flash:
            cr.set_source_rgba(1, 1, 1, self.flash * .25); cr.paint()
        self.text(cr, self.cfg["title_top"], 250, 56, (0, 0, 0), box=(1, 1, 1))
        self.text(cr, self.cfg["title_bot"], 345, 62, self.pal["accent"])
        self.text(cr, f"BALLS: {len(self.balls):,}", CY + self.R + 150, 84)
        if self.done_at is not None:
            self.text(cr, "FULL!", CY + 30, 170, self.pal["accent"], box=(0, 0, 0))
