"""Motor de sonido: la mitad del "satisfying".

Capas: impacto (transiente) + tono pentatónico (la nota depende de la velocidad del golpe)
+ cola de reverb. Pitch/densidad suben con la tensión. Silencio de 0.3s antes del clímax y drop.
Limitador de eventos por frame + granular ("lluvia", nunca saturación). Pista base pad+beat con
sidechain. Master con compresor; el normalizado a -14 LUFS lo hace ffmpeg (loudnorm 2 pasadas).
"""
import json, subprocess, wave
import numpy as np
from audio import synth
from audio.synth import SR

VOICES_PER_FRAME = 4      # golpes "completos" por frame; el resto va a la lluvia granular
GRAINS_PER_FRAME = 10


class AudioEngine:
    def __init__(self, duration, rng, scale="major_penta", root=220.0, timbre="marimba", bpm=112, fps=60):
        self.dur = duration
        self.n = int(SR * (duration + 3))
        self.rng = np.random.default_rng(rng.randrange(1 << 30))
        self.scale = synth.SCALES[scale]
        self.root, self.timbre, self.bpm, self.fps = root, timbre, bpm, fps
        self.hits = []      # (t, energy 0..1, kind, pan -1..1, tension 0..1)
        self.sigs = []      # (t, kind, pan, gain)
        self.fx = []        # (t, name, gain)
        self.tension = []   # (t, 0..1) curva para pitch/densidad/bed
        self.climax = None
        self._tones = {}

    # ---------- API para los formatos ----------
    def hit(self, t, energy, kind="click", pan=0.0, tension=0.0):
        if 0 <= t < self.dur + 2.5:
            self.hits.append((t, float(min(1, max(0, energy))), kind, float(pan), float(tension)))

    def signature(self, t, kind, pan=0.0, gain=0.6):
        self.sigs.append((t, kind, pan, gain))

    def event(self, t, name, gain=1.0):
        self.fx.append((t, name, gain))

    def set_tension(self, t, v):
        self.tension.append((t, v))

    def set_climax(self, t):
        self.climax = t

    # ---------- render ----------
    def _note(self, step):
        if step not in self._tones:
            o, d = divmod(step, len(self.scale))
            f = self.root * 2 ** (o + self.scale[d] / 12)
            self._tones[step] = synth.tone(f, self.timbre, 0.55)
        return self._tones[step]

    @staticmethod
    def _add(buf, i, w, gl, gr):
        if i >= len(buf) or i < 0:
            return
        m = min(len(w), len(buf) - i)
        buf[i:i + m, 0] += w[:m] * gl
        buf[i:i + m, 1] += w[:m] * gr

    @staticmethod
    def _pan(p):
        a = (p + 1) * np.pi / 4
        return float(np.cos(a)), float(np.sin(a))

    def _reverb(self, x, decay=1.9):
        n_ir = int(SR * decay)
        tt = np.arange(n_ir) / SR
        out = np.zeros_like(x)
        L = len(x) + n_ir
        nfft = 1 << (L - 1).bit_length()
        for ch in range(2):
            ir = self.rng.standard_normal(n_ir) * np.exp(-tt * 6.9 / decay)
            ir[: int(SR * 0.012)] = 0  # pre-delay
            ir = synth.lowpass(ir.astype(np.float32), 0.25)
            ir /= np.sqrt(np.sum(ir ** 2)) + 1e-9
            y = np.fft.irfft(np.fft.rfft(x[:, ch], nfft) * np.fft.rfft(ir, nfft), nfft)
            out[:, ch] = y[: len(x)]
        return out

    def _tension_curve(self):
        tt = np.arange(self.n) / SR
        if not self.tension:
            return np.zeros(self.n, np.float32)
        ts, vs = zip(*sorted(self.tension))
        return np.interp(tt, ts, vs).astype(np.float32)

    def render(self):
        n = self.n
        dry = np.zeros((n, 2), np.float32)    # impactos
        mus = np.zeros((n, 2), np.float32)    # tonos (van a reverb)
        rain = np.zeros((n, 2), np.float32)   # granular
        bed = np.zeros((n, 2), np.float32)    # pad + beat
        rng = self.rng

        # --- limitador por frame + granular ---
        frames = {}
        for h in self.hits:
            frames.setdefault(int(h[0] * self.fps), []).append(h)
        imp_cache = {}
        last_step = -99
        for fi, evs in frames.items():
            evs.sort(key=lambda e: -e[1])
            main, rest = evs[:VOICES_PER_FRAME], evs[VOICES_PER_FRAME:]
            for k, (t, e, kind, pan, ten) in enumerate(main):
                i = int(t * SR) + int(rng.integers(0, 120))
                key = (kind, int(e * 4))
                if key not in imp_cache or rng.random() < 0.3:
                    imp_cache[key] = synth.impact(kind, e, rng)
                gl, gr = self._pan(pan)
                g = (0.12 + 0.35 * e) / (1 + 0.5 * k)
                self._add(dry, i, imp_cache[key], g * gl, g * gr)
                # tono: velocidad -> grado de la escala, tensión -> transpone hacia arriba
                step = int(e * 6) + int(ten * 8) + 5
                if step == last_step:
                    step += 1 if rng.random() < 0.5 else -1
                last_step = step
                gt = (0.09 + 0.16 * e) / (1 + k)
                self._add(mus, i, self._note(step), gt * gl, gt * gr)
            if rest:   # lluvia: granos chiquitos, cantidad acotada, nivel ~ log(n)
                g_all = 0.05 * np.log1p(len(rest)) / np.sqrt(min(len(rest), GRAINS_PER_FRAME))
                for t, e, kind, pan, ten in rest[:GRAINS_PER_FRAME]:
                    w = synth.impact("click", e, rng) * (0.4 + e)
                    gl, gr = self._pan(pan)
                    self._add(rain, int(t * SR) + int(rng.integers(0, SR // self.fps)), w, g_all * gl, g_all * gr)

        for t, kind, pan, gain in self.sigs:
            gl, gr = self._pan(pan)
            self._add(mus, int(t * SR), synth.signature(kind, rng), 0.22 * gain * gl, 0.22 * gain * gr)

        # --- pista base: pad + beat suave ---
        ten = self._tension_curve()
        tt = np.arange(n, dtype=np.float32) / SR
        chord = [0, self.scale[2], 12, 12 + self.scale[1]]
        pad = np.zeros(n, np.float32)
        for j, semi in enumerate(chord):
            f = self.root / 2 * 2 ** (semi / 12)
            for det in (-0.12, 0.12):
                pad += np.sin(2 * np.pi * (f + det) * tt + j).astype(np.float32)
        ten = np.maximum(ten, 0.3)
        pad *= (0.5 + 0.5 * np.sin(2 * np.pi * 0.2 * tt)) * 0.02 * (0.6 + 0.8 * ten)
        bed[:, 0] += pad
        bed[:, 1] += np.roll(pad, 300)
        beat = 60 / self.bpm
        kk, hh = synth.kick(rng), synth.hat(rng)
        b = 0
        end = self.climax if self.climax else self.dur
        while b * beat < end:
            t = b * beat
            lvl = float(np.interp(t, tt[:: SR // 10], ten[:: SR // 10]))
            if lvl > 0.15:
                self._add(bed, int(t * SR), kk, 0.22 * lvl, 0.22 * lvl)
            if lvl > 0.35:
                self._add(bed, int((t + beat / 2) * SR), hh, 0.15 * lvl, 0.12 * lvl)
            b += 1

        # --- efectos (boom, riser, etc.) ---
        for t, name, gain in self.fx:
            if name == "boom":
                w = synth.boom(rng)
                self._add(dry, int(t * SR), w, 0.6 * gain, 0.6 * gain)
            elif name == "riser":
                w = synth.riser(3.0, rng)
                self._add(rain, int((t - 3.0) * SR), w, 0.3 * gain, 0.3 * gain)
            elif name == "slam":
                w = synth.impact("metal", 1.0, rng)
                self._add(dry, int(t * SR), w, 0.35 * gain, 0.35 * gain)
            elif name == "chord":   # acorde de victoria, arpegiado
                for j, step in enumerate((14, 16, 17, 19, 21)):
                    self._add(mus, int((t + j * 0.07) * SR), self._note(step), 0.16 * gain, 0.16 * gain)

        # --- sidechain: los impactos empujan el bed hacia abajo ---
        env = np.abs(dry[:, 0]) + np.abs(dry[:, 1])
        env = synth.lowpass(env, 1 / (SR * 0.04))
        duck = 1 / (1 + 6 * env)
        bed *= duck[:, None]

        wet = self._reverb(mus + 0.5 * rain)
        mix = dry + mus + rain + bed + 0.35 * wet

        # --- silencio de 0.3s antes del clímax ---
        if self.climax:
            a, b2 = int((self.climax - 0.3) * SR), int(self.climax * SR)
            fade = int(0.03 * SR)
            g = np.ones(n, np.float32)
            g[a:b2] = 0
            g[a - fade:a] = np.linspace(1, 0, fade)
            mix *= g[:, None]

        return self._master(mix)

    def _master(self, x):
        # compresor RMS simple (feed-forward), luego soft-clip suave como red de seguridad
        lvl = np.sqrt(np.maximum(synth.lowpass((x[:, 0] ** 2 + x[:, 1] ** 2) / 2, 1 / (SR * 0.02)), 0) + 1e-9)
        db = 20 * np.log10(lvl)
        thr, ratio = -20.0, 3.0
        gr = np.where(db > thr, (thr - db) * (1 - 1 / ratio), 0.0)
        gain = (10 ** (gr / 20)).astype(np.float32)
        y = x * gain[:, None]
        y /= max(1e-6, np.max(np.abs(y))) / 0.89
        return np.tanh(y * 1.1) / np.tanh(1.1)

    def save(self, path, target_lufs=-14.0, ceiling_db=-2.5):
        y = self.render()
        # normalizado propio: medir LUFS -> ganancia -> limitador lookahead (2 pasadas)
        for _ in range(2):
            self._write(path, y)
            lu = measure_lufs(path)
            y = limit(y * 10 ** ((target_lufs - lu) / 20), 10 ** (ceiling_db / 20))
        return self._write(path, y)

    @staticmethod
    def _write(path, y):
        with wave.open(path, "wb") as f:
            f.setnchannels(2)
            f.setsampwidth(2)
            f.setframerate(SR)
            f.writeframes((np.clip(y, -1, 1) * 32000).astype(np.int16).tobytes())
        return path


def limit(y, ceil, look=0.004, release=0.08):
    """limitador brickwall con lookahead: la ganancia baja ANTES del pico, nunca recorta."""
    from numpy.lib.stride_tricks import sliding_window_view
    w = int(SR * look)
    a = np.max(np.abs(y), axis=1)
    need = np.minimum(1.0, ceil / np.maximum(a, 1e-9)).astype(np.float32)
    pad = np.concatenate([need, np.ones(w - 1, np.float32)])
    g = sliding_window_view(pad, w).min(axis=1)            # mira hacia adelante
    sm = synth.lowpass(g, 1 / (SR * release))
    sm = np.concatenate([np.ones(w), sm[:-w]]) if w < len(sm) else sm
    g = np.minimum(g, np.minimum(sm, 1.0))
    return np.clip(y * g[:, None], -ceil, ceil)


def measure_lufs(path):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", path, "-af", "ebur128", "-f", "null", "-"],
                       capture_output=True, text=True)
    s = r.stderr[r.stderr.rfind("Summary:"):]
    return float(s[s.find("I:") + 2:].split()[0])


def loudnorm_args(wav, target=-14.0, tp=-1.5):
    """pasada 1 de loudnorm: medir. Devuelve el filtro para la pasada 2 (lineal, exacto)."""
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", wav, "-af",
                        f"loudnorm=I={target}:TP={tp}:LRA=11:print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True)
    j = json.loads(r.stderr[r.stderr.rfind("{"):])
    return (f"loudnorm=I={target}:TP={tp}:LRA=11:measured_I={j['input_i']}:measured_TP={j['input_tp']}:"
            f"measured_LRA={j['input_lra']}:measured_thresh={j['input_thresh']}:offset={j['target_offset']}:linear=true")
