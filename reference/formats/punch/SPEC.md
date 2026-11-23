# SPEC — PUNCH FILL (fuente: ref05 = SatisfiedBounce "CAN 1 BALL REFILL IT IN 60 SECONDS?", 1.2M y 2.8M vistas)

Hojas: `reference/sheets/ref05.jpg`, `ref05_zoom_0-4s.png`, `ref05_zoom_26-30s.png`.

## Lo que se ve (medido frame a frame)
- Fondo negro azulado, **aro blanco fino**, **arco amarillo** por fuera del aro que crece (progreso).
- Pivote central con **2 brazos independientes** (varilla gris fina + **guante/martillo gris grande** en la punta, cerca del aro).
- **Las varillas atraviesan las bolas** (no chocan); solo los guantes golpean.
- Los brazos se abren mucho y se cierran como un aplauso en distintos puntos del círculo.
- **Al chocar los guantes, las bolas atrapadas en la cuña entre los dos brazos se duplican** ("×2" al principio, "+82", "+94" después).
  Si no hay bolas en la cuña, no suma nada. Nada se multiplica por existir.
- Cada golpe trae un **color nuevo** que se propaga por la pila como una ola (la "infección").
- Bolas chicas y brillantes (≈7.5 px de radio a 1080), miles (3.757 al final).
- Contador grande "**N BALLS**" debajo del aro. Título blanco + línea amarilla arriba.
- Curva: 2→4→13→32→64→128 (10 s) → 600 (22 s) → 1.000 (34 s) → 1.500 (44 s) → lleno. Exponencial al principio y casi lineal después (+80 a +300 por golpe).
- Final: "IT GETS THIS FULL..." + cartel "FULL!" con el círculo completamente lleno.
- Sonido: pocos golpes por segundo (1-2 onsets/s), graves (centroide 550-1000 Hz): **el golpe del guante manda**. Sin lluvia saturada.

## Implementación (`formats/punch.py`)
- Ciclo de aplauso: abrir → (con las nacidas ya caídas) el Pacer elige centro y apertura → cerrar → CLAP.
- Pacer honesto: la regla "duplica lo atrapado" nunca cambia. Solo elige **dónde** y **cuánto abrir**
  (cuenta las bolas del sector con un histograma) para seguir la curva y llegar lleno entre el seg 46 y 51.
- Twist brainrot: cada ola de color es un brainrot (voz propia al golpear); el que tiene el color en el lleno gana.
