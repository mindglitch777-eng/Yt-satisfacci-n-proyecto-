# Satisfy Engine — Shorts de física 100% código

Genera Shorts verticales 1080x1920 con física real, audio sintetizado (sin copyright) y metadatos listos para subir.
Corre solo en GitHub Actions: no depende de Claude Code.

```
python run.py --format crusher|escape|mix --count 4
python upload.py   # requiere YT_CLIENT_ID / YT_CLIENT_SECRET / YT_REFRESH_TOKEN
```

## Piezas
| Archivo | Qué hace |
|---|---|
| `engine/core.py` | física (pymunk), render neón (cairo), audio procedural, `Pacer` |
| `engine/variation.py` | genoma por video + anti-repetición (distancia vs últimos 30 en `history.json`) |
| `formats/crusher.py` | "Can 1 ball fill it in 60s?" — martillo/péndulo, cada golpe xN |
| `formats/escape.py` | "Every escape = N balls" — aro giratorio con hueco |
| `.github/workflows/daily.yml` | render diario + subida programada + commit del historial |

## Pacer (el truco clave)
El clímax "FULL!" no es azar: el multiplicador se ajusta en vivo para seguir una curva exponencial
y llegar lleno entre el seg 50 y 57. Cada video llega al final → retención alta, nunca se "corta" aburrido.

## Agregar un formato
Heredar `BaseSim`, implementar `setup / update / draw`, sumar su espacio de parámetros en `SPACE` y sus títulos en `TITLES`.

## Roadmap de formatos (vistos en la investigación)
- **merge / suika con caras** (fútbol: "¿Quién gana el Balón de Oro?") → cruce directo con Futbol Edition
- **multiplicador por zonas** (hexágono con salidas x10 / x20 / split)
- **anillos concéntricos que se rompen** ("Will the ball multiply?")
- **zigzag de polígonos** (triangle → hexagon → … "wait till end")
- **color battle** (4 colores, ¿cuál gana?) → comentarios masivos
