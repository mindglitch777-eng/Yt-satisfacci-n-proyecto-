# BRAINROT PHYSICS

Shorts de física "satisfying" 100% código, protagonizados por fichas brainrot. Ver `CLAUDE.md` para el plan completo.

```bash
pip install -r requirements.txt          # + ffmpeg; en Linux: apt-get install libegl1 (lo pide skia)
python render.py --seed 8 --preview      # -> out/hammer_8.mp4 (+ 6 PNG de control)
python -m tools.qa out/hammer_8.mp4      # hoja de 6 frames + LUFS / true peak
python -m tools.sheet out/chars.png      # hoja de personajes
```

## Estado (paso 1 del plan: hecho)
| Pieza | Archivo |
|---|---|
| Física pymunk (substeps, anti-tunneling duro, fichas que nunca se quedan quietas) | `engine/sim.py` |
| Render skia: aro neón horneado, sprites, motion blur liviano, partículas, popups "+N", camera shake/zoom | `engine/gfx.py`, `engine/sim.py` |
| Pacer: lleno programado (seg 44-50), guion de cambios de líder y near-miss | `engine/pacer.py` |
| Sonido: impacto + tono pentatónico por velocidad + reverb, tensión sube el pitch, limitador por frame + lluvia granular, pad+beat con sidechain, silencio 0.3s + boom, compresor, -14 LUFS con limitador lookahead | `audio/` |
| 3 fichas brainrot propias (vector) con masa/rebote/tamaño, sonido y poder: Tralalero (double bounce), Tung Tung (slam), Cappuccina (split) | `characters/` |
| Formato: martillo multiplicador, batalla de 3 brainrots | `formats/hammer.py` |
| Loop: los últimos 0.5s se funden con el frame 1 | `engine/sim.py` |

Medición (4 cores, 30 fps): ~50 s de video en ~70 s de render. A 60 fps (`--fps 60`) ronda los 2.5 min.

Siguiente: paso 2 (batalla + merge evolutivo como formatos propios), paso 3 (genoma completo + anti-repetición + metadatos), paso 4 (workflow).
