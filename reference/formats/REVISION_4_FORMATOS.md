# Revisión de los 4 formatos contra su referencia (24/11/2026)

Fuente: artefacto "Brainrot Physics Muestras". Hojas a 5 fps (un ciclo) + 6 cuadros de todo el video, nuestro vs referencia.

## El error de fondo, que se repite en los 4

1. **Achicamos las bolas para meter miles y la referencia no.** Las referencias llenan con 1.000–3.700 bolas de tamaño medio y casi fijo.
   Nosotros terminamos con 5.400–9.800 bolitas diminutas, que en el celular se ven como ruido o arena, con huecos negros.
   → La capacidad y el tamaño de bola se COPIAN de la referencia (contar bolas en el frame "FULL").
2. **La curva de llenado está inventada.** Hay que copiar la curva de conteo de la referencia (leer el contador cada ~5 s).
   El Pacer sigue ESA tabla tiempo→bolas, no una exponencial genérica.
3. **El final se inventó igual para todos** ("se agrieta y se rompe"). Cada referencia tiene su final; ese es el payoff que el espectador espera.

## crusher_jaws (NexusBoxLab 9.6M), en orden de importancia
1. **Llenado 4 veces más lento.** La referencia está LLENA a los ~10 s (bolas medianas). Nosotros tenemos 88 bolas a los 9.5 s y llenamos a los 47 s.
   Los 20 s siguientes de la referencia son una **guerra de colores**: cada aplastón convierte una mancha grande en el color nuevo
   (territorios sólidos rojo/verde/amarillo/violeta). Ese mosaico es el contenido; el llenado es solo la intro.
2. **Las nuevas salen sueltas y tienen que salir en racimo.** En la referencia, las 4 nacen pegadas en un racimo compacto que deriva LENTO
   y junto hacia la otra pinza (0.6 → 1.6 s, cruza el círculo sin desarmarse). Las nuestras se dispersan apenas nacen.
3. **Final:** a los ~25 s el aro desaparece y la masa se DERRAMA fuera del círculo, en arco (cámara un poco más abierta). No "FULL + se rompe".
4. Bien: la forma de las pinzas, el engranaje, la alternancia izquierda/derecha y el ritmo de ~2.1 s.

## punch (SatisfiedBounce 2.8M); giro continuo aprobado por el usuario
1. **Guantes y bola inicial chicos.** Los guantes de la referencia son enormes (~0.2R de largo) y la primera bola mide r ≈ 0.077R.
   Los nuestros son la mitad: el choque pierde peso visual.
2. **Multiplicador que escala ×4, ×8, ×24, ×38:** los números grandes dejan de significar algo. La referencia: ×2 al principio
   y después "+74", "+81", "+82", "+94" (lo que entra en la cuña). Mostrar +N de lo atrapado.
3. Curva: la referencia hace 202 bolas a los 8 s, 498 a los 16, 759 a los 23, 1.027 a los 31, 1.366 a los 39 y FULL ~3.750 a los ~55.
   Nosotros vamos lentos al principio (145 a los 10 s) y explotamos al final (7.631). Seguir la tabla.
4. Bien: la cuña llena de un color sólido entre los brazos (a los 28 s se ve igual que la referencia) y el texto "X IS TAKING OVER".

## press ×4 (NexusBoxLab)
1. **Frame 1 muerto.** Nuestras barras están quietas de 0 a 1.2 s. En la referencia el ciclo ya está andando en el frame 1.
2. **Las barras corren por RIELES diagonales.** En la referencia hay 2 líneas largas en X que cruzan TODA la pantalla (más allá del aro),
   y las 4 barras deslizan por esos rieles: cerradas en X en el centro → se abren hasta el borde → vuelven. Ciclo de ~2.2 s, sin pausas.
   Los rieles son la mitad de la imagen y nos faltan.
3. **Distribución:** en la referencia las bolas están en TODO el círculo, también adentro del cuadrado. En la nuestra quedan en anillo con el centro vacío.
4. **Toma de color:** la referencia se llena a los ~19 s y después cada ciclo pinta casi todo el círculo de un color nuevo (cian → verde).
5. Final y tamaño: ver el error de fondo (7.681 bolitas vs ~1.500 medianas).

## slam (Neon Bounce, martillo gigante)
1. **Multiplicador:** la referencia es ×2 (2 → 4 → 8 … y FULL en exactamente 2.048 = 2^11). La nuestra usa ×4 y termina en 5.378. Volver a ×2 y a 2.048.
2. **El péndulo de la referencia oscila corto y rápido** (±20°, ~1.2 s) y la cabeza ES el bloque trapezoidal central.
   El nuestro hace más recorrido y es más lento.
3. **Bolas chicas y FIJAS desde el principio** (r ≈ 0.012R), de colores mezclados tipo confeti (cada bola de un color),
   y la pila sube plana como un líquido. Nosotros tenemos caras grandes que después se achican y manchas por color.
4. Curva de la referencia: 8 (0 s) · 100 (9 s) · 435 (19 s) · 853 (28 s) · 1.320 (38 s) · 1.799 (47 s) · 2.048 FULL (57 s). La nuestra va casi el doble de rápido.
5. Bien: el chorro hacia arriba de las bolas nuevas y los bloques laterales.

---

# Cómo encarar un formato nuevo: la FICHA antes del código

Antes de escribir código, se llena `reference/formats/<formato>/spec.json` mirando la referencia (hoja a 5 fps + contador).
El código solo lee la ficha. Si algo no está en la ficha, no se inventa: se mide.

```json
{
  "referencia": "reference/videos/raw/xxx.mp4",
  "arena": {"forma": "circulo", "R_px_1080": 460},
  "gravedad": 0,
  "maquina": {
    "tipo": "pinzas_borde | brazos_centro | barras_en_rieles | pendulo | iris",
    "piezas": [{"pivote": [0, -1.0], "largo_R": 0.45, "grosor_R": 0.04}],
    "movimiento": {"periodo_s": 2.1, "amplitud_deg": 90, "fase_entre_piezas": 0.5, "curva": "rápido al cerrar, lento al abrir"},
    "dibujo": "rieles en X que cruzan toda la pantalla, engranajes, guantes grandes, etc."
  },
  "bolas": {"r_inicial_R": 0.077, "r_final_R": 0.03, "capacidad_full": 3750, "colores": "uno por generación | confeti"},
  "multiplica": {"regla": "lo atrapado ×2 | ×4 por aplastada | +N de la cuña", "texto_popup": "×2 / +74"},
  "salen": "racimo compacto que deriva lento | abanico que llena la cuña | 4 chorros por los huecos | chorro hacia arriba",
  "curva_conteo": [[0, 2], [8, 202], [16, 498], [23, 759], [31, 1027], [39, 1366], [55, 3750]],
  "despues_de_lleno": "guerra de colores / toma de color / nada",
  "final": "aro desaparece y se derrama | FULL 2048 | drop",
  "texto_pantalla": ["CAN 1 BALL REFILL IT", "IN 60 SECONDS?"]
}
```

**Cómo se valida (tres pruebas, todas automáticas):**
1. `measure` + `compare` del movimiento (ritmo, gravedad, tamaño de bola).
2. **Curva de conteo:** el contador del render en esos mismos segundos, con ±20% de margen.
3. **Hoja lado a lado:** generar `sheets/<formato>_comparacion.jpg` con nuestro arriba y la referencia abajo, en los mismos
   segundos (ciclo de 0–2.4 s a 5 fps + 6 cuadros de todo el video), y mirarla ANTES de dar algo por terminado.

Orden de trabajo: ficha → máquina sola (sin bolas) hasta que el ciclo coincida en la hoja → 1 bola y la regla de multiplicar
→ curva de conteo → colores → final → sonido → recién ahí brainrots.
