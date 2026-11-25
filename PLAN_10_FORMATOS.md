# PLAN: 10 formatos andando para el domingo 29/11 (modo AHORRO)

El presupuesto de uso es limitado: cada token cuenta. Objetivo: 10 formatos que se vean bien y sean satisfactorios.
El refinamiento fino viene DESPUÉS, con datos reales de YouTube. Este plan está por encima de "hacerlo idéntico a la referencia".

## Los 10
| # | formato | estado | base que reutiliza | referencia |
|---|---|---|---|---|
| 1 | crusher_jaws | CERRADO | — | raw/nexusboxlab_crusher_9.6M.mp4 |
| 2 | punch | CERRADO | — | raw/satisfiedbounce_punch_refill.mp4 |
| 3 | press | en curso | — | raw/nexusboxlab_press_x4.mp4 |
| 4 | slam | revisión hecha | — | raw/neonbounce_bighammer_6.6M.mp4 |
| 5 | bighammer | nuevo | slam (×2, tope 2048 = FULL, bolitas confeti chicas fijas) | raw/neonbounce_bighammer_6.6M.mp4 |
| 6 | iris | nuevo | pinzas/cuña de crusher_jaws + aplastar ×2; 7 cuchillas en el borde que cierran juntas cada ~3.7 s, sin gravedad | raw/splitworks_iris_4.1M.mp4 |
| 7 | two_cones | nuevo | brazos desde el centro de punch, con agujas; gravedad leve, golpe que ACELERA 0.93→0.43 s, final "drop" (desaparece el aro y se dispersan) | raw/xbongobeats_2cones_5.3M.mp4 |
| 8 | escape | nuevo | aro giratorio con hueco; cada bola que escapa = 3 nuevas en el centro; lleno = FULL | reference/prototype/formats/escape.py |
| 9 | color_battle | nuevo | 4 brainrots, uno por cuadrante y color; cada uno multiplica a su ritmo; barra de % abajo; "PICK ONE NOW" en el frame 1; gana uno | capturas SatisfiedBounce "WHICH COLOUR WINS?" |
| 10 | brainrot_duel | nuevo | pantalla dividida, dos columnas de pisos: "1 brainrot ×10 vs 1.000 ×2", remontada programada al final, "Pick a side" | raw/bongballs_duel_5.8M.mp4 |

## Reglas de ahorro (obligatorias)
1. **Nada de código a medida por formato si se puede evitar.** Primero cargar lo común en `formats/` (arena, sizing, Pacer por tabla,
   colores por ola, estilo de bola, final, audio). Un formato nuevo = su `spec.json` + la pieza de máquina que le falte.
2. **Iterar en baja:** previews a 540x960, 15 fps, solo el tramo que se está tocando (10–20 s). Render completo 1080p solo para cerrar.
3. **Máximo 2 rondas de corrección por formato.** Después se cierra con lo que haya y se anota en spec.json qué quedó pendiente.
4. **Criterio de cierre (checklist, no perfección):**
   - el frame 1 se mueve, tiene una bola grande y legible y la pregunta en pantalla;
   - la máquina tiene un ritmo regular y legible, parecido a la referencia en la hoja lado a lado;
   - el contador sube con una curva creíble y llega al clímax entre los 45 y 55 s (o al final de la referencia);
   - colores por ola (manchas sólidas), sin bolas fuera de la arena ni texto cortado;
   - final claro: FULL / drop / derrame / ganador;
   - audio a -14 LUFS sin picos.
   Las métricas de `compare` se reportan pero NO bloquean en los formatos nuevos (6 a 10).
5. **Formatos 9 y 10 no tienen video original:** basarse en las capturas y en esta tabla; no salir a buscar más referencias.
6. **Sin preguntar entre formatos.** Cerrar, unir a main (PR) y seguir. Reportar solo al terminar cada tanda, con UNA hoja por formato.
7. Brainrots: el mismo sistema que punch ("X IS TAKING OVER", colores de ficha). Nada más elaborado hasta después del domingo.

## Calendario
- **Miércoles:** cerrar press y slam.
- **Jueves:** bighammer, iris, two_cones.
- **Viernes:** escape, color_battle, brainrot_duel.
- **Sábado:** pase rápido por los 10 (mismo estilo de HUD, títulos y metadatos), workflow de render + upload a YouTube en GitHub Actions.
- **Domingo:** primeros videos programados.
