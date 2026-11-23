# Los 5 más vistos del nicho (ago–nov 2026): mecánica medida

Videos originales (sin la interfaz de TikTok y sin tramos a 2x) en `reference/videos/raw/`.
Medidos con `tools/motion/measure.py` y revisados cuadro a cuadro a 4 fps. Cada formato tiene su `target.json`.

**Aviso sobre la herramienta:** `measure.py` detecta brazos que salen del CENTRO.
Sirve para punch y two_cones. En crusher_jaws (mandíbulas en el borde), iris (cuchillas en el borde)
y bighammer (péndulo + bloques fijos), las métricas `claps`, `arm_*` y `aim` no son válidas.
Ahí valen `machine_period_s`, `ball_r_*` y `mass_in_top_half_pct`, más lo escrito acá.
Antes de usar `compare` en esos formatos, hay que agregarle a `measure.py` el detector de su máquina.

| formato | vistas | máquina | gravedad (% masa arriba) | ritmo | multiplicación |
|---|---|---|---|---|---|
| crusher_jaws (nexusboxlab) | 9.6M | 2 mandíbulas articuladas en el borde (9 y 3 h) | NO (62%) | ciclo de 2.1 s; mandíbulas alternadas → un aplastón cada ~1 s | aplastar = duplicar |
| bighammer (neon.bounce) | 6.6M | péndulo central + yunque y rampas grises fijos | SÍ (20%) | péndulo 1.2 s; ×2 cada ~2 s al principio | ×2 por golpe; termina en 2048 = 2^11 "FULL!" |
| two_cones (xbongobeats) | 5.3M | 2 conos/agujas en varillas desde el centro, en tijera | leve (39%) | se aceleran: golpe cada 0.93 s → 0.43 s | al chocar los conos |
| punch (satisfiedbounce) | 2.8M | 2 brazos con guantes en tijera | NO (52%) | se frenan: golpe cada 0.7 s → 1.3 s | ×2 lo atrapado, después +70–90 |
| iris (splitworks) | 4.1M | 7 cuchillas curvas en el borde (diafragma de cámara) | NO (72%) | se cierra cada ~3.5–4 s, lento y pesado | cada bola aplastada se parte en 2 |
| duel (bongballs) | 5.8M | carrera en pantalla dividida, pisos que se rompen | — | por piso | 1 bola ×10 vs 1.000 bolas ×2 por piso |

## crusher_jaws (nexusboxlab, 9.6M): el más visto de los que multiplican
- Dos pinzas de 2 tramos montadas en engranajes sobre el aro, a las 9 y a las 3. Cada pinza ENTRA hacia el centro,
  se cierra formando un rombo/caja que encierra bolas, las aplasta y se retira abierta. Las dos pinzas se alternan.
- Sin gravedad: las bolas flotan cerca del centro, donde las dejó la última explosión.
- 1 bola roja → aplastada → racimo verde (~6) → azul → … Color nuevo por generación, que se expande como una mancha.
- r/R de la bola: 0.04 al principio → 0.008 al final (se achican).
- Final: la cámara hace ZOOM hacia la masa (se sale del círculo) y los ciclos empiezan a VACIAR el círculo (aplastar = polvo).
  Es un final inverso al "FULL": tensión al revés.

## bighammer (neon.bounce, 6.6M)
- CON gravedad. Péndulo central (pivote arriba del yunque) que va y viene cada 1.2 s, más un yunque trapezoidal y dos rampas grises fijas.
  Las bolas caen y quedan en el yunque, y el martillo las aplasta contra él.
- Conteo (texto "N BALLS" abajo): 2 (0 s) · 15 (5 s) · 61 (10 s) · 152 (15 s) · 344 (21 s) · 579 (26 s) · 794 (31 s) ·
  1.025 (36 s) · 1.320 (41 s) · 1.564 (47 s) · 1.799 (52 s) · **2.048 FULL! (57 s)**.
  Al principio ×2 cada ~2 s (4 → 8 → 16), después crece casi lineal (~50 bolas/s). La capacidad es justo 2^11.
- Las bolas tienen tamaño fijo (r/R ≈ 0.015) y se apilan con gravedad hasta tapar las rampas.

## two_cones (xbongobeats, 5.3M)
- Dos agujas/conos en la punta de varillas finas que salen del centro. Cada uno gira por su cuenta (se mueven el 90% del tiempo, ~200°/s).
- Gravedad leve: las bolas se juntan abajo. Las agujas bajan y "pican" el montón.
- Ritmo que ACELERA (0.93 s → 0.43 s), sincronizado con un beat. El aro cambia de color en cada golpe (flash).
- Final: círculo lleno → el aro desaparece y las bolas se dispersan por toda la pantalla ("wait for the drop").

## iris (splitworks, 4.1M)
- 7 cuchillas curvas con pivote en el aro que se cierran juntas hacia el centro, como el diafragma de una cámara, y se vuelven a abrir.
- Sin gravedad (72% de la masa arriba): las bolas flotan.
- Cobertura del centro por las cuchillas (cada 0.5 s): picos de cierre en ~1.5, ~5, ~9 y ~13.5 s → **un cierre cada ~3.5–4 s**.
  Desde los 16 s el círculo está tan lleno que las cuchillas ya no se ven libres.
- Cada bola atrapada en el cierre se parte en 2. Colores nuevos.
- Final: lleno, con polvo/humo de bolas aplastadas sobre las cuchillas.

## duel (bongballs, 5.8M): otro género
- Pantalla dividida, dos columnas de "pisos" (floor X/8). Izquierda: 1.000 bolas ×2 por piso. Derecha: 1 bola ×10 por piso.
- Contadores grandes arriba (16.000 → 128.000 vs 1 → 10.000.000). La izquierda arranca ganando por mucho y la derecha remonta al final.
- Final: cartel "1 BALL WINS! The other side had 91% of its last floor done". Texto fijo "Pick a side in the comments".
- Es la plantilla ideal para "brainrot vs brainrot": dos fichas, dos reglas, se elige bando, remontada programada.

## Lo que comparten (reglas para cualquier formato nuevo)
1. Una sola bola grande y visible en el frame 1, ya en movimiento.
2. Máquina con ritmo regular y legible (entre 0.4 y 4 s por golpe), nunca caótico.
3. Color nuevo por generación: cada golpe se ve como una "ola".
4. Final anunciado y cumplido: FULL / drop / remontada / vaciado.
5. La gravedad depende del formato. Se mide, no se supone: 3 de 5 NO tienen gravedad.
