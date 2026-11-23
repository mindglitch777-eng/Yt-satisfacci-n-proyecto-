"""Genoma mínimo (paso 1). El genoma completo + anti-repetición llega en el paso 3."""
import random

PALETTES = [
    {"bg": (0.03, 0.02, 0.08), "floor": (0.10, 0.06, 0.22), "accent": (1.0, 0.85, 0.15), "hammer": (0.75, 0.78, 0.9)},
    {"bg": (0.01, 0.05, 0.07), "floor": (0.03, 0.15, 0.18), "accent": (0.2, 1.0, 0.75), "hammer": (0.95, 0.55, 0.3)},
    {"bg": (0.07, 0.02, 0.05), "floor": (0.2, 0.05, 0.12), "accent": (1.0, 0.4, 0.55), "hammer": (0.8, 0.8, 0.85)},
]


def punch_genome(seed):
    """genoma del PUNCH: el movimiento sale de reference/formats/punch/MEDIDAS.md (no se sortea)."""
    r = random.Random(seed)
    return {
        "seed": seed, "format": "punch", "lang": "en",
        "chars": r.sample(["tralalero", "tungtung", "cappuccina"], 3),
        "palette": {"bg": (0.015, 0.02, 0.05), "floor": (0, 0, 0), "accent": (1.0, 0.78, 0.12), "hammer": (0.8, 0.8, 0.85)},
        "capacity": 2600,
        "head_w": r.uniform(112, 124), "head_h": r.uniform(96, 106),
        "iv_early": 0.8, "iv_late": 1.3, "ritard_t": 18.0,
        "scale": r.choice(["major_penta", "minor_penta", "egyptian"]),
        "root": r.choice([130.8, 146.8, 164.8]),
        "timbre": r.choice(["marimba", "pluck"]),
        "bpm": 120, "round": r.randint(2, 9),
    }


def random_genome(seed):
    r = random.Random(seed)
    return {
        "seed": seed, "format": "hammer", "lang": "en",
        "chars": r.sample(["tralalero", "tungtung", "cappuccina"], 3),
        "winner": r.randrange(3),
        "palette": r.choice(PALETTES), "hue": r.random(),
        "chip_r": r.choice([24, 26, 28]), "packing": 0.48,
        "motion": r.choice(["spin", "pendulum"]), "speed": r.uniform(1.5, 2.1),
        "heads": r.choice([1, 2, 2]),
        "head_w": r.uniform(70, 95), "head_h": r.uniform(48, 60),
        "mult": 2,   # "el martillo aprieta la bolita y salen dos más"
        "target_t": r.uniform(45, 50), "curve": r.uniform(2.2, 2.8),
        "scale": r.choice(["major_penta", "minor_penta", "egyptian"]),
        "root": r.choice([196.0, 220.0, 246.9, 261.6]),
        "timbre": r.choice(["marimba", "glass", "bell", "pluck"]),
        "bpm": r.choice([100, 110, 120, 128]),
        "gravity": r.uniform(900, 1250),
    }
