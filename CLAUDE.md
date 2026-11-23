# BRAINROT PHYSICS — fábrica de Shorts satisfying 100% código

## Objetivo
Canal de YouTube Shorts que crece en **vistas y suscriptores** y llega a **monetizar** (YPP).
Videos de física "satisfying" generados por código, protagonizados por **brainrots como fichas**:
ese es el diferencial frente a los canales de pelotitas genéricas.
El sistema corre solo (GitHub Actions). Claude Code lo construye y lo mejora, pero no hace falta para operarlo.

## Referencias del nicho (TikTok, Nov 2026)
SatisfiedBounce (1.2M a 3.2M en sus mejores videos), Splitworks (3.9M), 27Balls (15M), NexusBoxLab, Badbounce, Neon Bounce.
Mecánica común: **1 bola → una máquina la golpea → se multiplica → contador → pregunta "¿se llena en 60s?"**.
Formatos vistos: martillo o péndulo que multiplica, aro giratorio con hueco ("every escape = 3 balls"),
anillos concéntricos que se rompen ("will the ball multiply?"), merge estilo suika, zigzag de polígonos,
color battle (4 colores, ¿cuál gana?), hexágono con zonas x10/x20/split, prensa hidráulica, blades/aspas.

## REGLA: fidelidad a las referencias (obligatoria desde Nov 2026)
- **Ningún formato se programa "de memoria".** Antes de escribirlo hay que tener referencias reales
  (grabaciones o capturas) en `reference/formats/<formato>/` y una ficha `SPEC.md` con la mecánica exacta:
  qué hace la máquina, qué le pasa a la bola (aplastada, golpeada, partida), cuántas salen, dónde aparecen,
  ritmo de la cámara, textos en pantalla y qué suena en cada evento.
- `python -m tools.refstudy <video>` saca la hoja de frames + el análisis de sonido (golpes por segundo,
  brillo y volumen en el tiempo) para armar el SPEC. Las capturas que manda el usuario mandan sobre cualquier suposición.
- La descripción del usuario se toma literal. Ej.: "el martillo aprieta la bolita y salen dos más" = aplastar
  contra la pared → la bola sobrevive y nacen +2; NO es "golpe en el aire = multiplicar".
- Desde este container TikTok está bloqueado y YouTube pide verificación anti-bot: las referencias
  las sube el usuario al repo (o se habilita el host en el entorno).

## Brainrots como fichas (núcleo del diferencial)
- Cada ficha es un personaje brainrot (estilo Tralalero Tralala, Tung Tung Sahur, Bombardiro Crocodilo, Ballerina Cappuccina, etc.).
- **Dibujar versiones propias en vector/código** (no descargar ni copiar imágenes de terceros): así evitamos reclamos y el "reused content".
- Cada ficha tiene una **identidad mecánica**: masa, rebote, tamaño, sonido propio y un "poder" (se divide en 2, explota, atrae, rebota doble).
- Formatos con fichas: **batalla de brainrots** (¿cuál sobrevive o llena primero?), **merge evolutivo** (brainrot chico → final form),
  **torneo por llaves** (serie de videos → suscripción para ver al siguiente), **"elegí tu brainrot"** en los primeros 2s (comentarios masivos).
- Nombre visible sobre cada ficha y barra de "quién va ganando" → el espectador elige bando y se queda hasta el final.

## Arquitectura
- `engine/`: física (pymunk o Box2D, con substeps y anti-tunneling), render (skia-python o cairo) con glow, motion blur liviano,
  partículas, camera shake y zoom en el clímax, y encode ffmpeg (1080x1920, 60fps si el tiempo de render lo permite).
- `formats/`: un archivo por formato. Interfaz `setup / update / draw / events`.
- `characters/`: fichas brainrot (sprite vectorial + stats + sonido).
- `audio/`: motor de sonido (ver abajo).
- `variation/`: genoma de parámetros + anti-repetición.
- `research/`: scripts con la YouTube Data API (canales del nicho, vistas/día, títulos ganadores).
- `growth/`: YouTube Analytics API → retención y suscriptores por video → reajuste de pesos del genoma.
- `.github/workflows/`: render diario + upload programado + commit del historial.
- Prototipo previo en `reference/prototype/` (crusher/escape + Pacer + anti-repetición): usarlo como referencia, NO como base obligatoria; la calidad tiene que ser muy superior.

## Sonido (prioridad alta: es la mitad del "satisfying")
- Capas: impacto (transiente) + tono musical (escala pentatónica, la nota depende de la velocidad del golpe) + cola de reverb.
- Pitch y densidad que **suben con la tensión**. Silencio de 0.3s antes del clímax y después un drop o explosión.
- Limitador de eventos por frame + agrupación (granular): miles de choques tienen que sonar a "lluvia", nunca a saturación.
- Sonido propio por ficha brainrot (sintetizado o grabado por nosotros, nunca audio con copyright).
- **Sin música de fondo.** Solo sonidos de satisfacción: martillo, aplastado (squish), multiplicación (pop),
  choques entre bolas (clacks tipo canica), rebotes en la pared, y las voces de los brainrots.
- Voces brainrot ("tung tung tung sahur", "tralalero tralala", "ballerina cappuccina") sintetizadas por nosotros
  (espeak-ng + procesado), nunca el audio original de los memes.
- Master: compresor, normalizado a -14 LUFS (estándar YouTube).

## Reglas de viralidad (en el código, no a mano)
- **Hook en el frame 1**: pregunta grande + algo ya en movimiento. Nada de intro.
- **Pacer**: el clímax se programa (lleno o victoria entre el seg 45 y 55) con una curva de tensión exponencial; nunca queda librado al azar.
- **Near-miss**: momentos de "casi pierde" generados a propósito.
- **Loop**: que el último frame empalme visualmente con el primero (rewatch = más vistas).
- Contador grande, barra de progreso, popups "+N", y CTA final textual del tipo "¿quién gana el próximo? → suscribite".
- Series numeradas (Torneo #1, #2…) para convertir vistas en suscriptores.

## Monetización: cumplir con YouTube ("contenido inauténtico / repetitivo")
Ser producción masiva con plantilla es el mayor riesgo para entrar al YPP. Para mitigarlo:
- La anti-repetición tiene que cambiar mecánica, personajes, cámara, audio y narrativa, no solo los colores.
- Cada video necesita un "evento" único: una ficha nueva, un poder distinto o un giro.
- Títulos y descripciones variados y honestos; sin clickbait falso.
- Publicar 2 o 3 por día, no 20.

## Anti-repetición
Genoma = formato, fichas, poderes, arena, máquina, paleta, cámara, timbre, escala musical, título y curva del Pacer.
Distancia contra los últimos 50 publicados en `history.json`: si un genoma queda demasiado cerca, se descarta.
`growth/` va pesando los genes según retención y suscriptores ganados (bandit simple).

## Calidad: definición de "terminado"
- Antes de dar algo por hecho, renderizar una muestra, sacar 6 frames y revisarlos (nada de bolas fuera de la arena, texto cortado ni fichas superpuestas).
- Revisar el audio: sin clipping, a -14 LUFS.
- Un video de 60s se renderiza en menos de 3 min en un runner de GitHub.
- Secrets solo por variables de entorno: `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN`, `YT_API_KEY`.

## Plan de construcción (en este orden)
1. Motor base sólido + 1 formato (martillo multiplicador) con 3 fichas brainrot y el motor de sonido completo.
2. Batalla de brainrots + merge evolutivo.
3. Variación + anti-repetición + metadatos.
4. Workflow de render y upload.
5. Research con la API + growth loop.
6. El resto de los formatos.

## REGLA: el movimiento se MIDE, no se supone (Nov 2026)
- Las grabaciones originales están en `reference/videos/raw/` (11 videos). Mirar hojas de frames no alcanza:
  la lógica del movimiento (quién se mueve, a qué velocidad, con qué ritmo, si hay gravedad) se saca con números.
- `python -m tools.motion.measure VIDEO --tiktok -o x.json` mide ritmo de golpes, tijera entre brazos,
  velocidad, tamaño de bola y gravedad efectiva, y excluye los tramos grabados a 2x.
- Cada formato tiene `reference/formats/<formato>/target.json` (métricas de la referencia) y `MEDIDAS.md` (las leyes del movimiento).
- **Un formato no está terminado hasta que `python -m tools.motion.compare target.json render.json` da PASA.**
  Si una métrica falla, se corrige el código de movimiento. No se cambia la tolerancia y no se "interpreta".
- PUNCH: leer `reference/formats/punch/MEDIDAS.md` antes de tocar `formats/punch.py`
  (sin gravedad, brazos en tijera, golpe que apunta a la bola, ritmo de 0.7 s a 1.3 s, ×2 de lo atrapado, bola que se achica).
- Formatos nuevos: primero medir la referencia y escribir su `target.json`; si `measure.py` no cubre la mecánica
  (aspas, aro con hueco, merge), primero se le agregan las métricas que falten y después se programa.
