# PUNCH: lo que la referencia HACE, medido (no supuesto)

Fuente: `reference/videos/raw/satisfiedbounce_punch_refill.mp4` (SatisfiedBounce, "CAN 1 BALL REFILL IT IN 60 SECONDS?", 2.8M).
Medido con `tools/motion/measure.py` a 30 fps durante 40 s, en unidades del aro (R = radio).
Objetivo numérico: `target.json`. Para validar un render: `tools/motion/compare.py` (tiene que dar PASA).

## Las 6 leyes del movimiento

**1. NO hay gravedad (o es despreciable).**
La bola sola flota 0.6 s en la parte de arriba sin bajar (y = −0.53R → −0.51R). Masas enteras quedan pegadas
ARRIBA del círculo durante 0.8 s (t = 8.2–9.0 s). La masa de bolas está en la mitad de arriba el 52% del tiempo.
Las bolas se mueven SOLO porque las empujan los brazos o porque salen disparadas de un golpe. Después frenan
(amortiguación alta) y se quedan apiladas donde quedaron. Es una escoba, no una pecera.
→ `gravity ≈ 0`, `damping` alto (las bolas sueltas frenan en ~0.5 s), fricción bola-bola alta.

**2. Los dos brazos se mueven, en tijera.**
Correlación de velocidad entre brazos = **−0.52**: se cierran uno contra el otro como dos manos que aplauden.
Cada brazo está en movimiento ~50% del tiempo. Velocidad media 150°/s, picos de 400–650°/s, y frenan casi en seco.
Entre golpes se abren mucho (hasta 180°) para reubicarse.

**3. El golpe apunta a la bola.**
En los primeros golpes los guantes se juntan justo donde está la bola: a 13–17° en la mayoría de los casos.
Con muchas bolas, la cuña apunta a una porción de la masa.

**4. El ritmo se ralentiza (ritardando).**
Intervalo entre golpes: **0.7 s al principio → 1.3 s al final**. Guantes juntos en el golpe: **0.22 s**.
Es lo contrario a "acelerar la tensión": al principio es rápido y juguetón, al final cada golpe pesa más.

**5. Regla de multiplicación: lo que queda atrapado en la cuña se duplica.**
Conteo leído del contador en pantalla:

| s | 0 | 2 | 4 | 6 | 8 | 10 | 12 | 14 | 16 | 20 | 24 | 28 | 32 | 36 | 40 | 44 |
|---|---|---|---|---|---|----|----|----|----|----|----|----|----|----|----|----|
| bolas | 2 | 4 | 13 | 32 | 64 | 128 | 251 | 325 | 349 | 519 | 677 | 764 | 933 | 1056 | 1238 | 1492 |

- Fase 1 (0–12 s): **exponencial**, ×2 cada ~2 s. Todas las bolas entran en la cuña, así que todas se duplican.
- Fase 2 (12 s en adelante): **lineal**, +70 a +90 por golpe ("+74", "+82", "+91" en pantalla), unas 40 bolas/s.
  La cuña tiene capacidad fija, y por eso el crecimiento se vuelve lineal **solo, sin forzarlo**.
- Cada golpe hace nacer las bolas nuevas en un **color nuevo** (rojo → azul → amarillo → verde → …), que inunda el círculo como una ola.

**6. Las bolas se achican a medida que hay más.**
r/R = **0.077 con 1 bola** (grande, legible en el frame 1) → ~0.05 con 2–5 → ~0.03 con 60 → **0.008–0.015 al final**.
Ajuste: `r/R ≈ 0.08 · N^-0.23`. Cada bola nace con el tamaño que le corresponde al conteo del momento.

## Qué tenía mal punch_v4 (medido con la misma herramienta)

| métrica | referencia | punch_v4 | problema |
|---|---|---|---|
| intervalo de golpes al principio | 0.7 s | 1.5 s | arranca lento y "renguea" (alterna 0.9 s / 2.4 s) |
| guantes juntos | 0.22 s | 0.42 s | el golpe se queda pegado: pierde el "clap" |
| correlación entre brazos | −0.52 | +0.19 | barren juntos en vez de aplaudir |
| % de tiempo que se mueve cada brazo | 45 / 56 | 36 / 67 | uno hace todo, el otro casi quieto |
| primera bola r/R | 0.077 | 0.018 | un punto invisible en el frame 1 → hook muerto |
| gravedad | ~0 | 700–950 px/s² | todo cae al fondo: no es lo que hace la referencia |

## Cuidado al medir grabaciones de TikTok
Hay tramos grabados a **2x** (mantener apretado). `measure.py --tiktok` los detecta y los excluye.
Si se mide un tramo a 2x, todo sale el doble de rápido: puede ser una de las causas de que "no se entendía la velocidad".
Tramos a 2x en las grabaciones: neonbounce 0, badbounce 1.5–2.5 s, nexusbox_figure8 10.5–19 s,
punch_refill 41.5–42.8 s, will_multiply 26–53 s, potatoes 28–36 s.
