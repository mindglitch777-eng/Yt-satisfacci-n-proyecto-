"""Core: física (pymunk) + render (cairo) + audio procedural + encode (ffmpeg).
Cada formato hereda de BaseSim y solo define mecánica + HUD."""
import math, random, subprocess, os, wave
import numpy as np, cairo, pymunk

W, H, FPS = 1080, 1920, 30
CX, CY = W / 2, H / 2 + 40
BALL_CT, WALL_CT, HIT_CT = 1, 2, 3


def hsv(h, s=0.85, v=1.0):
    i = int(h * 6) % 6; f = h * 6 - int(h * 6)
    p, q, t = v * (1 - s), v * (1 - f * s), v * (1 - (1 - f) * s)
    return [(v, t, p), (q, v, p), (p, v, t), (p, q, v), (t, p, v), (v, p, q)][i]


class Audio:
    """Sonido 100% sintetizado: sin copyright, cero dependencias. Pitch sube con la tensión."""
    SR = 44100

    def __init__(self, seconds, rng):
        self.buf = np.zeros(int(self.SR * (seconds + 3)), np.float32)
        self.rng = rng
        self.scale = rng.choice([[0, 2, 4, 7, 9], [0, 3, 5, 7, 10], [0, 2, 4, 5, 7, 9, 11]])
        self.base = rng.choice([220, 247, 262, 294])
        self.timbre = rng.choice(["pluck", "marimba", "glass"])

    def note(self, t, step, vol=0.25, dur=0.18):
        oct_, deg = divmod(step, len(self.scale))
        f = self.base * 2 ** (oct_ + self.scale[deg] / 12)
        n = int(self.SR * dur); x = np.arange(n) / self.SR
        if self.timbre == "pluck":
            w = np.sin(2 * np.pi * f * x) * np.exp(-x * 22)
        elif self.timbre == "marimba":
            w = (np.sin(2 * np.pi * f * x) + .3 * np.sin(2 * np.pi * f * 4 * x) * np.exp(-x * 60)) * np.exp(-x * 14)
        else:
            w = (np.sin(2 * np.pi * f * x) + .5 * np.sin(2 * np.pi * f * 2.76 * x)) * np.exp(-x * 9)
        i = int(t * self.SR); self.buf[i:i + n] += vol * w[: len(self.buf) - i]

    def pop(self, t, vol=0.15):
        n = int(self.SR * .05); x = np.arange(n) / self.SR
        w = np.sin(2 * np.pi * (900 - 6000 * x) * x) * np.exp(-x * 80)
        i = int(t * self.SR); self.buf[i:i + n] += vol * w

    def boom(self, t):
        n = int(self.SR * 1.2); x = np.arange(n) / self.SR
        w = (np.sin(2 * np.pi * 55 * x) + .4 * np.random.randn(n) * np.exp(-x * 8)) * np.exp(-x * 3)
        i = int(t * self.SR); self.buf[i:i + n] += .6 * w[: len(self.buf) - i]

    def save(self, path):
        b = np.tanh(self.buf * 1.2)  # soft-clip: miles de eventos sin saturar feo
        with wave.open(path, "wb") as f:
            f.setnchannels(1); f.setsampwidth(2); f.setframerate(self.SR)
            f.writeframes((b * 32000).astype(np.int16).tobytes())


class BaseSim:
    DURATION = 60
    CONTAIN = True  # anti-fuga: ninguna bola atraviesa el aro (tunneling con miles de bolas)
    def __init__(self, cfg):
        self.cfg, self.rng = cfg, random.Random(cfg["seed"])
        self.space = pymunk.Space(); self.space.gravity = (0, cfg.get("gravity", 900))
        self.balls, self.t, self.frame, self.done_at = [], 0.0, 0, None
        self.audio = Audio(self.DURATION, self.rng)
        self.particles = []
        self.R = cfg.get("arena_r", 470)
        self.ball_r = cfg.get("ball_r", 9)
        self.capacity = int(.80 * (self.R / self.ball_r) ** 2)
        self.pal = cfg["palette"]
        self.setup()

    # ---------- helpers físicos ----------
    def ring(self, r, gap_deg=0, gap_at=0, segs=96, body=None, elasticity=1.0):
        body = body or self.space.static_body
        shapes = []
        for i in range(segs):
            a0, a1 = 2 * math.pi * i / segs, 2 * math.pi * (i + 1) / segs
            mid = math.degrees((a0 + a1) / 2 - gap_at) % 360
            if gap_deg and (mid < gap_deg / 2 or mid > 360 - gap_deg / 2):
                continue
            s = pymunk.Segment(body, (r * math.cos(a0), r * math.sin(a0)), (r * math.cos(a1), r * math.sin(a1)), 4)
            s.elasticity, s.friction, s.collision_type = elasticity, .2, WALL_CT
            shapes.append(s)
        self.space.add(*shapes)
        return shapes

    def add_ball(self, x, y, vx=0, vy=0, color=None):
        b = pymunk.Body(1, pymunk.moment_for_circle(1, 0, self.ball_r))
        b.position, b.velocity = (x, y), (vx, vy)
        s = pymunk.Circle(b, self.ball_r); s.elasticity, s.friction = self.cfg.get("bounce", .9), .1
        s.collision_type = BALL_CT
        s.color = color or self.rng.choice(self.pal["balls"]); s.cool = 0.0
        self.space.add(b, s); self.balls.append(s)
        return s

    def burst(self, x, y, color, n=6):
        for _ in range(n):
            a, v = self.rng.uniform(0, 6.28), self.rng.uniform(150, 450)
            self.particles.append([x, y, v * math.cos(a), v * math.sin(a), .5, color])

    # ---------- loop ----------
    def step(self):
        dt = 1 / FPS; sub = 3
        for _ in range(sub):
            self.space.step(dt / sub)
        if self.CONTAIN:
            lim = self.R - self.ball_r - 4
            for sh in self.balls:
                p = sh.body.position; d = p.length
                if d > lim:
                    u = p / d; sh.body.position = u * (lim - 1)
                    v = sh.body.velocity; vn = v.dot(u)
                    if vn > 0: sh.body.velocity = v - u * (1.8 * vn)
        self.t += dt; self.frame += 1
        for p in self.particles:
            p[0] += p[2] * dt; p[1] += p[3] * dt; p[4] -= dt
        self.particles = [p for p in self.particles if p[4] > 0]
        # limpieza: bolas que salen del cuadro
        out = [s for s in self.balls if abs(s.body.position.x) > W or abs(s.body.position.y) > H]
        for s in out:
            self.on_exit(s); self.space.remove(s.body, s); self.balls.remove(s)
        self.update()

    # ---------- render ----------
    def draw_base(self, cr):
        bg = self.pal["bg"]
        g = cairo.RadialGradient(CX, CY, 50, CX, CY, H * .7)
        g.add_color_stop_rgb(0, *[min(1, c * 2.2 + .03) for c in bg]); g.add_color_stop_rgb(1, *bg)
        cr.set_source(g); cr.paint()

    def glow_ring(self, cr, r, hue0, width=7, t=0):
        """aro neón arcoíris rotando — la firma visual del nicho"""
        n = 120
        for i in range(n):
            a0, a1 = 2 * math.pi * i / n, 2 * math.pi * (i + 1) / n + .01
            col = hsv((hue0 + i / n + t * .05) % 1)
            for lw, al in ((width * 4, .08), (width * 2, .2), (width, 1)):
                cr.set_source_rgba(*col, al); cr.set_line_width(lw)
                cr.arc(CX, CY, r, a0, a1); cr.stroke()

    def draw_balls(self, cr):
        r = self.ball_r
        for s in self.balls:
            x, y = s.body.position; c = s.color
            cr.set_source_rgb(*c); cr.arc(CX + x, CY + y, r, 0, 6.2832); cr.fill()
            cr.set_source_rgba(1, 1, 1, .45); cr.arc(CX + x - r * .3, CY + y - r * .3, r * .35, 0, 6.2832); cr.fill()
        for x, y, _, _, life, c in self.particles:
            cr.set_source_rgba(*c, max(0, life * 2)); cr.arc(CX + x, CY + y, 4, 0, 6.2832); cr.fill()

    def text(self, cr, s, y, size, color=(1, 1, 1), box=None, x=None):
        cr.select_font_face("DejaVu Sans", 0, 1); cr.set_font_size(size)
        e = cr.text_extents(s); tx = (W - e.width) / 2 - e.x_bearing if x is None else x
        if box:
            cr.set_source_rgb(*box); pad = 22
            cr.rectangle(tx - pad, y + e.y_bearing - pad, e.width + 2 * pad, e.height + 2 * pad); cr.fill()
        cr.set_source_rgba(0, 0, 0, .6); cr.move_to(tx + 4, y + 4); cr.show_text(s)
        cr.set_source_rgb(*color); cr.move_to(tx, y); cr.show_text(s)

    def render(self, out_path, preview_every=0):
        tmp = out_path + ".silent.mp4"
        enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgra",
            "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast",
            "-crf", "20", "-pix_fmt", "yuv420p", tmp], stdin=subprocess.PIPE)
        surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
        total = int(self.DURATION * FPS); hold = int(2.5 * FPS)
        while self.frame < total:
            self.step()
            cr = cairo.Context(surf); self.draw(cr)
            enc.stdin.write(surf.get_data())
            if self.done_at is not None and self.frame - self.done_at * FPS > hold:
                break
            if preview_every and self.frame % preview_every == 0:
                surf.write_to_png(f"{out_path}.f{self.frame}.png")
        enc.stdin.close(); enc.wait()
        wav = out_path + ".wav"; self.audio.save(wav)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", tmp, "-i", wav, "-c:v", "copy", "-c:a", "aac",
                        "-b:a", "160k", "-shortest", out_path], check=True)
        os.remove(tmp); os.remove(wav)
        return {"seconds": round(self.t, 1), "final_count": len(self.balls)}

    # a implementar
    def setup(self): ...
    def update(self): ...
    def draw(self, cr): ...
    def on_exit(self, s): ...


class Pacer:
    """El truco 'invertido': el final NO es azar. Se programa que llegue al clímax
    justo antes del segundo objetivo (p.ej. 'FULL!' a los 57s) y el multiplicador
    se ajusta en vivo para seguir una curva de tensión exponencial."""
    def __init__(self, target_t, cap, curve=2.6):
        self.T, self.cap, self.k = target_t, cap, curve

    def desired(self, t):
        x = min(1, t / self.T)
        return self.cap * (math.exp(self.k * x) - 1) / (math.exp(self.k) - 1)

    def spawn(self, t, count, base):
        d = self.desired(t)
        if count > d * 1.15: return 0
        if count < d * .7: return base + 2
        return base
