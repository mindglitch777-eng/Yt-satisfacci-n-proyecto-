"""Hoja de personajes para revisar el dibujo: python -m tools.sheet out/chars.png"""
import sys, skia
from engine.gfx import bake, draw_text
from characters import ROSTER

def main(path):
    chars = list(ROSTER.values())
    def fn(c):
        c.clear(skia.Color(16, 16, 28))
        for i, ch in enumerate(chars):
            for j, r in enumerate((120, 40, 18)):
                img, half = ch.sprite(r)
                c.drawImage(img, 180 + i * 330 - half, 220 + j * 230 - half)
            draw_text(c, ch.name, 180 + i * 330, 820, 44, ch.color, stroke=6)
    bake(1020, 880, fn).save(path, skia.kPNG)

if __name__ == "__main__":
    main(sys.argv[1])
