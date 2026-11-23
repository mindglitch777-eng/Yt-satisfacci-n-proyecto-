"""PUNCH FILL — movimiento según reference/formats/punch/MEDIDAS.md (medido con tools/motion, no supuesto).

Las 6 leyes, tal como están implementadas acá:
1. Sin gravedad, amortiguación alta: las bolas se mueven solo porque las empujan los brazos o salen de un golpe,
   y frenan en ~0.5 s donde quedaron (escoba, no pecera).
2. Los DOS brazos se mueven en tijera: se abren alrededor del objetivo y se cierran uno contra el otro
   (velocidades opuestas), aceleran fuerte y frenan en seco; entre golpes se reubican abriéndose hasta 180°.
3. El golpe apunta a la bola / a una porción de la masa.
4. Ritardando: intervalo entre golpes 0.7 s al principio → 1.3 s al final; guantes juntos ~0.2 s.
5. Lo atrapado en la cuña se duplica. La cuña tiene capacidad fija → exponencial al principio, lineal después.
   Las nacidas (y las atrapadas) toman un color nuevo.
6. Las bolas se achican a medida que hay más: cada una nace con el radio que le toca al conteo del momento.

Las varillas y guantes son paredes. Como a 400-650°/s el guante recorre más que una bola por subpaso,
el empuje se resuelve geométricamente (lo que la varilla barrió en el frame queda delante de ella),
y pymunk resuelve el resto (bola contra bola, aro).
"""
import math
import numpy as np
import pymunk
import skia

from engine.sim import Sim
from engine.gfx import W, H, rgb, draw_text, text_width
from characters import get as get_char

BALL = 4
TAU = 2 * math.pi

TXT = {
    "en": {"t1": "CAN 1 BALL REFILL IT", "t2": "IN 60 SECONDS?", "balls": "BALLS", "full": "FULL!",
           "almost": "IT GETS THIS FULL...", "taking": "IS TAKING OVER", "wins": "WINS!",
           "cta1": "WHICH BRAINROT WINS NEXT?", "cta2": "SUBSCRIBE FOR ROUND {n}"},
    "es": {"t1": "¿PUEDE 1 BOLA LLENARLO", "t2": "EN 60 SEGUNDOS?", "balls": "BOLAS", "full": "¡LLENO!",
           "almost": "SE LLENA ASÍ...", "taking": "VA GANANDO", "wins": "¡GANA!",
           "cta1": "¿QUÉ BRAINROT GANA LA PRÓXIMA?", "cta2": "SUSCRIBITE PARA LA RONDA {n}"},
}


def wrap(a):
    return (a + math.pi) % TAU - math.pi


def ease_open(u):
    """péndulo: después del choque rebotan rápido hacia afuera y se frenan suave arriba."""
    u = min(1.0, max(0.0, u))
    return math.sin(math.pi * u / 2)


def ease_close(u):
    """cierre: sale suave desde la apertura y va ganando velocidad hasta que los martillos chocan."""
    u = min(1.0, max(0.0, u))
    return 1 - math.cos(math.pi * u / 2)


class Punch(Sim):
    SUBSTEPS = 3

    def setup(self):
        g = self.g
        self.L = TXT[g.get("lang", "en")]
        self.cx, self.cy, self.R = W / 2, 905, 455
        self.space.gravity = (0, g.get("gravity", 160))   # ley 1: muy leve (terminal ≈ 57 px/s con este damping)
        self.space.damping = g.get("damping", 0.06)  # queda 6% de la velocidad tras 1 s → frenan en ~0.5 s
        self.space.iterations = 8
        self.space.use_spatial_hash(14, 12000)
        segs = 120
        for i in range(segs):
            a0, a1 = TAU * i / segs, TAU * (i + 1) / segs
            rr = self.R + 6
            s = pymunk.Segment(self.space.static_body, (self.cx + rr * math.cos(a0), self.cy + rr * math.sin(a0)),
                               (self.cx + rr * math.cos(a1), self.cy + rr * math.sin(a1)), 6)
            s.elasticity, s.friction = 0.3, 0.6
            self.space.add(s)
        # brazos (dibujo + empuje geométrico)
        self.hw, self.hh = g["head_w"], g["head_h"]
        self.arm_len = self.R - self.hh / 2 - 6
        self.rod_w = 7
        self.gap = 2 * math.atan2(self.hw / 2 + 3, self.arm_len)   # ángulo con los guantes tocándose
        self.chars = [get_char(k) for k in g["chars"]]
        self.cur = 0
        # brazos sólidos en la física (bloquean siempre, también quietos)
        self.arm_bodies = []
        L, hw, hh = self.arm_len, self.hw, self.hh
        for k in range(2):
            b = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
            b.position = (self.cx, self.cy)
            rod = pymunk.Segment(b, (16, 0), (L - hh / 2, 0), self.rod_w)
            head = pymunk.Poly(b, [(L - hh / 2, -hw / 2), (L + hh / 2, -hw / 2), (L + hh / 2, hw / 2),
                                   (L - hh / 2, hw / 2)], radius=2)
            for sh in (rod, head):
                sh.elasticity, sh.friction = 0.1, 0.5
            self.space.add(b, rod, head)
            self.arm_bodies.append(b)
        hub = pymunk.Circle(self.space.static_body, 17, (self.cx, self.cy))
        self.space.add(hub)
        self.bodies, self.col, self.rad = [], [], []
        # ley 6: r/R medido ≈ 0.0765 con 1 bola. El medidor ve el núcleo saturado (≈0.72 r real).
        self.r0 = g.get("r_first", 0.106) * self.R
        self.r_exp = g.get("r_exp", 0.30)
        self.r_min = g.get("r_min", 5.2)
        # ciclo
        # índice 0 = martillo DERECHO (ángulo en -90°..90°), índice 1 = IZQUIERDO (90°..270°), en espejo.
        # La primera bola está arriba → el primer golpe es arriba.
        self.side = -1                                   # -1 = chocan arriba, +1 = chocan abajo
        self.target = -math.pi / 2
        a0 = math.radians(55)
        self.ang = [-math.pi / 2 + self.gap / 2 + a0, 1.5 * math.pi - self.gap / 2 - a0]
        self.prev_ang = list(self.ang)
        for b, a in zip(self.arm_bodies, self.ang):
            b.angle = a
        self.cyc_t0, self.phase = 0.0, "close"
        self.close_from = list(self.ang)
        self.close_to = self._closed(-1, 0.0)
        self.cyc = dict(close_T=0.3, hold=0.1)
        self.mult_seq = g.get("mult_seq", [2, 3, 4, 5])   # ×2, ×3, ×4, ×5 y después se queda en el último
        self.pops, self.flashes = [], []
        self.last_voice = -9
        self.round = g.get("round", 2)
        self.winner = 0
        self.claps = 0
        self.mult_i = 0
        # la primera bola flota arriba (ref: y ≈ -0.53R), ya en movimiento suave
        self._add(self.cx + 0.08 * self.R, self.cy - 0.53 * self.R, 40, 0, 0, self.r0)

    # ---------- bolas ----------
    def r_for(self, n):
        return max(self.r_min, self.r0 * max(1, n) ** -self.r_exp)

    def _resize_all(self):
        """todas las bolas del MISMO tamaño: cuando hay más, se achican todas juntas."""
        r = self.r_for(len(self.bodies))
        if self.rad and abs(self.rad[0] - r) < 0.05:
            return r
        for b in self.bodies:
            for sh in b.shapes:
                sh.unsafe_set_radius(r)
        self.rad = [r] * len(self.bodies)
        return r

    def _add(self, x, y, vx, vy, col, r):
        b = pymunk.Body(1, pymunk.moment_for_circle(1, 0, r))
        b.position, b.velocity = (x, y), (vx, vy)
        s = pymunk.Circle(b, r)
        s.elasticity, s.friction, s.collision_type = 0.2, 0.7, BALL
        self.space.add(b, s)
        self.bodies.append(b)
        self.col.append(col)
        self.rad.append(r)

    def positions(self):
        return np.array([b.position for b in self.bodies], np.float64).reshape(-1, 2)

    def tension(self):
        return min(1.0, len(self.bodies) / max(1, self.g["capacity"])) ** 1.2

    # ---------- ritmo (ley 4) ----------
    def interval(self):
        g = self.g
        k = min(1.0, self.t / g.get("ritard_t", 36.0))
        return g.get("iv_early", 0.7) + (g.get("iv_late", 1.3) - g.get("iv_early", 0.7)) * k

    # ---------- objetivo (ley 3) ----------
    def _pick_target(self):
        P = self.positions()
        if not len(P):
            return self.target
        # posición prevista al momento del golpe (frenan exponencialmente: tau ≈ -1/ln(damping))
        V = np.array([b.velocity for b in self.bodies], np.float64).reshape(-1, 2)
        tau = -1 / math.log(self.space.damping)
        P = P + V * tau
        phi = np.arctan2(P[:, 1] - self.cy, P[:, 0] - self.cx)
        if len(P) <= 40:
            # pocas bolas: el golpe apunta al centro angular del grupo (todas entran en la cuña)
            return float(math.atan2(np.mean(np.sin(phi)), np.mean(np.cos(phi))))
        # una porción de la masa: el sector (de ~40°) más poblado entre unos candidatos al azar
        h, _ = np.histogram(phi, bins=36, range=(-np.pi, np.pi))
        hs = np.convolve(np.r_[h[-2:], h, h[:2]], np.ones(5), "valid")
        # el golpe RECORRE el círculo: entre sectores con bolas, prefiere los lejos del golpe anterior (60-140°)
        c = math.atan2(math.sin(self.ang[0]) + math.sin(self.ang[1]), math.cos(self.ang[0]) + math.cos(self.ang[1]))
        best, best_s = 0, -1.0
        for i in range(36):
            a = -np.pi + (i + 0.5) * TAU / 36
            dist = abs(math.degrees(wrap(a - c)))
            far = 0.25 + min(1.0, dist / 70.0) * (1.0 if dist < 140 else 0.7)
            s = (hs[i] / max(1, hs.max())) * far * (0.6 + 0.8 * self.rng.random())
            if hs[i] > 0 and s > best_s:
                best, best_s = i, s
        return -np.pi + (best + 0.5) * TAU / 36

    def _want(self, t):
        """curva de llenado medida en ref05 (~3% a los 10 s); lleno hacia el seg ~48."""
        g = self.g
        return g["capacity"] * min(1.0, max(0.0, t) / g.get("target_t", 48.0)) ** g.get("curve", 2.1)

    def _closed(self, side, o):
        """ángulos (derecho, izquierdo) con los guantes juntos arriba (side=-1) o abajo (+1), corridos o rad."""
        g2 = self.gap / 2
        return [side * (math.pi / 2 - g2) + o, math.pi - side * (math.pi / 2 - g2) + o]

    def _opened(self, side, amp, o):
        """abiertos: cada martillo a 'amp' de su punto de choque, el derecho a la derecha y el izquierdo a la izquierda."""
        return [side * (math.pi / 2 - amp) + o, math.pi - side * (math.pi / 2 - amp) + o]

    def _new_cycle(self):
        """martillo DERECHO e IZQUIERDO: se abren hacia sus costados y vuelven uno contra el otro.
        Chocan abajo o arriba (donde haya más bolas); lo que quedó en el espacio que barren se multiplica."""
        I = self.interval() - 2.5 * self.dt     # los cambios de fase caen en bordes de frame
        late = min(1.0, self.t / 36.0)
        P = self.positions()
        if len(P):
            below = float(np.mean(P[:, 1] > self.cy))
            more = 1 if below >= 0.5 else -1
            n = len(P)
            if n <= 40:
                side = more                                   # pocas: van a buscarlas
            else:
                # Pacer: atrasado → choca donde hay MÁS bolas; adelantado → donde hay MENOS (la regla ×N no cambia)
                ahead = n > self._want(self.t + I)
                side = -more if ahead else more
                if self.rng.random() < 0.15:
                    side = -side
        else:
            side = self.side
        # amplitud de cada martillo (recorrido): golpes rápidos = cortos, lentos = hasta los costados
        amp = math.radians((70 + 20 * late) * self.rng.uniform(0.93, 1.07))   # se abren hacia los costados
        o_close = math.radians(self.rng.uniform(-10, 10))      # el choque no siempre cae en el mismo punto
        o_open = math.radians(self.rng.uniform(-8, 8))
        self.lag = 0.0                  # el izquierdo arranca apenas después (manos reales)
        # recorrido continuo y parejo (sin quedarse quietos esperando): se abren y vuelven a chocar
        hold = 0.08
        open_T = (I - hold) * 0.45
        close_T = (I - hold) * 0.55
        self.cyc = dict(open_T=open_T, close_T=close_T, hold=hold, wait=0.0)
        self.open_from = list(self.ang)
        self.open_to = self._opened(side, amp, o_open)
        self.close_to = self._closed(side, o_close)
        self.side = side
        self.target = side * math.pi / 2 + o_close
        self.phase, self.cyc_t0 = "open", self.t

    # ---------- golpe (ley 5) ----------
    def _clap(self):
        self.claps += 1
        P = self.positions()
        hx = self.cx + self.arm_len * math.cos(self.target)
        hy = self.cy + self.arm_len * math.sin(self.target)
        pan = self.pan(hx)
        ten = self.tension()
        self.flashes.append([hx, hy, 0.0])
        self.cam.kick(0.12 + 0.2 * ten)
        k = 0
        if len(P) and self.done_at is None:
            dx, dy = P[:, 0] - self.cx, P[:, 1] - self.cy
            rad = np.hypot(dx, dy)
            phi = np.arctan2(dy, dx)
            off = np.abs((phi - self.target + np.pi) % TAU - np.pi)
            margin = (np.array(self.rad) * 1.2 + self.hw * 0.2) / np.maximum(rad, 40)
            caught = np.nonzero((off < self.gap / 2 + margin) & (rad > 30))[0]
            # capacidad fija de la cuña: las que entran en el triángulo entre los guantes
            r_new = self.r_for(len(P))
            wedge_area = 0.5 * (self.gap + 0.1) * (self.R ** 2 - 40 ** 2)
            cap = max(1, int(wedge_area * self.g.get("wedge_fill", 0.22) / (math.pi * r_new ** 2)))
            if len(caught) > cap:
                caught = caught[np.argsort(off[caught])][:cap]
            k = len(caught)
            mult = self.mult_seq[min(self.mult_i, len(self.mult_seq) - 1)] if k else 1
            room = self.g["capacity"] - len(P)
            n_new = max(0, min(k * (mult - 1), room))
            if k:
                self.mult_i += 1
            if k:
                self.cur = (self.cur + 1) % len(self.chars)
                for i in caught:
                    self.col[i] = self.cur
                tx, ty = -math.sin(self.target), math.cos(self.target)
                ux, uy = math.cos(self.target), math.sin(self.target)
                # las nuevas nacen DENTRO de la cuña: junto a cada atrapada, un paso hacia el pivote
                # (así el brazo que se abre no las arrastra) y salen despacio por la boca de la cuña
                spd = min(1.0, 0.2 + len(P) / 200)
                for j in range(n_new):
                    i = caught[j % k]
                    x, y = P[i]
                    step = r_new * 2.05 * (1 + j // k)
                    jit = self.rng.uniform(-0.6, 0.6) * r_new
                    nx, ny = x - ux * step + tx * jit, y - uy * step + ty * jit
                    if math.hypot(nx - self.cx, ny - self.cy) < 40:
                        nx, ny = x + tx * jit * 2, y + ty * jit * 2
                    v = self.rng.uniform(40, 160) * spd
                    self._add(nx, ny, -ux * v + tx * self.rng.uniform(-30, 30) * spd,
                              -uy * v + ty * self.rng.uniform(-30, 30) * spd, self.cur, r_new)
                for i in caught:
                    self.bodies[i].velocity = (self.bodies[i].velocity.x * 0.2, self.bodies[i].velocity.y * 0.2)
                # al abrirse los brazos, lo del golpe sale DISPARADO cruzando el círculo (los brazos lo persiguen)

                # el "+N" va en la cuña cerca del pivote (< 0.45R): lejos de los guantes, legible
                self._resize_all()                      # todas del mismo tamaño
                lx = self.cx + 0.3 * self.R * math.cos(self.target)
                ly = self.cy + 0.3 * self.R * math.sin(self.target)
                lab = f"×{mult}" if n_new == k * (mult - 1) else f"+{n_new}"
                self.pops.append([lx, ly, lab, 0.0])
                self.particles.burst(hx, hy, self.chars[self.cur].color, n=14, speed=600, size=3, life=0.35)
        e = min(1.0, 0.4 + k / 120)
        self.audio.hit(self.t, e, "punch", pan, ten)
        if k:
            self.audio.hit(self.t + 0.002, e, "squish", pan, ten)
            for i in range(int(min(8, 2 + 1.5 * math.log2(1 + k)))):
                self.audio.event(self.t + 0.04 + i * 0.03, "pop", 0.9 + 0.5 * ten + 0.07 * i)
            if self.t - self.last_voice > self.g.get("voice_gap", 2.6):
                self.audio.voice(self.t + 0.08, self.chars[self.cur].key, "short", pan)
                self.last_voice = self.t
        if len(self.bodies) >= self.g["capacity"] and self.done_at is None:
            self._climax()

    def _climax(self):
        self.done_at = self.t
        self.winner = self.cur
        self.audio.set_climax(self.t)
        self.audio.event(self.t - 0.3, "riser", 1.0)
        self.audio.event(self.t, "boom", 1.0)
        self.audio.event(self.t + 0.05, "chord", 1.0)
        self.audio.voice(self.t + 0.9, self.chars[self.cur].key, "full", 0.0, 1.2)
        self.cam.kick(0.8)

    # ---------- movimiento de los brazos (leyes 2 y 4) ----------
    def _arm_targets(self):
        c = self.cyc
        u_t = self.t - self.cyc_t0
        if self.phase == "open":
            if u_t >= c["open_T"]:
                self.phase, self.cyc_t0 = "wait", self.t
                self.ang = list(self.open_to)
                return list(self.open_to)
            lag = getattr(self, "lag", 0.0)
            es = [ease_open(u_t / c["open_T"]), ease_open((u_t - lag) / max(1e-3, c["open_T"] - lag))]
            return [a + (b - a) * e for a, b, e in zip(self.open_from, self.open_to, es)]
        if self.phase == "wait":
            if u_t >= c["wait"]:
                self.phase, self.cyc_t0 = "close", self.t
                self.close_from = list(self.ang)
            return list(self.ang)
        if self.phase == "close":
            to = self.close_to
            if u_t >= c["close_T"]:
                self.phase, self.cyc_t0 = "hold", self.t
                self._clap()
                return to
            e = ease_close(u_t / c["close_T"])
            # desplazamiento exacto (sin "camino corto"): cada brazo vuelve por donde abrió → siempre tijera
            return [a + (b - a) * e for a, b in zip(self.close_from, to)]
        # hold: guantes juntos
        if u_t >= c["hold"] and self.done_at is None:
            self._new_cycle()
        return list(self.ang)

    def _sweep(self, P0, new_ang):
        """empuje geométrico: lo que la varilla barrió en este frame queda delante de ella."""
        if not len(P0):
            return
        P1 = self.positions()
        dx0, dy0 = P0[:, 0] - self.cx, P0[:, 1] - self.cy
        rad0 = np.hypot(dx0, dy0)
        phi0 = np.arctan2(dy0, dx0)
        dx1, dy1 = P1[:, 0] - self.cx, P1[:, 1] - self.cy
        rad1 = np.hypot(dx1, dy1)
        phi1 = np.arctan2(dy1, dx1)
        rr = np.array(self.rad)
        reach = self.arm_len + self.hh / 2
        for k in range(2):
            d = wrap(new_ang[k] - self.prev_ang[k])
            if abs(d) < 1e-4:
                continue
            sgn = 1.0 if d > 0 else -1.0
            # medio-ancho angular de la varilla/guante + la bola
            wid = (self.rod_w + rr) / np.maximum(rad0, 20)
            wid = np.where(rad0 > self.arm_len - self.hh / 2, (self.hw / 2 + rr) / np.maximum(rad0, 20), wid)
            rel0 = ((phi0 - self.prev_ang[k]) * sgn + np.pi) % TAU - np.pi   # posición respecto de la varilla vieja
            # solo lo que estaba DELANTE de la varilla (centro del lado que avanza); lo de atrás no se arrastra
            swept = (rel0 > 0) & (rel0 < abs(d) + wid) & (rad0 > 18) & (rad0 < reach + rr)
            if not swept.any():
                continue
            wid1 = (self.rod_w + rr) / np.maximum(rad1, 20)
            wid1 = np.where(rad1 > self.arm_len - self.hh / 2, (self.hw / 2 + rr) / np.maximum(rad1, 20), wid1)
            rel1 = ((phi1 - new_ang[k]) * sgn + np.pi) % TAU - np.pi
            bad = np.nonzero(swept & (rel1 < wid1))[0]
            w_ang = d / self.dt
            closing = self.phase in ("close", "hold")
            for i in bad:
                ra = min(max(rad1[i], 20.0), self.R - rr[i])
                push = wid1[i] + 0.004
                if closing:
                    # nunca más allá de la línea media: lo apretado queda atrapado en la cuña
                    push = min(push, abs(wrap(self.target - new_ang[k])))
                a = new_ang[k] + sgn * push
                b = self.bodies[i]
                b.position = (self.cx + ra * math.cos(a), self.cy + ra * math.sin(a))
                # sale con la velocidad tangencial del brazo (lo arrastra)
                vt = w_ang * ra
                vt = max(-320.0, min(320.0, vt))          # no hereda toda la velocidad del guante
                b.velocity = (-math.sin(a) * vt, math.cos(a) * vt)

    def step(self):
        # el loop base corre la física; acá se mueven los brazos y se corrige el empuje
        new_ang = self._arm_targets() if self.done_at is None else list(self.ang)
        P0 = self.positions() if self.bodies else np.zeros((0, 2))
        self.prev_ang = list(self.ang)
        self.ang = new_ang
        for b, a0, a1 in zip(self.arm_bodies, self.prev_ang, new_ang):
            b.angle = a0
            b.angular_velocity = (a1 - a0) / self.dt
        super().step()
        for b, a1 in zip(self.arm_bodies, new_ang):
            b.angle = a1
        self._sweep(P0, new_ang)
        self._contain()

    def update(self):
        dt = self.dt
        for p in self.pops:
            p[3] += dt
        self.pops = [p for p in self.pops if p[3] < 1.0]
        for f in self.flashes:
            f[2] += dt
        self.flashes = [f for f in self.flashes if f[2] < 0.3]
        if self.frame % 6 == 0:
            self.audio.set_tension(self.t, self.tension())
        if self.frame % 2 == 0:
            w = max(abs(wrap(a - b)) for a, b in zip(self.ang, self.prev_ang)) / dt
            mass = min(1.0, len(self.bodies) / 600)
            self.audio.rumble(self.t, min(1.0, 0.1 + 0.1 * w * (0.2 + 0.8 * mass)))
        if self.done_at is not None and self.end_at is None and self.t > self.done_at + 5.0:
            self.end_at = self.t

    def _contain(self):
        if not self.bodies:
            return
        P = self.positions()
        rad = np.hypot(P[:, 0] - self.cx, P[:, 1] - self.cy)
        rr = np.array(self.rad)
        lim = self.R - rr
        for i in np.nonzero(rad > lim)[0]:
            b = self.bodies[i]
            ux, uy = (P[i, 0] - self.cx) / rad[i], (P[i, 1] - self.cy) / rad[i]
            b.position = (self.cx + ux * (lim[i] - 0.5), self.cy + uy * (lim[i] - 0.5))
            vx, vy = b.velocity
            vn = vx * ux + vy * uy
            if vn > 0:
                b.velocity = (vx - 1.3 * vn * ux, vy - 1.3 * vn * uy)
                if vn > 120 and self.rng.random() < 0.15:
                    self.audio.hit(self.t, min(1, vn / 600), "clack", self.pan(P[i, 0]), self.tension())

    # ---------- dibujo ----------
    def draw_world(self, c):
        ring = skia.Paint(Color4f=rgb((0.95, 0.95, 0.97), 1.0), AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=8)
        c.drawCircle(self.cx, self.cy, self.R + 6, ring)
        frac = min(1.0, len(self.bodies) / self.g["capacity"])
        if frac > 0:
            arc = skia.Paint(Color4f=rgb(self.pal["accent"]), AntiAlias=True, Style=skia.Paint.kStroke_Style,
                             StrokeWidth=9, StrokeCap=skia.Paint.kRound_Cap)
            rr = self.R + 22
            c.drawArc(skia.Rect(self.cx - rr, self.cy - rr, self.cx + rr, self.cy + rr), -90, 360 * frac, False, arc)
        self.draw_balls(c)
        self.draw_arms(c)
        for x, y, age in self.flashes:
            k = age / 0.3
            c.drawCircle(x, y, 24 + 90 * k, skia.Paint(Color4f=skia.Color4f(1, 1, 1, 0.8 * (1 - k)), AntiAlias=True,
                                                      MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 14)))
        self.particles.draw(c)
        for x, y, s, age in self.pops:
            pop = 1 + 0.35 * max(0, 0.15 - age) / 0.15
            draw_text(c, s, x, y + 20, 62 * pop, (1, 1, 1), stroke=10, alpha=min(1, (1.0 - age) * 3), max_w=360)

    def draw_balls(self, c):
        """esfera sombreada: borde oscuro + núcleo saturado + brillo (como la referencia)."""
        if not self.bodies:
            return
        P = self.positions()
        col = np.array(self.col)
        rr = np.round(np.array(self.rad) * 2) / 2   # agrupar por radio (0.5 px)
        for ci in np.unique(col):
            base = self.chars[ci].color
            dark = [v * 0.22 for v in base]
            light = [min(1, v * 0.55 + 0.5) for v in base]
            for r in np.unique(rr[col == ci]):
                sel = P[(col == ci) & (rr == r)]
                pts = [skia.Point(float(x), float(y)) for x, y in sel]
                c.drawPoints(skia.Canvas.kPoints_PointMode, pts,
                             skia.Paint(Color4f=rgb(dark), AntiAlias=True, StrokeWidth=2 * r, StrokeCap=skia.Paint.kRound_Cap))
                c.drawPoints(skia.Canvas.kPoints_PointMode, pts,
                             skia.Paint(Color4f=rgb(base), AntiAlias=True, StrokeWidth=2 * r * 0.74, StrokeCap=skia.Paint.kRound_Cap))
                hl = [skia.Point(p.fX - r * 0.28, p.fY - r * 0.3) for p in pts]
                c.drawPoints(skia.Canvas.kPoints_PointMode, hl,
                             skia.Paint(Color4f=rgb(light, 0.95), AntiAlias=True, StrokeWidth=max(1.2, r * 0.5),
                                        StrokeCap=skia.Paint.kRound_Cap))

    def draw_arms(self, c):
        L, hw, hh = self.arm_len, self.hw, self.hh
        rod = skia.Paint(Color4f=rgb((0.62, 0.63, 0.67)), AntiAlias=True, StrokeWidth=2 * self.rod_w,
                         StrokeCap=skia.Paint.kRound_Cap)
        rod_hi = skia.Paint(Color4f=rgb((0.9, 0.9, 0.93)), AntiAlias=True, StrokeWidth=5, StrokeCap=skia.Paint.kRound_Cap)
        for a in self.ang:
            c.save(); c.translate(self.cx, self.cy); c.rotate(math.degrees(a))
            c.drawLine(0, 0, L - hh / 2, 0, rod)
            c.drawLine(0, -2, L - hh / 2, -2, rod_hi)
            c.translate(L, 0)
            _glove(c, hw, hh)
            c.restore()
        c.drawCircle(self.cx, self.cy, 18, skia.Paint(Color4f=rgb((0.85, 0.86, 0.9)), AntiAlias=True))
        c.drawCircle(self.cx, self.cy, 18, skia.Paint(Color4f=rgb((0.3, 0.3, 0.35)), AntiAlias=True,
                                                      Style=skia.Paint.kStroke_Style, StrokeWidth=3))
        c.drawCircle(self.cx, self.cy, 6, skia.Paint(Color4f=rgb((0.3, 0.3, 0.35)), AntiAlias=True))

    def draw_hud(self, c):
        L, acc = self.L, self.pal["accent"]
        n = len(self.bodies)
        done = self.done_at is not None
        if done and self.t - self.done_at > 0.3:
            draw_text(c, L["almost"], W / 2, 250, 76, (1, 1, 1), stroke=12)
        else:
            draw_text(c, L["t1"], W / 2, 170, 78, (1, 1, 1), stroke=12)
            draw_text(c, L["t2"], W / 2, 260, 78, acc, stroke=12)
        y = self.cy + self.R + 150
        num = f"{n:,}"
        wn, wb = text_width(num, 112), text_width(L["balls"], 44)
        x0 = W / 2 - (wn + 18 + wb) / 2
        draw_text(c, num, x0, y, 112, (1, 1, 1), align="left", stroke=12)
        draw_text(c, L["balls"], x0 + wn + 18, y, 44, (0.75, 0.75, 0.8), align="left", stroke=8)
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


def _glove(c, hw, hh):
    """guante gris metálico como el de la referencia: cuerpo, puño, pulgar y nudillos."""
    outline = skia.Paint(Color4f=rgb((0.25, 0.25, 0.28)), AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=4)
    sh = skia.GradientShader.MakeLinear([(0, -hw / 2), (0, hw / 2)],
                                        [rgb((0.9, 0.9, 0.92)).toColor(), rgb((0.55, 0.56, 0.6)).toColor()])
    fill = skia.Paint(Shader=sh, AntiAlias=True)
    body = skia.RRect.MakeRectXY(skia.Rect(-hh / 2, -hw / 2, hh * 0.32, hw / 2), 18, 18)
    c.drawRRect(body, fill); c.drawRRect(body, outline)
    cuff = skia.RRect.MakeRectXY(skia.Rect(hh * 0.22, -hw * 0.42, hh / 2, hw * 0.42), 8, 8)
    c.drawRRect(cuff, fill); c.drawRRect(cuff, outline)
    thumb = skia.RRect.MakeRectXY(skia.Rect(-hh * 0.25, hw * 0.28, hh * 0.15, hw * 0.62), 10, 10)
    c.drawRRect(thumb, fill); c.drawRRect(thumb, outline)
    line = skia.Paint(Color4f=rgb((0.38, 0.38, 0.42)), AntiAlias=True, StrokeWidth=3)
    for k in (-0.22, 0.0, 0.22):
        c.drawLine(-hh / 2 + 6, k * hw, -hh * 0.05, k * hw, line)
    c.drawLine(hh * 0.3, -hw * 0.3, hh * 0.3, hw * 0.3, line)
