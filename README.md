# BRAINROT PHYSICS

Shorts de física "satisfying" 100% código, protagonizados por fichas brainrot. Ver `CLAUDE.md` para el plan completo.

```bash
pip install -r requirements.txt          # + ffmpeg; Linux: apt-get install libegl1 espeak-ng
python render.py --seed 2                # -> out/punch_2.mp4 (formato por defecto: punch)
python -m tools.qa out/punch_2.mp4      # hoja de 6 frames + LUFS / true peak
python -m tools.sheet out/chars.png      # hoja de personajes
```

## Estado (paso 1 del plan: hecho)
| Pieza | Archivo |
|---|---|
| Física pymunk (substeps, anti-tunneling duro, fichas que nunca se quedan quietas) | `engine/sim.py` |
| Render skia: aro neón horneado, sprites, motion blur liviano, partículas, popups "+N", camera shake/zoom | `engine/gfx.py`, `engine/sim.py` |
| Pacer: lleno programado (seg 44-50), guion de cambios de líder y near-miss | `engine/pacer.py` |
| Sonido: impacto + tono pentatónico por velocidad + reverb, tensión sube el pitch, limitador por frame + lluvia granular, sin música (solo squish, pop, clacks, martillo y voces brainrot sintetizadas con espeak-ng), silencio 0.3s + boom, compresor, -14 LUFS con limitador lookahead | `audio/` |
| 3 fichas brainrot propias (vector) con masa/rebote/tamaño, sonido y poder: Tralalero (double bounce), Tung Tung (slam), Cappuccina (split) | `characters/` |
| Formato: martillo APLASTADOR (aprieta la ficha contra la pared → +2), batalla de 3 brainrots | `formats/hammer.py`, `reference/formats/hammer/SPEC.md` |
| Estudio de referencias: hoja de frames + análisis de sonido de cualquier grabación | `tools/refstudy.py` |
| Loop: los últimos 0.5s se funden con el frame 1 | `engine/sim.py` |

Medición (4 cores, 30 fps): ~50 s de video en ~70 s de render. A 60 fps (`--fps 60`) ronda los 2.5 min.

Siguiente: paso 2 (batalla + merge evolutivo como formatos propios), paso 3 (genoma completo + anti-repetición + metadatos), paso 4 (workflow).

## Formato principal: PUNCH FILL (calcado de ref05)
Ver `reference/formats/punch/SPEC.md` y el catálogo `reference/formats/README.md`. `formats/hammer.py` queda obsoleto.

---

# Publicación automática (todos los días, sin la compu)

El workflow `.github/workflows/daily.yml` corre solo a las **06:17 (hora de Argentina)**:
1. Renderiza **3 videos** rotando entre los 6 formatos (crusher_jaws, punch, press, slam, iris, two_cones), cada uno con
   fichas, colores y semilla distintos, y con título, descripción y tags variados (`publish/metadata.py`).
2. Los sube a YouTube **programados** a las 12:07, 16:13 y 20:37 (hora de Argentina).
3. Deja los 3 mp4 en un **Release** de GitHub llamado `videos-AAAA-MM-DD`.
4. Guarda `history.json` para no repetir semillas.

Para probarlo sin esperar: en GitHub → pestaña **Actions** → "Videos del día" → **Run workflow**.

## Bajar los videos al celular
GitHub (app o navegador) → el repo → **Releases** (en la app: "Releases" dentro del repo) → el del día → tocá el `.mp4`.
Desde ahí lo guardás en el celular y lo subís a mano con música si querés.

## Credenciales de YouTube, paso a paso desde el celular
Usá el navegador del celular (Chrome) en **"Sitio de escritorio"** (menú ⋮ → "Sitio de escritorio"): las consolas de
Google y GitHub se ven mejor así. Hacelo con la cuenta de Google **dueña del canal**.

### 1. Crear el proyecto y activar la API (una sola vez)
1. Entrá a **console.cloud.google.com** → arriba, "Seleccionar proyecto" → **Proyecto nuevo** → nombre `brainrot-physics` → Crear.
2. Menú ☰ → **APIs y servicios** → **Biblioteca** → buscá **"YouTube Data API v3"** → **Habilitar**.

### 2. Pantalla de consentimiento
1. ☰ → APIs y servicios → **Pantalla de consentimiento de OAuth** (o "Google Auth Platform") → tipo **Externo** → Crear.
2. Nombre de la app: `brainrot-physics`; correo de asistencia: el tuyo; correo del desarrollador: el tuyo → Guardar.
3. En **Usuarios de prueba** agregá el mail de la cuenta dueña del canal.
4. Volvé a la pantalla de consentimiento y tocá **"Publicar app"** (pasa a "En producción").
   Si la dejás en "Prueba", el permiso se vence a los 7 días y la subida deja de andar.

### 3. Crear YT_CLIENT_ID y YT_CLIENT_SECRET
1. ☰ → APIs y servicios → **Credenciales** → **Crear credenciales** → **ID de cliente de OAuth**.
2. Tipo de aplicación: **Aplicación web**. Nombre: `github`.
3. En **URIs de redireccionamiento autorizados** agregá exactamente: `https://developers.google.com/oauthplayground`
4. Crear. Te muestra el **ID de cliente** (= `YT_CLIENT_ID`) y el **Secreto del cliente** (= `YT_CLIENT_SECRET`).
   Copialos a una nota del celular.

### 4. Sacar YT_REFRESH_TOKEN
1. Entrá a **developers.google.com/oauthplayground**.
2. Tocá el engranaje ⚙ (arriba a la derecha) → marcá **"Use your own OAuth credentials"** → pegá el ID y el Secreto → Close.
3. A la izquierda, en el cuadro "Input your own scopes", escribí: `https://www.googleapis.com/auth/youtube.upload` → **Authorize APIs**.
4. Elegí la cuenta del canal. Si dice "Google no verificó esta app": **Configuración avanzada** → **Ir a brainrot-physics** → Permitir.
5. Volvés al Playground: tocá **"Exchange authorization code for tokens"**.
6. Copiá el **Refresh token** (= `YT_REFRESH_TOKEN`).

### 5. Cargarlas en GitHub
1. Entrá a github.com → el repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**.
2. Creá tres secretos, con estos nombres exactos y el valor que copiaste:
   - `YT_CLIENT_ID`
   - `YT_CLIENT_SECRET`
   - `YT_REFRESH_TOKEN`
3. Probalo: Actions → "Videos del día" → **Run workflow**. En el log, el paso "Subir a YouTube" tiene que decir
   `subido <id> ... → se publica ...`.

### Importante: los videos pueden quedar privados
YouTube bloquea como **privados** los videos subidos por la API desde proyectos que no pasaron su **auditoría**
(los proyectos nuevos no la tienen). Si te pasa, el video aparece en YouTube Studio como privado "bloqueado":
1. Mientras tanto: bajá el mp4 del Release y subilo a mano desde la app de YouTube (ahí podés agregarle música).
2. Para destrabarlo: pedí la auditoría en el formulario **"YouTube API Services - Audit and Quota Extension Form"**
   (support.google.com/youtube/contact/yt_api_form). Tarda días o semanas.
