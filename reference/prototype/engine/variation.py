"""Sistema de dinamismo + anti-repetición.
Cada video = un 'genoma' de parámetros. Se guarda su huella en history.json y
se rechaza cualquier genoma demasiado parecido a los últimos N publicados."""
import json, random, os, time, hashlib

PALETTES = [
    {"name": "neon_night", "bg": (.02, .02, .06), "accent": (1, .82, .1), "hammer": (.85, .2, .25),
     "balls": [(.98, .3, .4), (.3, .9, .5), (.35, .55, 1), (1, .85, .2), (.8, .4, 1)]},
    {"name": "candy", "bg": (.05, .02, .08), "accent": (1, .4, .7), "hammer": (.6, .6, .68),
     "balls": [(1, .55, .75), (.55, .85, 1), (.75, 1, .6), (1, .9, .5)]},
    {"name": "mono_red", "bg": (.03, .03, .04), "accent": (1, .25, .3), "hammer": (.65, .65, .7),
     "balls": [(.95, .2, .25), (1, .35, .35), (.85, .15, .2)]},
    {"name": "toxic", "bg": (.01, .04, .03), "accent": (.4, 1, .3), "hammer": (.9, .75, .1),
     "balls": [(.4, 1, .3), (.2, .9, .6), (.7, 1, .2)]},
    {"name": "ocean", "bg": (.01, .03, .07), "accent": (.3, .9, 1), "hammer": (.95, .5, .15),
     "balls": [(.2, .6, 1), (.3, .9, 1), (.5, .4, 1), (.9, .95, 1)]},
    {"name": "rainbow", "bg": (.03, .02, .05), "accent": (1, .85, .1), "hammer": (.7, .7, .75),
     "balls": [(1, .3, .3), (1, .6, .2), (1, .9, .2), (.3, .9, .4), (.3, .6, 1), (.7, .4, 1)]},
]

TITLES = {
    "crusher": [("EVERY HIT = x{m} BALLS", "FULL BY 60 SECONDS?"), ("CAN 1 BALL", "FILL IT IN 60 SECONDS?"),
                ("EVERY PUNCH MULTIPLIES", "WILL IT GET FULL?"), ("1 BALL vs A MACHINE", "HOW MANY AT 60s?")],
    "escape": [("EVERY ESCAPE = {m} NEW BALLS", "HOW MANY AT 60 SECONDS?"), ("ESCAPE = x{m}", "WILL IT GET FULL?"),
               ("1 BALL. 1 GAP.", "CAN IT FILL THE CIRCLE?")],
}

SPACE = {
    "crusher": lambda r: {"heads": r.choice([1, 2, 2, 3]), "arm_len": r.uniform(.55, .8), "head_w": r.uniform(100, 160),
                          "head_h": r.uniform(45, 70), "motion": r.choice(["spin", "pendulum"]),
                          "speed": r.uniform(.9, 2.0), "mult": r.choice([2, 3, 4])},
    "escape": lambda r: {"gap_deg": r.uniform(22, 45), "speed": r.uniform(.7, 1.6), "flip_every": r.uniform(4, 9),
                         "mult": r.choice([2, 3, 3, 4])},
}

NUMERIC = ["arm_len", "head_w", "speed", "gap_deg", "ball_r", "target_t", "curve", "hue"]


def fingerprint(g):
    return {k: g[k] for k in ["format", "palette_name", "title_idx", "heads", "motion", "mult"] if k in g} | \
           {k: round(g[k], 2) for k in NUMERIC if k in g}


def distance(a, b):
    if a.get("format") != b.get("format"): return 1.0
    cat = sum(a.get(k) != b.get(k) for k in ["palette_name", "title_idx", "heads", "motion", "mult"]) / 5
    num = [abs(a[k] - b[k]) / (abs(a[k]) + abs(b[k]) + 1e-6) for k in NUMERIC if k in a and k in b]
    return .6 * cat + .4 * (sum(num) / max(1, len(num)))


def new_genome(fmt, history_path="history.json", window=30, min_dist=.28, tries=200):
    hist = json.load(open(history_path)) if os.path.exists(history_path) else []
    recent = [h["fp"] for h in hist if h["fp"]["format"] == fmt][-window:]
    best, best_d = None, -1
    for _ in range(tries):
        seed = random.SystemRandom().randrange(2**31); r = random.Random(seed)
        pal = r.choice(PALETTES); ti = r.randrange(len(TITLES[fmt]))
        g = {"format": fmt, "seed": seed, "palette": pal, "palette_name": pal["name"], "title_idx": ti,
             "hue": r.random(), "ball_r": r.choice([7, 8, 9, 10]), "target_t": r.uniform(50, 57),
             "curve": r.uniform(2.2, 3.4), "bounce": r.uniform(.8, .95)} | SPACE[fmt](r)
        top, bot = TITLES[fmt][ti]
        g["title_top"], g["title_bot"] = top.format(m=g.get("mult", 2)), bot.format(m=g.get("mult", 2))
        d = min([distance(fingerprint(g), h) for h in recent] or [1])
        if d >= min_dist: return g
        if d > best_d: best, best_d = g, d
    return best  # el más distinto posible si el espacio está saturado


def record(g, path_video, history_path="history.json", meta=None):
    hist = json.load(open(history_path)) if os.path.exists(history_path) else []
    hist.append({"ts": int(time.time()), "video": path_video, "fp": fingerprint(g), "seed": g["seed"],
                 "id": hashlib.md5(str(g["seed"]).encode()).hexdigest()[:8], "meta": meta or {}})
    json.dump(hist, open(history_path, "w"), indent=1)
