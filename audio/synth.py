"""Instrumentos sintetizados (sin samples, sin copyright)."""
import numpy as np

SR = 44100
SCALES = {
    "major_penta": [0, 2, 4, 7, 9],
    "minor_penta": [0, 3, 5, 7, 10],
    "japanese": [0, 1, 5, 7, 8],
    "egyptian": [0, 2, 5, 7, 10],
}


def t_axis(dur):
    return np.arange(int(SR * dur), dtype=np.float32) / SR


def env_ad(n, attack=0.002, decay=8.0):
    x = np.arange(n, dtype=np.float32) / SR
    a = np.clip(x / attack, 0, 1)
    return a * np.exp(-x * decay)


def tone(freq, timbre, dur=0.5):
    x = t_axis(dur)
    w2 = 2 * np.pi * freq * x
    if timbre == "pluck":
        w = np.sin(w2) + 0.35 * np.sin(2 * w2) * np.exp(-x * 30) + 0.15 * np.sin(3 * w2) * np.exp(-x * 45)
        e = env_ad(len(x), 0.001, 9)
    elif timbre == "marimba":
        w = np.sin(w2) + 0.45 * np.sin(4 * w2) * np.exp(-x * 50) + 0.2 * np.sin(10 * w2) * np.exp(-x * 120)
        e = env_ad(len(x), 0.001, 11)
    elif timbre == "glass":
        w = np.sin(w2) + 0.5 * np.sin(2.76 * w2) * np.exp(-x * 6) + 0.25 * np.sin(5.4 * w2) * np.exp(-x * 14)
        e = env_ad(len(x), 0.002, 5)
    else:  # bell
        w = np.sin(w2) + 0.6 * np.sin(2.0 * w2 + 0.3) * np.exp(-x * 4) + 0.4 * np.sin(3.01 * w2) * np.exp(-x * 9) \
            + 0.2 * np.sin(4.2 * w2) * np.exp(-x * 16)
        e = env_ad(len(x), 0.002, 4)
    return (w * e / 1.7).astype(np.float32)


def noise(n, rng):
    return rng.standard_normal(n).astype(np.float32)


def lowpass(x, alpha):
    """one-pole IIR vectorizado vía filtro exponencial por bloques (aprox barato)."""
    k = int(max(1, 1 / alpha))
    kern = np.exp(-np.arange(k * 4) / k).astype(np.float32)
    kern /= kern.sum()
    if len(kern) < 64:
        return np.convolve(x, kern)[: len(x)].astype(np.float32)
    L = len(x) + len(kern)
    nfft = 1 << (L - 1).bit_length()
    return np.fft.irfft(np.fft.rfft(x, nfft) * np.fft.rfft(kern, nfft), nfft)[: len(x)].astype(np.float32)


def impact(kind, energy, rng):
    """transiente de golpe según la ficha."""
    if kind == "bubble":      # tiburón: blip de burbuja que cae de pitch
        x = t_axis(0.09)
        f = 700 + 900 * energy
        w = np.sin(2 * np.pi * np.cumsum(f * np.exp(-x * 25) + 250) / SR) * env_ad(len(x), 0.001, 45)
    elif kind == "wood":      # tronco: toc de madera
        x = t_axis(0.12)
        w = (np.sin(2 * np.pi * 520 * x) * np.exp(-x * 55) + 0.6 * np.sin(2 * np.pi * 1180 * x) * np.exp(-x * 80)
             + 0.5 * noise(len(x), rng) * np.exp(-x * 300))
    elif kind == "ceramic":   # taza: tin de cerámica
        x = t_axis(0.18)
        w = (np.sin(2 * np.pi * 2350 * x) + 0.6 * np.sin(2 * np.pi * 3720 * x) + 0.4 * np.sin(2 * np.pi * 5110 * x)) \
            * np.exp(-x * 32) * 0.5 + 0.4 * noise(len(x), rng) * np.exp(-x * 400)
    elif kind == "metal":     # martillo / pared
        x = t_axis(0.25)
        w = (np.sin(2 * np.pi * 180 * x) * np.exp(-x * 25) + 0.5 * np.sin(2 * np.pi * 1630 * x) * np.exp(-x * 40)
             + 0.6 * noise(len(x), rng) * np.exp(-x * 160))
    else:                     # click genérico
        x = t_axis(0.03)
        w = noise(len(x), rng) * np.exp(-x * 250)
    return w.astype(np.float32)


def signature(kind, rng):
    """"voz" de la ficha cuando se multiplica (su firma sonora)."""
    if kind == "wood":   # tung-tung: doble toc grave
        a = impact("wood", 1.0, rng)
        out = np.zeros(int(SR * 0.32), np.float32)
        lo = np.sin(2 * np.pi * 300 * t_axis(0.12)) * np.exp(-t_axis(0.12) * 40)
        out[: len(a)] += a + lo.astype(np.float32)
        o = int(SR * 0.16)
        out[o:o + len(a)] += 0.8 * (a + lo.astype(np.float32))
        return out
    if kind == "bubble":  # tralalero: trino que sube
        x = t_axis(0.28)
        f = 500 + 1400 * x / 0.28 + 120 * np.sin(2 * np.pi * 28 * x)
        return (np.sin(2 * np.pi * np.cumsum(f) / SR) * env_ad(len(x), 0.005, 9)).astype(np.float32)
    if kind == "ceramic":  # cappuccina: ting-ting
        a = impact("ceramic", 1.0, rng)
        out = np.zeros(int(SR * 0.3), np.float32)
        out[: len(a)] += a
        o = int(SR * 0.09)
        out[o:o + len(a)] += 0.7 * a
        return out
    return impact("click", 1.0, rng)


def kick(rng):
    x = t_axis(0.35)
    f = 45 + 110 * np.exp(-x * 30)
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-x * 9)).astype(np.float32)


def hat(rng):
    x = t_axis(0.05)
    n = noise(len(x), rng)
    n = n - lowpass(n, 0.3)
    return (n * np.exp(-x * 90) * 0.5).astype(np.float32)


def boom(rng):
    x = t_axis(2.2)
    f = 30 + 90 * np.exp(-x * 3)
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-x * 1.6)
    n = lowpass(noise(len(x), rng), 0.08) * np.exp(-x * 2.5) * 3
    return (sub + n).astype(np.float32)


def riser(dur, rng):
    x = t_axis(dur)
    n = noise(len(x), rng)
    hp = n - lowpass(n, 0.05)
    return (hp * (x / dur) ** 2 * 0.5).astype(np.float32)


def squish(rng, energy=1.0):
    """aplastado: thunk grave + ruido "húmedo" que cae de pitch."""
    x = t_axis(0.22)
    f = 220 * np.exp(-x * 14) + 60
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-x * 18)
    n = noise(len(x), rng)
    wet = (lowpass(n, 0.12) * 3) * np.exp(-x * 26) * (0.5 + 0.5 * np.sin(2 * np.pi * np.cumsum(900 * np.exp(-x * 20) + 80) / SR))
    return ((body * 0.9 + wet * 0.7) * (0.6 + 0.4 * energy)).astype(np.float32)


def pop(rng, pitch=1.0):
    """pop de multiplicación: burbuja brillante que sube."""
    x = t_axis(0.11)
    f = (600 + 2600 * (1 - np.exp(-x * 60))) * pitch
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * env_ad(len(x), 0.001, 38)).astype(np.float32)


def clack(rng, energy=1.0):
    """canica contra canica: dos parciales altos inarmónicos, cortísimo."""
    x = t_axis(0.05)
    f1 = rng.uniform(2600, 3800)
    w = np.sin(2 * np.pi * f1 * x) + 0.6 * np.sin(2 * np.pi * f1 * 2.31 * x)
    return (w * np.exp(-x * 120) * (0.4 + 0.6 * energy) * 0.6).astype(np.float32)
