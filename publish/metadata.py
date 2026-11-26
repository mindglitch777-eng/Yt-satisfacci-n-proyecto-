"""Títulos, descripciones y tags variados y honestos (sin clickbait falso), uno distinto por video."""
import random

TITLES = {
    "crusher_jaws": ["Every crushed ball becomes 4", "The crusher jaws never stop", "How many balls can the jaws make?",
                     "1 ball vs the crusher jaws", "Watch the jaws fill the circle"],
    "punch": ["Can 1 ball refill it in 60 seconds?", "Two hammers, one ball, endless copies",
              "Every punch doubles what it catches", "1 ball → full circle", "The hammers keep spinning"],
    "press": ["Every crushed ball becomes 4 more", "The press never misses", "1 ball vs the X press",
              "How fast does the press fill it?", "The 4-bar press"],
    "slam": ["The giant hammer doubles every ball", "2 balls to 2048", "Can the hammer reach 2048?",
             "Giant hammer vs tiny balls", "Every slam = ×2"],
    "iris": ["The iris crushes every ball into 4", "7 blades, 1 ball", "Watch the iris close",
             "How many balls can the iris make?", "The shutter multiplies everything"],
    "two_cones": ["Wait for the drop", "Two needles, faster every hit", "The cones never stop",
                  "It gets faster… then drops", "1 ball, 2 needles, 2000 balls"],
}
MECHANIC = {
    "crusher_jaws": "Two gear-driven jaws take turns crushing whatever they grab, and every crushed ball comes back as 4.",
    "punch": "Two spinning hammers clap together; whatever gets trapped between them doubles.",
    "press": "Four bars slide on X-shaped rails and crush the middle; every crushed ball becomes 4 more.",
    "slam": "A giant pendulum hammer squeezes the balls against the side blocks and doubles them, all the way to 2048.",
    "iris": "Seven curved blades close like a camera shutter; every ball caught in the center becomes 4.",
    "two_cones": "Two needles spin in opposite directions, faster every hit, until the circle drops.",
}
BASE_TAGS = ["satisfying", "physics simulation", "satisfying video", "oddly satisfying", "ball simulation",
             "brainrot", "shorts", "asmr physics", "multiply balls"]
FMT_TAGS = {
    "crusher_jaws": ["crusher", "jaws", "gears"], "punch": ["hammer", "punch", "refill"],
    "press": ["hydraulic press", "press", "crush"], "slam": ["giant hammer", "2048", "pendulum"],
    "iris": ["iris", "shutter", "blades"], "two_cones": ["drop", "needles", "beat"],
}


def make(fmt, seed, chars, part):
    r = random.Random(seed * 7919 + len(fmt))
    title = f"{r.choice(TITLES[fmt])} #shorts"
    names = ", ".join(c.upper() for c in chars)
    desc = (f"{MECHANIC[fmt]}\n\nBrainrot colors in this one: {names}.\n"
            f"Part {part} — which machine should come next? Tell me in the comments.\n\n"
            "100% generated with code: physics, drawing and sounds made by us.\n"
            "#satisfying #physics #brainrot")
    tags = BASE_TAGS + FMT_TAGS[fmt] + [c for c in chars]
    r.shuffle(tags)
    return {"title": title[:100], "description": desc, "tags": tags[:15]}
