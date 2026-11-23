# SPEC — PUNCH FILL (fuente: ref05 = SatisfiedBounce "CAN 1 BALL REFILL IT IN 60 SECONDS?", 1.2M y 2.8M vistas)

Analizado CUADRO A CUADRO a 10 fps alrededor de dos golpes: `reference/sheets/ref05_clap_26s.png` y `ref05_clap_28s.png`.
(La primera versión se hizo mirando a 4 fps y se equivocó en la lógica; no volver a analizar a baja frecuencia).

## Ciclo real (≈2.5 s)
1. **Barrido**: un brazo da casi la vuelta entera alrededor del pivote. **Varillas y guantes son paredes**:
   empujan TODA la pila delante y la comprimen contra el otro brazo. La cuña se cierra de a poco.
2. **Las que se escapan** por detrás del brazo quedan sueltas en la zona barrida y se ven del color del PRÓXIMO golpe.
3. **Compresión → golpe**: los guantes chocan, destello blanco, la masa se pulveriza en polvo, aparece "+N".
4. **Apertura**: el brazo vuelve barriendo hacia atrás casi toda la vuelta y la masa renacida (color nuevo) sale
   en abanico detrás de él, inundando el círculo. Queda una "V" chica entre los brazos.
5. El brazo fijo también se corre, así que el golpe cae cada vez en un lugar distinto.
- Después del golpe todo el círculo queda de un solo color (el nuevo).

## Números medidos
- Curva: 2→4→13→32→64→128 (10 s) → 600 (22 s) → 1.000 (34 s) → 1.500 (44 s) → lleno. Al principio ×2/×3, después +80…+300.
- Sonido: 1-2 eventos por segundo y centroide espectral de 550 a 1000 Hz (todo grave/cálido; el golpe manda).
- Visual: aro blanco fino, arco amarillo de progreso, bolas de r≈7.5 px a 1080, "N BALLS" abajo, final "IT GETS THIS FULL..." + "FULL!".

## Implementación: `formats/punch.py`
- Fases `sweep` / `open`. El brazo que barre se calcula SIEMPRE relativo al fijo → el golpe cae exacto.
- Anti-tunneling: las bolas que cruzan la varilla en un frame vuelven al lado correcto.
- Compresión: si la cuña no tiene lugar, las que sobran se pulverizan (cuentan para el renacimiento).
- Renacimiento con grilla de ocupación (sin superposición), desde el borde hacia adentro.
- Pacer honesto: elige N (+N visible) y el ritmo del barrido para llenar entre el seg 46 y 51.
- Sonido validado con `tools.refstudy` contra ref05: centroide mediano ≈715 Hz (ref ≈760).
