"""Fichas brainrot: versiones propias dibujadas en vector (nada descargado).

Cada ficha = sprite + identidad mecánica (masa, rebote, tamaño), sonido propio y un poder.
"""
import math
import skia
from engine.gfx import rgb, bake, draw_text


def _p(c, col, a=1.0, stroke=0.0):
    p = skia.Paint(Color4f=rgb(col, a), AntiAlias=True)
    if stroke:
        p.setStyle(skia.Paint.kStroke_Style)
        p.setStrokeWidth(stroke)
        p.setStrokeCap(skia.Paint.kRound_Cap)
        p.setStrokeJoin(skia.Paint.kRound_Join)
    return p


def _eyes(c, r, y, dx, size, look=(0.15, 0.1), white=(1, 1, 1)):
    for sx in (-1, 1):
        c.drawCircle(sx * dx * r, y * r, size * r, _p(c, white))
        c.drawCircle(sx * dx * r, y * r, size * r, _p(c, (0.08, 0.08, 0.1), 1, r * 0.035))
        c.drawCircle(sx * dx * r + look[0] * size * r, y * r + look[1] * size * r, size * 0.5 * r,
                     _p(c, (0.05, 0.05, 0.08)))
        c.drawCircle(sx * dx * r + (look[0] - 0.2) * size * r, y * r - 0.25 * size * r, size * 0.18 * r,
                     _p(c, (1, 1, 1)))


class Character:
    key = ""
    name = ""
    color = (1, 1, 1)
    mass = 1.0
    bounce = 0.9
    size = 1.0          # multiplicador de radio
    power = ""
    power_label = ""
    sound = {}

    def draw_body(self, c, r):
        raise NotImplementedError

    def sprite(self, r):
        """sprite horneado: aro de color de equipo + personaje recortado al círculo."""
        cache = self.__dict__.setdefault("_cache", {})
        k = round(r, 1)
        if k not in cache:
            pad = 6
            S = 2 * (r + pad)

            def fn(c):
                c.translate(S / 2, S / 2)
                c.drawCircle(0, 0, r + 3, _p(c, self.color, 0.35))
                c.save()
                path = skia.Path().addCircle(0, 0, r)
                c.clipPath(path, doAntiAlias=True)
                c.drawCircle(0, 0, r, _p(c, self.bg))
                self.draw_body(c, r)
                # brillo superior
                sh = skia.GradientShader.MakeLinear([(0, -r), (0, r * 0.2)],
                                                    [skia.Color4f(1, 1, 1, 0.28).toColor(),
                                                     skia.Color4f(1, 1, 1, 0).toColor()])
                c.drawCircle(0, 0, r, skia.Paint(Shader=sh, AntiAlias=True))
                c.restore()
                c.drawCircle(0, 0, r - r * 0.05, _p(c, self.color, 1, max(2.0, r * 0.12)))
            cache[k] = (bake(S, S, fn), S / 2)
        return cache[k]


class Tralalero(Character):
    """tiburón azul con zapatillas: liviano y elástico."""
    key, name = "tralalero", "TRALALERO"
    color = (0.25, 0.65, 1.0)
    bg = (0.55, 0.85, 1.0)
    mass, bounce, size = 0.8, 0.98, 1.0
    power, power_label = "double_bounce", "DOUBLE BOUNCE"
    sound = {"kind": "bubble", "base": 1.0}

    def draw_body(self, c, r):
        body = (0.33, 0.52, 0.72)
        # aleta dorsal
        fin = skia.Path()
        fin.moveTo(-0.15 * r, -0.62 * r); fin.lineTo(0.18 * r, -1.05 * r); fin.lineTo(0.32 * r, -0.55 * r); fin.close()
        c.drawPath(fin, _p(c, body))
        c.drawOval(skia.Rect(-0.95 * r, -0.7 * r, 0.95 * r, 0.75 * r), _p(c, body))
        # panza blanca
        c.drawOval(skia.Rect(-0.7 * r, 0.0, 0.7 * r, 0.8 * r), _p(c, (0.96, 0.97, 1.0)))
        # boca con dientes
        mouth = skia.Path()
        mouth.moveTo(-0.5 * r, 0.22 * r); mouth.quadTo(0, 0.62 * r, 0.5 * r, 0.22 * r); mouth.close()
        c.drawPath(mouth, _p(c, (0.55, 0.08, 0.12)))
        teeth = skia.Path()
        for i in range(6):
            x0 = -0.45 * r + i * 0.15 * r
            teeth.moveTo(x0, 0.24 * r); teeth.lineTo(x0 + 0.075 * r, 0.36 * r); teeth.lineTo(x0 + 0.15 * r, 0.24 * r)
        c.drawPath(teeth, _p(c, (1, 1, 1)))
        _eyes(c, r, -0.2, 0.36, 0.2, look=(0.3, 0.1))
        # zapatillas
        for sx in (-1, 1):
            c.drawRoundRect(skia.Rect(sx * 0.55 * r - 0.28 * r, 0.72 * r, sx * 0.55 * r + 0.28 * r, 0.95 * r),
                            0.1 * r, 0.1 * r, _p(c, (0.15, 0.4, 1.0)))
            c.drawLine(sx * 0.55 * r - 0.2 * r, 0.8 * r, sx * 0.55 * r + 0.2 * r, 0.8 * r, _p(c, (1, 1, 1), 1, 0.05 * r))


class TungTung(Character):
    """tronco de madera con bate: pesado, golpea fuerte."""
    key, name = "tungtung", "TUNG TUNG"
    color = (1.0, 0.62, 0.2)
    bg = (1.0, 0.86, 0.6)
    mass, bounce, size = 2.2, 0.72, 1.12
    power, power_label = "slam", "TUNG SLAM"
    sound = {"kind": "wood", "base": 1.0}

    def draw_body(self, c, r):
        wood, dark = (0.72, 0.47, 0.25), (0.45, 0.27, 0.12)
        c.drawRoundRect(skia.Rect(-0.62 * r, -0.95 * r, 0.62 * r, 1.0 * r), 0.35 * r, 0.35 * r, _p(c, wood))
        for i, y in enumerate((-0.55, 0.15, 0.62)):  # vetas
            c.drawLine(-0.5 * r, y * r, -0.15 * r, (y + 0.06) * r, _p(c, dark, 0.6, 0.05 * r))
            c.drawLine(0.2 * r, (y + 0.15) * r, 0.5 * r, (y + 0.1) * r, _p(c, dark, 0.6, 0.05 * r))
        c.drawOval(skia.Rect(-0.55 * r, -1.02 * r, 0.55 * r, -0.72 * r), _p(c, (0.85, 0.62, 0.38)))
        c.drawOval(skia.Rect(-0.3 * r, -0.94 * r, 0.3 * r, -0.8 * r), _p(c, dark, 0.7, 0.04 * r))
        _eyes(c, r, -0.25, 0.27, 0.19, look=(0.0, 0.25))
        c.drawLine(-0.22 * r, 0.25 * r, 0.22 * r, 0.25 * r, _p(c, (0.2, 0.1, 0.05), 1, 0.07 * r))
        # bate
        bat = skia.Path()
        bat.moveTo(0.55 * r, 0.75 * r); bat.lineTo(0.95 * r, -0.4 * r); bat.lineTo(1.12 * r, -0.33 * r); bat.lineTo(0.68 * r, 0.8 * r); bat.close()
        c.drawPath(bat, _p(c, (0.9, 0.74, 0.5)))
        c.drawPath(bat, _p(c, dark, 1, 0.04 * r))


class Cappuccina(Character):
    """taza de cappuccino bailarina: chiquita, se divide al ser golpeada."""
    key, name = "cappuccina", "CAPPUCCINA"
    color = (1.0, 0.38, 0.72)
    bg = (1.0, 0.8, 0.9)
    mass, bounce, size = 0.6, 0.88, 0.9
    power, power_label = "split", "SPLIT x2"
    sound = {"kind": "ceramic", "base": 1.0}

    def draw_body(self, c, r):
        cup = (0.98, 0.96, 0.92)
        # tutú
        tutu = skia.Path()
        tutu.moveTo(-0.95 * r, 0.75 * r)
        for i in range(7):
            x = -0.95 * r + (i + 0.5) * (1.9 * r / 7)
            tutu.quadTo(x, 1.05 * r, x + 0.95 * r / 7, 0.75 * r)
        tutu.lineTo(0.6 * r, 0.5 * r); tutu.lineTo(-0.6 * r, 0.5 * r); tutu.close()
        c.drawPath(tutu, _p(c, (1.0, 0.55, 0.78)))
        # taza
        cupp = skia.Path()
        cupp.moveTo(-0.7 * r, -0.45 * r); cupp.lineTo(0.7 * r, -0.45 * r); cupp.lineTo(0.5 * r, 0.62 * r)
        cupp.quadTo(0, 0.75 * r, -0.5 * r, 0.62 * r); cupp.close()
        c.drawPath(cupp, _p(c, cup))
        c.drawCircle(0.78 * r, 0.0, 0.2 * r, _p(c, cup, 1, 0.09 * r))  # asa
        # café + espuma con corazón
        c.drawOval(skia.Rect(-0.7 * r, -0.62 * r, 0.7 * r, -0.28 * r), _p(c, (0.48, 0.28, 0.15)))
        c.drawOval(skia.Rect(-0.55 * r, -0.56 * r, 0.55 * r, -0.34 * r), _p(c, (0.93, 0.82, 0.66)))
        heart = skia.Path()
        heart.moveTo(0, -0.38 * r); heart.cubicTo(-0.25 * r, -0.5 * r, -0.08 * r, -0.62 * r, 0, -0.5 * r)
        heart.cubicTo(0.08 * r, -0.62 * r, 0.25 * r, -0.5 * r, 0, -0.38 * r)
        c.drawPath(heart, _p(c, (0.6, 0.35, 0.2)))
        _eyes(c, r, 0.02, 0.25, 0.15, look=(-0.2, 0.0))
        smile = skia.Path(); smile.moveTo(-0.15 * r, 0.3 * r); smile.quadTo(0, 0.42 * r, 0.15 * r, 0.3 * r)
        c.drawPath(smile, _p(c, (0.4, 0.15, 0.15), 1, 0.05 * r))
        for sx in (-1, 1):  # cachetes
            c.drawCircle(sx * 0.42 * r, 0.25 * r, 0.09 * r, _p(c, (1, 0.5, 0.6), 0.6))


ROSTER = {cls.key: cls() for cls in (Tralalero, TungTung, Cappuccina)}


def get(key):
    return ROSTER[key]
