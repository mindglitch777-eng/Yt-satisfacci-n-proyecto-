"""Renderiza los videos del día rotando entre los formatos cerrados, con semilla distinta en cada uno.

    python -m publish.daily --count 3 --outdir release
Deja <outdir>/<fecha>_<n>_<formato>.mp4 + .json (metadatos) y agrega cada video a history.json.
"""
import argparse, datetime as dt, json, os, random
import variation as V
from formats import FORMATS
from publish.metadata import make

READY = ["crusher_jaws", "punch", "press", "slam", "iris", "two_cones"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, default=3)
    ap.add_argument("--outdir", default="release")
    ap.add_argument("--fps", type=int, default=30)
    a = ap.parse_args()
    os.makedirs(a.outdir, exist_ok=True)
    hist = json.load(open("history.json")) if os.path.exists("history.json") else []
    today = dt.datetime.now(dt.timezone.utc).date()
    day = (today - dt.date(2026, 11, 29)).days
    rng = random.Random(today.toordinal())
    for i in range(a.count):
        fmt = READY[(day * a.count + i) % len(READY)]          # cada 2 días pasan los 6 formatos
        used = {h["seed"] for h in hist if h["format"] == fmt}
        seed = rng.randrange(1, 10 ** 6)
        while seed in used:
            seed = rng.randrange(1, 10 ** 6)
        g = getattr(V, fmt + "_genome")(seed)
        part = sum(1 for h in hist if h["format"] == fmt) + 1
        g["round"] = part + 1
        base = os.path.join(a.outdir, f"{today.isoformat()}_{i + 1}_{fmt}")
        info = FORMATS[fmt](g, fps=a.fps).run(base + ".mp4")
        meta = make(fmt, seed, g["chars"], part)
        rec = {"date": today.isoformat(), "slot": i, "format": fmt, "seed": seed, "chars": g["chars"],
               "file": base + ".mp4", **meta, "seconds": info["seconds"], "render_s": info["render_s"]}
        json.dump(rec, open(base + ".json", "w"), indent=1, ensure_ascii=False)
        hist.append(rec)
        print(f"[{i + 1}/{a.count}] {fmt} semilla {seed}: {info['seconds']} s de video en {info['render_s']} s")
    json.dump(hist, open("history.json", "w"), indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()
