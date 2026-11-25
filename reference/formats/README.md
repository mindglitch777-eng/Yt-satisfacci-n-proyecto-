# Catálogo de referencias (grabaciones del usuario, Nov 2026)

Los mp4 están en `reference/videos/` (fuera de git por tamaño); las hojas de frames y el análisis de sonido, en `reference/sheets/`.

| ref | canal / formato | mecánica real | estado |
|---|---|---|---|
| ref01 | 27Balls: polígonos que se achican ("wait till end") → espiral con bola x100000 | una bola recorre polígonos que pierden lados; al final, espiral y explosión de bolas | pendiente |
| ref02 | Splitworks: cuchillas curvas que se abren y cierran | las cuchillas cierran sobre las bolas y **las parten en 2** | pendiente |
| ref03 | Merge con caras (papas futbolistas, "¿Quién gana el Balón de Oro?") | caen fichas desde un tubo; dos iguales se fusionan en el siguiente nivel; LEVEL N + SCORE | pendiente (= merge evolutivo brainrot) |
| ref04 | SatisfiedBounce "Will the ball multiply?" | aros concéntricos con multiplicadores x2/x4/x50; una bola rompe la pared; el final se llena | pendiente |
| ref05 | SatisfiedBounce "CAN 1 BALL REFILL IT IN 60 SECONDS?" | **2 brazos con guante; el aplauso duplica lo atrapado en la cuña** | **hecho: `formats/punch.py`** |
| ref06 | Badbounce: octógono con zonas x10 / x20 / x3 / split / turbo + barra giratoria | la bola cae en zonas que la multiplican | pendiente |
| ref07 | Dos garras en forma de C que se cierran en el centro | lo atrapado entre las garras se multiplica y cambia de color | pendiente |
| ref08 | blend3dfy: disco 3D de bolas que forma figuras | ondas de bolas en 3D (fuera del nicho 2D) | descartado |
| ref09 | Neon Bounce: pistones grises desde abajo | el pistón aplasta contra el piso → +bolas multicolor | pendiente |
| ref10 | BonnoBeats: dos púas cónicas que rotan | lo que pinchan las púas se multiplica | pendiente |
| ref11 | NexusBoxLab: mandíbulas cuadradas que se cierran al centro | lo atrapado en el cuadrado central se multiplica; color nuevo | pendiente |

Patrón común: **la máquina se cierra sobre las bolas y SOLO lo atrapado se multiplica**; aro blanco fino; bolas chicas y brillantes;
color nuevo por evento que se propaga; contador "N BALLS"; final completamente lleno.
