"""Base de todos los formatos: física, loop de render, encode y mezcla de audio.

Un formato implementa setup / update / draw / events (on_hit, on_wall).
"""
import math, os, random, subprocess, time
import numpy as np
import pymunk
import skia

from engine.gfx import W, H, Frame, Camera, Particles, Popups, background
from audio.engine import AudioEngine

CHIP, WALL, MACHINE = 1, 2, 3


class Chip:
    __slots__ = ("body", "shape", "char", "team", "r", "cool", "born", "flash")


class Sim:
    DURATION = 60.0
    SUBSTEPS = 4

    def __init__(self, genome, fps=60):
        self.g = genome
        self.fps = fps
        self.dt = 1 / fps
        self.rng = random.Random(genome["seed"])
        self.space = pymunk.Space()
        self.space.gravity = (0, genome.get("gravity", 1400))
        self.space.iterations = 12
        self.chips = []
        self.t = 0.0
        self.frame = 0
        self.done_at = None
        self.end_at = None
        self.audio = AudioEngine(self.DURATION, self.rng, genome["scale"], genome["root"],
                                 genome["timbre"], genome["bpm"], fps)
        self.cam = Camera(self.rng)
        self.particles = Particles(self.rng)
        self.popups = Popups()
        self.pal = genome["palette"]
        self.bg = background(self.pal)
        self.space.on_collision(CHIP, MACHINE, begin=self._machine_hit)
        self.space.on_collision(CHIP, WALL, post_solve=self._wall_hit)
        self.space.on_collision(CHIP, CHIP, post_solve=self._chip_hit)
        self._wall_budget = 0
        self.setup()

    # ---------- física ----------
    def add_chip(self, char, team, x, y, vx=0.0, vy=0.0, r=None):
        r = r or self.g["chip_r"] * char.size
        b = pymunk.Body(char.mass, pymunk.moment_for_circle(char.mass, 0, r))
        b.position, b.velocity = (x, y), (vx, vy)
        s = pymunk.Circle(b, r)
        s.elasticity, s.friction, s.collision_type = char.bounce, 0.15, CHIP
        ch = Chip()
        ch.body, ch.shape, ch.char, ch.team, ch.r = b, s, char, team, r
        ch.cool, ch.born, ch.flash = -9.0, self.t, 0.0
        s.chip = ch
        self.space.add(b, s)
        self.chips.append(ch)
        return ch

    def remove_chip(self, ch):
        self.space.remove(ch.body, ch.shape)
        self.chips.remove(ch)

    def ring_walls(self, cx, cy, r, segs=128, thickness=10):
        shapes = []
        for i in range(segs):
            a0, a1 = 2 * math.pi * i / segs, 2 * math.pi * (i + 1) / segs
            # el segmento se coloca por fuera del radio útil
            rr = r + thickness
            s = pymunk.Segment(self.space.static_body, (cx + rr * math.cos(a0), cy + rr * math.sin(a0)),
                               (cx + rr * math.cos(a1), cy + rr * math.sin(a1)), thickness)
            s.elasticity, s.friction, s.collision_type = 1.0, 0.05, WALL
            shapes.append(s)
        self.space.add(*shapes)
        return shapes

    def contain_circle(self, cx, cy, R):
        """anti-tunneling duro: ninguna ficha queda fuera de la arena, pase lo que pase."""
        for ch in self.chips:
            p = ch.body.position
            dx, dy = p.x - cx, p.y - cy
            d = math.hypot(dx, dy)
            lim = R - ch.r
            if d > lim and d > 0:
                ux, uy = dx / d, dy / d
                ch.body.position = (cx + ux * lim, cy + uy * lim)
                v = ch.body.velocity
                vn = v.x * ux + v.y * uy
                if vn > 0:
                    ch.body.velocity = (v.x - ux * 1.9 * vn, v.y - uy * 1.9 * vn)

    def keep_alive(self, vmin=260):
        """las fichas nunca se quedan quietas en el piso (el nicho vive del movimiento)."""
        for ch in self.chips:
            v = ch.body.velocity
            s = v.length
            if s < vmin:
                a = self.rng.uniform(0, 2 * math.pi) if s < 1 else math.atan2(v.y, v.x)
                ch.body.velocity = (vmin * math.cos(a), vmin * math.sin(a) - 120)

    def _machine_hit(self, arb, space, data):
        ch = arb.shapes[0].chip
        if self.done_at is None and self.t - ch.cool > 0.3:
            ch.cool = self.t
            self.on_hit(ch, arb)

    def _wall_hit(self, arb, space, data):
        if arb.is_first_contact and self._wall_budget > 0:
            ch = arb.shapes[0].chip
            e = min(1.0, arb.total_impulse.length / (ch.char.mass * 900))
            if e > 0.08:
                self._wall_budget -= 1
                self.on_wall(ch, e)

    def _chip_hit(self, arb, space, data):
        if arb.is_first_contact and self._wall_budget > 0:
            a = arb.shapes[0].chip
            e = min(1.0, arb.total_impulse.length / (a.char.mass * 1100))
            if e > 0.12:
                self._wall_budget -= 1
                self.audio.hit(self.t, e * 0.6, "click", self.pan(a.body.position.x), self.tension())

    def pan(self, x):
        return max(-1, min(1, (x - W / 2) / (W / 2))) * 0.7

    def tension(self):
        return 0.0

    def step(self):
        self._wall_budget = 24
        h = self.dt / self.SUBSTEPS
        for _ in range(self.SUBSTEPS):
            self.space.step(h)
        self.update()
        self.particles.update(self.dt)
        self.popups.update(self.dt)
        self.cam.update(self.dt)
        for ch in self.chips:
            if ch.flash > 0:
                ch.flash -= self.dt
        self.t += self.dt
        self.frame += 1

    # ---------- render de fichas (sprites horneados + motion blur liviano) ----------
    def draw_chips(self, c):
        p = skia.Paint(AntiAlias=True)
        ghost = skia.Paint()
        ghost.setAlphaf(0.25)
        flash = skia.Paint(Color4f=skia.Color4f(1, 1, 1, 0.6), AntiAlias=True)
        for ch in self.chips:
            img, half = ch.char.sprite(ch.r)
            x, y = ch.body.position
            vx, vy = ch.body.velocity
            sp2 = vx * vx + vy * vy
            age = self.t - ch.born
            if sp2 > 900 ** 2:   # trail solo para las rápidas
                c.drawImage(img, x - vx * self.dt * 0.8 - half, y - vy * self.dt * 0.8 - half, paint=ghost)
            if age < 0.18:       # pop de nacimiento
                k = 0.4 + 0.6 * age / 0.18
                c.save(); c.translate(x, y); c.scale(k, k)
                c.drawImage(img, -half, -half, paint=p)
                c.restore()
            else:
                c.save(); c.translate(x, y); c.rotate(math.degrees(ch.body.angle) * 0.5)
                c.drawImage(img, -half, -half, paint=p)
                c.restore()
            if ch.flash > 0:
                flash.setAlphaf(min(0.7, ch.flash * 4))
                c.drawCircle(x, y, ch.r, flash)

    # ---------- loop principal ----------
    def run(self, out_path, preview_frames=(), max_seconds=None):
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
        silent = out_path + ".v.mp4"
        enc = subprocess.Popen(
            ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}",
             "-r", str(self.fps), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
             "-pix_fmt", "yuv420p", "-movflags", "+faststart", silent], stdin=subprocess.PIPE)
        fr = Frame()
        c = fr.canvas
        first = None
        total = int((max_seconds or 59.5) * self.fps)
        t0 = time.time()
        loop_len = int(0.5 * self.fps)
        n = 0
        while n < total:
            self.step()
            c.save()
            c.drawImage(self.bg, 0, 0)
            self.cam.apply(c)
            self.draw_world(c)
            c.restore()
            self.draw_hud(c)
            if first is None:
                first = fr.buf.copy()
            # loop: los últimos 0.5s se funden con el frame 1 (empalme para el rewatch)
            if self.end_at is not None:
                k = (self.t - self.end_at) * self.fps
                if k >= 0:
                    a = min(1.0, k / loop_len)
                    if a > 0:
                        fr.buf[:] = (fr.buf * (1 - a) + first * a).astype(np.uint8)
                    if k >= loop_len:
                        enc.stdin.write(fr.buf.data)
                        n += 1
                        break
            enc.stdin.write(fr.buf.data)
            if self.frame in preview_frames:
                fr.surface.makeImageSnapshot().save(f"{out_path}.f{self.frame:05d}.png", skia.kPNG)
            n += 1
        enc.stdin.close()
        enc.wait()
        render_s = time.time() - t0
        self.audio.dur = self.t
        wav = self.audio.save(out_path + ".wav")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", silent, "-i", wav, 
                        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart",
                        out_path], check=True)
        os.remove(silent)
        os.remove(wav)
        return {"seconds": round(self.t, 2), "frames": n, "render_s": round(render_s, 1),
                "climax_t": self.done_at, "chips": len(self.chips)}

    # ---------- a implementar por cada formato ----------
    def setup(self): ...
    def update(self): ...
    def draw_world(self, c): ...
    def draw_hud(self, c): ...
    def on_hit(self, ch, arb): ...
    def on_wall(self, ch, e):
        self.audio.hit(self.t, e, ch.char.sound["kind"], self.pan(ch.body.position.x), self.tension())
