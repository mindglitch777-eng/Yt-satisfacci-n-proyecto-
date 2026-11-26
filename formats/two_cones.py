"""TWO CONES — dos agujas/conos en varillas desde el centro que giran sin parar en sentidos opuestos (simétricos:
se cruzan abajo y arriba, alternando). El golpe ACELERA (0.93 → 0.43 s). Lo que queda entre los conos se duplica.
Gravedad leve, el aro destella del color nuevo en cada golpe, final "drop". Reutiliza el giro continuo de punch.
Datos: reference/formats/two_cones/spec.json (xbongobeats 5.3M)."""
import math
import skia

from formats.punch import Punch
from engine.gfx import rgb, W, H, draw_text

TXT = {
    "en": {"t1": "WAIT FOR", "t2": "THE DROP", "balls": "BALLS", "full": "DROP!",
           "almost": "HERE IT COMES...", "taking": "IS TAKING OVER", "wins": "WINS!", "broke": "DROP!",
           "cta1": "WHICH MACHINE IS NEXT?", "cta2": "SUBSCRIBE FOR PART {n}"},
    "es": {"t1": "ESPERÁ", "t2": "EL DROP", "balls": "BOLAS", "full": "¡DROP!",
           "almost": "AHÍ VIENE...", "taking": "VA GANANDO", "wins": "¡GANA!", "broke": "¡DROP!",
           "cta1": "¿QUÉ MÁQUINA SIGUE?", "cta2": "SUSCRIBITE PARA LA PARTE {n}"},
}


class TwoCones(Punch):
    TXT = TXT

    def setup(self):
        super().setup()
        import pymunk
        for b in self.arm_bodies:                 # la varilla es fina: no choca; solo el cono golpea
            for sh in b.shapes:
                if isinstance(sh, pymunk.Segment):
                    sh.filter = pymunk.ShapeFilter(mask=0)

    def _sweep(self, P0, new_ang):
        """sin empuje geométrico de la varilla (en la referencia la varilla no arrastra la pila); el cono choca por física."""
        return

    def _break(self):
        """drop: el aro desaparece y las bolas se dispersan por toda la pantalla (sin caer)."""
        super()._break()
        self.space.gravity = (0, 0)
        self.space.damping = 0.6
        self.frags = []

    def draw_world(self, c):
        super().draw_world(c)
        # destello del aro con el color del último golpe
        if self.broken_at is None and self.flashes:
            age = self.flashes[-1][2]
            col = self.colors[self.cur]
            c.drawCircle(self.cx, self.cy, self.R + 6, skia.Paint(
                Color4f=rgb(col, max(0.0, 1 - age / 0.3)), AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=10))

    def draw_arms(self, c):
        """varilla fina + cono metálico (aguja) apuntando hacia afuera."""
        if self.broken_at is not None and self.t - self.broken_at > 0.35:
            return
        L, hw, hh = self.arm_len, self.hw, self.hh
        rod = skia.Paint(Color4f=rgb((0.55, 0.56, 0.6)), AntiAlias=True, StrokeWidth=4)
        for a in self.ang:
            c.save(); c.translate(self.cx, self.cy); c.rotate(math.degrees(a))
            c.drawLine(0, 0, L - hh / 2, 0, rod)
            sh = skia.GradientShader.MakeLinear([(0, -hw / 2), (0, hw / 2)],
                                                [rgb((0.35, 0.36, 0.4)).toColor(), rgb((0.85, 0.86, 0.9)).toColor(),
                                                 rgb((0.3, 0.31, 0.35)).toColor()])
            cone = skia.Path()
            cone.moveTo(L - hh / 2, -hw * 0.12); cone.lineTo(L + hh / 2, -hw / 2)
            cone.lineTo(L + hh / 2, hw / 2); cone.lineTo(L - hh / 2, hw * 0.12); cone.close()
            c.drawPath(cone, skia.Paint(Shader=sh, AntiAlias=True))
            c.drawRect(skia.Rect(L + hh / 2 - 8, -hw / 2, L + hh / 2, hw / 2), skia.Paint(Color4f=rgb((0.2, 0.2, 0.23)), AntiAlias=True))
            c.restore()
        c.drawCircle(self.cx, self.cy, 6, skia.Paint(Color4f=rgb((0.9, 0.9, 0.92)), AntiAlias=True,
                                                      Style=skia.Paint.kStroke_Style, StrokeWidth=2))
