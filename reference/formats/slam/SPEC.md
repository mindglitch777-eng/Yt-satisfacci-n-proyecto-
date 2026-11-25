# SPEC — MARTILLO GIGANTE (fuente: reference/videos/raw/neonbounce_hammer_fill.mp4, Neon Bounce, 157.7k likes)
Descripción del propio video: *"El martillo gigante aplastando. ¡Mirá cómo las pelotas se multiplican!"*
Analizado a 10 fps (0-5 s y 9-11 s) + frames sueltos a 0.5/20/40/55 s.

## Mecánica
- **Gravedad**: las bolas caen y se juntan en el piso. Empieza con **2 bolas** ("2 BALLS").
- **Martillo-péndulo**: varilla desde el centro + cabeza = bloque gris grande cerca del piso. Oscila suave de lado a lado.
- **Dos yunques fijos** (bloques grises): abajo-izquierda y a la derecha.
- En cada pasada el martillo **barre el piso** hacia un yunque; lo que queda **apretado en la rendija** se aplasta
  (destello) y sale **multiplicado en CHORRO hacia arriba** por la rendija, de un color nuevo; después cae y se apila.
- Crecimiento: 4 → 16 → 61 → 152 → 338 → … ≈ lineal después (la rendija tiene capacidad fija). 1.917 bolas a los 55 s.
- La pila de colores sube por encima de los bloques hasta llenar el círculo. Contador "N BALLS" abajo.

## Implementación: `formats/slam.py` (base `formats/arena.py`)
- Yunques = polígonos estáticos (sector anular); martillo = cuerpo cinemático que rota (seno, se queda un instante apretado).
- Aplastado = bolas en la rendija entre la cabeza y el yunque cuando se cierra; capacidad fija (`gap_deg`).
- ×4 de lo aplastado, en chorro hacia el centro/arriba. Lleno ~49 s → grietas → se rompe.
