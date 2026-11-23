"""Voces brainrot sintetizadas por nosotros (espeak-ng + procesado). Nunca el audio original del meme.

Si espeak-ng no está instalado, devuelve None y el video sale sin voces (no se rompe nada).
"""
import os, shutil, subprocess, tempfile, wave
import numpy as np
from audio.synth import SR

PHRASES = {
    "tungtung": {"full": ("tung tung tung tung sahur", "it", 34, 150), "short": ("tung tung", "it", 30, 190)},
    "tralalero": {"full": ("tralalero tralala", "it", 55, 170), "short": ("tralala", "it", 60, 190)},
    "cappuccina": {"full": ("ballerina cappuccina", "it+f3", 75, 160), "short": ("cappuccina", "it+f3", 80, 185)},
}
_cache = {}


def _espeak(text, voice, pitch, speed):
    exe = shutil.which("espeak-ng") or shutil.which("espeak")
    if not exe:
        return None
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        path = f.name
    try:
        subprocess.run([exe, "-v", voice, "-p", str(pitch), "-s", str(speed), "-a", "180", "-w", path, text],
                       check=True, capture_output=True)
        with wave.open(path) as w:
            sr = w.getframerate()
            x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
    finally:
        os.remove(path)
    # remuestreo a SR + un poco de "cartoon": doble voz desafinada y brillo
    n = int(len(x) * SR / sr)
    x = np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)
    shifted = np.interp(np.arange(n) * 1.06, np.arange(n), x, right=0).astype(np.float32)
    y = 0.7 * x + 0.45 * shifted
    y = np.tanh(y * 1.8) / np.tanh(1.8)
    from audio.synth import band
    y = band(y, 90, 3200)   # voz más cálida, sin siseo
    fade = int(0.01 * SR)
    y[:fade] *= np.linspace(0, 1, fade)
    y[-fade:] *= np.linspace(1, 0, fade)
    return y / (np.max(np.abs(y)) + 1e-9)


def voice(key, kind="short"):
    k = (key, kind)
    if k not in _cache:
        spec = PHRASES.get(key, {}).get(kind)
        _cache[k] = _espeak(*spec) if spec else None
    return _cache[k]
