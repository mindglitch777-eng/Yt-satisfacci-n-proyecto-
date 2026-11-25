"""Voces de los brainrots: SOLO si hay grabaciones propias en assets/voices/.

Las voces sintetizadas (espeak) quedaban mal, así que se sacaron. Sin archivos, el video sale sin voces.
Archivos aceptados (wav o mp3, cualquier sample rate, se normalizan solos):
    assets/voices/<personaje>_short.wav   (p. ej. tungtung_short.wav: "tung tung")
    assets/voices/<personaje>_full.wav    (p. ej. tungtung_full.wav: "tung tung tung sahur")
    assets/voices/<personaje>.wav         (se usa para los dos si no hay los otros)
Personajes: tungtung, tralalero, cappuccina.
OJO: tienen que ser grabaciones propias o con licencia. El audio original de los memes puede generar reclamos de copyright.
"""
import os, subprocess
import numpy as np
from audio.synth import SR

DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "voices")
_cache = {}


def _load(path):
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                       capture_output=True)
    y = np.frombuffer(r.stdout, np.float32).copy()
    if not len(y):
        return None
    fade = int(0.01 * SR)
    y[:fade] *= np.linspace(0, 1, fade)
    y[-fade:] *= np.linspace(1, 0, fade)
    return y / (np.max(np.abs(y)) + 1e-9)


def voice(key, kind="short"):
    k = (key, kind)
    if k not in _cache:
        _cache[k] = None
        for name in (f"{key}_{kind}", key):
            for ext in (".wav", ".mp3", ".ogg", ".m4a"):
                p = os.path.join(DIR, name + ext)
                if os.path.exists(p):
                    _cache[k] = _load(p)
                    break
            if _cache[k] is not None:
                break
    return _cache[k]
