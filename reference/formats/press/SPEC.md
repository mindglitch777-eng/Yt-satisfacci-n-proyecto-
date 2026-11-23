# SPEC — PRENSA ×4 (fuente: reference/videos/raw/nexusboxlab_press_x4.mp4, NexusBoxLab, 90.7k likes)
Descripción del propio video: *"Cada vez que aplastás una pelota, aparecen 4 más."* Analizado a 10 fps (0-5 s y 14-28 s).

## Ciclo (~4 s)
1. **Abierto**: 4 barras metálicas (borde dorado del lado de adentro) forman un cuadrado girado 45° con huecos en las 4 esquinas.
   Las bolas sueltas rebotan y **derivan hacia el centro** (atracción radial suave).
2. **Cierre**: el cuadrado se achica (arranca suave, llega rápido) empujando lo de adentro; lo que no entra se aplasta.
3. **Golpe**: las barras se cruzan formando una **X** en el centro → destello → todo lo atrapado se pulveriza.
4. **×4**: por cada bola aplastada salen **4 nuevas**, en **4 masas compactas de color nuevo** disparadas por los 4 huecos
   (arriba, abajo, izquierda, derecha). Lo que estaba afuera no se multiplica y conserva su color.
5. **Apertura**: el cuadrado se abre (sale rápido, frena suave) y empuja todo hacia el borde.
- Con mucha masa: se acumula en las 4 esquinas contra las barras y en el centro.
- Final: el círculo se rompe y las bolas invaden la pantalla (en la referencia); acá: grietas → se parte → caen.

## Implementación: `formats/press.py` (base común `formats/arena.py`)
- Barras cinemáticas que se trasladan (no rotan). Captura = dentro de las 4 normales.
- Crecimiento exponencial natural (×~1.8 por golpe, sin forzar): 1 → 4 → 16 → … → ~7.600 → FULL a los ~47 s.
- `center_pull` y `t_wait` regulan cuánto se rellena el centro entre golpes (y por lo tanto la duración).
