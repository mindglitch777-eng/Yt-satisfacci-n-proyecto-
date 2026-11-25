> **CERRADO (25-11-2026).** Cobertura del final medida con la MISMA regla de píxeles para la referencia y el render
> (`% de píxeles saturados`, tools: scratch cov.py): 24.5 s 85/91 · 25.5 81–79/89 · 26.5 70–67/64 · 27.5 33–32/33 ·
> 28.5 23–24/25 · 29.5 13/13 · 30.5 12/11 (semillas 1 y 2 / ref) → todas dentro de ±10.
> Bolitas con el estilo de la referencia (brillo arriba, sin contorno oscuro) en todos los formatos.

> **v2 (24-11-2026), fiel a la referencia:** cada pinza = 2 brazos en L que GIRAN sobre el engranaje del aro (tijera),
> una vuelta cada 4.2 s: entran barriendo, "⊐" → rombo → "T" (aplastón ×4) → salen y quedan plegadas afuera ~2.3 s.
> Las dos en contrafase → aplastón cada 2.1 s alternado. Brazos = cuerpos rígidos que rotan (no se recrean por frame).
> Detector: además mide `jaw_outside_pct` (brazos afuera del aro, ref 70%) y corta cuando las bolas cubren >30% del aro.
> La v1 (pinzas que se estiraban desde adentro) daba PASA porque el detector solo miraba adentro del aro.

# SPEC — CRUSHER JAWS (fuente: reference/videos/raw/nexusboxlab_crusher_9.6M.mp4)

## Medición (tools/motion/measure.py --machine jaws)
Detector de pinzas laterales: por frame y por mitad (izq/der), reach = 1 − distancia mínima al centro de los píxeles
gris medio (95 < g < 215, sat < 30, d < 0.9R). Se descarta el tramo en que las bolas tapan > 30% del círculo
(los tonos sombreados de las bolas se confunden con el gris). En la referencia: válido 0–12.2 s, 6 entradas.

| métrica | ref | qué es |
|---|---|---|
| jaw_cycle_s | 2.1 | tiempo entre entradas (de cualquier lado) |
| jaw_alternation | 1.0 | 100% de las entradas cambian de lado |
| jaw_reach | 0.70 | la pinza llega a 0.30R del centro |
| jaw_in_s | 0.6 | desde que empieza a entrar hasta el máximo |
| jaw_active_s | 1.8 | cuánto tiempo está adentro |
| jaw_overlap_pct | 0 | nunca las dos adentro a la vez |
`compare` usa `CHECKS_JAWS` cuando el target dice `"machine": "jaws"` (claps/arm_*/aim no aplican).

## Implementación: formats/crusher_jaws.py
- Engranajes a las 9 y a las 3; cada pinza = 2 brazos de 2 tramos, interpolados entre poses
  rest (">" pegado al aro) → mouth ("⊏" mirando al centro) → deep (máximo alcance) → closed (colapsa = aplastón) → rest.
- Sin gravedad, damping alto. Lo encerrado por el rombo se pulveriza y renace ×4 en un racimo compacto de color nuevo
  (huecos libres más cercanos) que sale hacia donde entra la otra pinza; cada racimo a otra altura (4 de 7 arriba).
- Tope por aplastón (`jaw_cap` 160) → exponencial al principio (1→4→10→13→25…), lineal después; lleno ~48 s → se rompe.
- Bolas lisas (`faces: False`): los ojos de los sprites (blanco/negro) se confunden con el gris de las pinzas.
- Diferencia con la referencia: allá el final hace zoom y vacía el círculo; acá se usa el final del canal (FULL → se rompe).
- Se mide hasta la ruptura (`--dur climax+1.3`): después aparecen textos/fragmentos que no son la máquina.
