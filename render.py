"""python render.py --seed 7 [--fps 60] [--preview] [--seconds N]"""
import argparse, json
from variation import random_genome, punch_genome
from formats import FORMATS


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--format", default="punch")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--out", default=None)
    ap.add_argument("--seconds", type=float, default=None)
    ap.add_argument("--preview", action="store_true", help="guarda 6 frames PNG para revisar")
    a = ap.parse_args()
    from variation import press_genome, slam_genome, crusher_jaws_genome
    g = {"punch": punch_genome, "press": press_genome, "slam": slam_genome,
         "crusher_jaws": crusher_jaws_genome}.get(a.format, random_genome)(a.seed)
    out = a.out or f"out/{g['format']}_{a.seed}.mp4"
    sim = FORMATS[g["format"]](g, fps=a.fps)
    prev = ()
    if a.preview:
        prev = tuple(int(s * a.fps) for s in (0.02, 8, 20, 35, g["target_t"] + 0.6, g["target_t"] + 4.5))
    info = sim.run(out, prev, a.seconds)
    print(json.dumps({"out": out, **info, "genome": {k: v for k, v in g.items() if k != "palette"}}, indent=1))


if __name__ == "__main__":
    main()
