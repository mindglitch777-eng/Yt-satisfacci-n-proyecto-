# Top 5: lógica real, vista en cuadros enteros a 5 fps (hojas en reference/sheets/top5/)
Reemplaza las descripciones de MEDIDAS_TOP5.md donde no coincidan.

## crusher_jaws (9.6M): lo que hice MAL y cómo es de verdad
- Cada pinza = **dos brazos en L articulados en un engranaje que está SOBRE el aro** (9 h y 3 h).
- Los dos brazos giran alrededor del engranaje **en tijera** (uno hacia arriba, el otro hacia abajo) y **atraviesan el aro**:
  abiertos quedan AFUERA del círculo, plegados hacia afuera; al cerrarse entran barriendo, forman un "⊐" abierto,
  después un rombo que encierra bolas, colapsan en una "T" (aplastón) y siguen hasta volver a salir del aro.
- **Las dos pinzas se mueven a la vez, en contrafase**: mientras una entra la otra está saliendo/afuera.
  Una pinza completa el ciclo cada ~2.2 s; aplastón cada ~1.1 s alternando izquierda/derecha.
- Regla: cada bola aplastada → **4** (1 roja → 4 verdes; 3 → 12). El racimo nuevo sale despedido hacia el centro.
- Mi versión: pinzas fijas que "se estiran" desde una pose de reposo adentro del aro, una por turno. Incorrecto.

## bighammer (6.6M)
- Gravedad. Péndulo central con cabeza trapezoidal enorme (casi toca el piso) + 2 bloques fijos a los costados.
- El péndulo va y viene; golpea el bloque derecho (~0.8 s) y el izquierdo (~2.0 s): lo que quedó entre la cabeza y el
  bloque se duplica (2 → 4 BALLS) en la junta, de color nuevo. Contador "N BALLS" abajo del aro.
- Es casi el `slam` que ya existe (que salió de otra grabación de Neon Bounce), pero ×2 y con los bloques más altos.

## two_cones (5.3M)
- Dos conos metálicos en varillas finas desde el centro. **Giran todo el tiempo en sentidos opuestos, simétricos**
  respecto del eje vertical: se encuentran alternando **abajo (0.0 s), arriba (0.8 s), abajo (1.8 s)**.
- Al encontrarse con bolas entre medio, explotan multiplicadas de color nuevo; el aro se tiñe de ese color un instante.
- Es el mismo movimiento que `punch` v8 con velocidades iguales (el choque cae siempre arriba/abajo).

## iris (4.1M)
- 7 cuchillas curvas con pivote en el aro. Giran todas juntas: se cierran hasta tocarse en el centro (~0.6 s),
  se abren hasta quedar pegadas al aro (~2.0 s). Ciclo lento.
- POR VERIFICAR (no visto todavía): qué le pasa exactamente a la bola atrapada (MEDIDAS dice "se parte en 2").

## duel (5.8M)
- Pantalla dividida: "1 BALL VS 1,000 BALLS — WHO REACHES THE BOTTOM FIRST?". Cada columna tiene pisos con un número
  (vidas): **cada rebote de una bola contra el piso le resta 1**; en 0 el piso se rompe y las bolas bajan multiplicadas
  (izquierda ×2 por piso, derecha ×10). Arriba: total de bolas y "FLOOR n/8". Abajo: "Pick a side in the comments".
