"""python run.py --format crusher --count 3   → out/*.mp4 + out/*.json (título, descripción, tags)"""
import argparse, json, os, random, time
from engine.variation import new_genome, record
from formats.crusher import Crusher
from formats.escape import Escape

FORMATS = {"crusher": Crusher, "escape": Escape}
TAGS = ["satisfying", "oddly satisfying", "physics simulation", "asmr", "satisfying video", "bouncing ball", "shorts"]


def meta_for(g):
    title = f"{g['title_top'].title()} — {g['title_bot'].title()} #shorts #satisfying"
    return {"title": title[:100], "tags": TAGS + [g["format"], g["palette_name"]],
            "description": f"{g['title_top']} {g['title_bot']}\nComment your guess BEFORE the end 👇\n#satisfying #physics #asmr"}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--format", default="mix"); ap.add_argument("--count", type=int, default=1)
    ap.add_argument("--preview", type=int, default=0); ap.add_argument("--duration", type=float, default=60)
    a = ap.parse_args(); os.makedirs("out", exist_ok=True)
    for i in range(a.count):
        fmt = random.choice(list(FORMATS)) if a.format == "mix" else a.format
        g = new_genome(fmt); Sim = FORMATS[fmt]; Sim.DURATION = a.duration
        name = f"out/{fmt}_{g['palette_name']}_{g['seed']}"
        t0 = time.time(); res = Sim(g).render(name + ".mp4", a.preview)
        m = meta_for(g) | res; json.dump(m, open(name + ".json", "w"), indent=1)
        record(g, name + ".mp4", meta=res)
        print(f"✔ {name}.mp4  {res}  render {time.time()-t0:.0f}s")
