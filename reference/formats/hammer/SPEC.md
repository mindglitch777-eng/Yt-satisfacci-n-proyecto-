# OBSOLETO: reemplazado por `formats/punch.py` (ver ../punch/SPEC.md). Se escribió sin referencias reales y no coincide con el nicho.

# SPEC — Martillo aplastador (v2)

Fuente: descripción literal del usuario (Nov 2026) + títulos de referencia ("Ball Crushing, Splitting & Multiplication").
Pendiente: grabaciones reales en esta carpeta → correr `python -m tools.refstudy` y ajustar este SPEC.

## Mecánica
- Arena circular. Martillo con pivote en el centro (giro o péndulo) cuya cara llega casi a la pared.
- Las bolas caen por gravedad y se apilan contra la pared.
- **El martillo APRIETA una bola contra la pared** → la bola se aplasta (animación squash) → sobrevive y
  **nacen 2 más** (+2) detrás del martillo. Golpe en el aire = solo rebote, no multiplica.
- Regla fija y honesta en pantalla: "EVERY SQUASH = +2". El Pacer no cambia la regla:
  regula la velocidad del martillo y, si un equipo va pasado del guion, esa bola "se escurre" (sale disparada sin aplastarse).

## Sonido por evento
| evento | sonido |
|---|---|
| aplastado | golpe metálico grave + squish (ruido filtrado que cae de pitch) |
| multiplicación | pop brillante + nota pentatónica (sube con el llenado) + voz brainrot ocasional |
| bola contra bola | clack de canica (lluvia granular cuando son muchos) |
| bola contra pared | toque propio de cada ficha |
| clímax | 0.3 s de silencio → boom + acorde + voz del ganador |
Sin música de fondo.
