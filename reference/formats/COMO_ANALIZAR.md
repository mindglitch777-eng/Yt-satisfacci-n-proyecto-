# Cómo analizar una referencia (aprendido a los golpes, Nov 2026)

## Por qué me equivoqué dos veces (punch y crusher_jaws)
1. **Miré cuadros chicos y recortados.** Recorté solo el círculo: en crusher_jaws las pinzas pasan la mitad del ciclo
   AFUERA del aro, y eso quedó fuera de la imagen. Con tiras de 160 px los engranajes de cuadros vecinos se pegaban.
2. **Medí solo adentro del círculo** (detector con d < 0.9R): el número confirmó mi idea equivocada en vez de corregirla.
   Un PASA solo dice que el render se parece a lo que el detector ve, no que la mecánica sea la misma.
3. **Partí de una descripción escrita** (MEDIDAS/SPEC de otra sesión) y busqué confirmarla en los frames,
   en vez de describir los frames desde cero.

## Método (en este orden, antes de escribir una línea de código)
1. **Cuadro entero** (pantalla completa, no recortada al aro), **5 fps, con la hora impresa**, cuadros de ≥ 300 px,
   12 cuadros por hoja (2.4 s). Una hoja del primer ciclo + una de otro ciclo más adelante + una del final.
   `ffmpeg -ss T -t 2.4 -i V -vf "fps=5,scale=300:-1,drawtext=text='%{pts\:hms}':x=5:y=5:fontsize=16:fontcolor=yellow,tile=6x2:padding=4:color=white" -frames:v 1 hoja.png`
2. **Describir cada pieza que se mueve, por separado**: dónde está el eje, hacia dónde gira, si sale del aro,
   si las piezas se mueven a la vez o por turnos. Escribirlo ANTES de mirar números.
3. **Contar las bolas a mano en 2 golpes** (antes/después) para sacar la regla (×2, ×4, +N).
4. **Recién ahí** medir con `tools.motion` para el ritmo y las velocidades. Si el detector no ve una parte del
   movimiento (afuera del aro, tapado por bolas), anotarlo en el SPEC como límite.
5. **Mostrarle al usuario la descripción en 5 líneas antes de programar.** Corregir una frase cuesta nada;
   corregir un formato programado cuesta horas.

## Atajos para crear formatos más rápido
- Todas las referencias comparten: aro, bolas del mismo tamaño, color nuevo por golpe, contador, final FULL → rompe
  (`formats/arena.py` ya lo tiene). Un formato nuevo = solo la máquina + su regla de captura.
- Las máquinas vistas hasta ahora son 3 tipos de movimiento: **rotación continua** (two_cones, punch), **vaivén**
  (bighammer, crusher_jaws, iris) y **pisos con vida** (duel). Conviene una pieza reutilizable por tipo.
