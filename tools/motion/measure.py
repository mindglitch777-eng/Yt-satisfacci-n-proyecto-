"""Mide el MOVIMIENTO de un video (referencia o render propio) y saca números comparables.

    python -m tools.motion.measure VIDEO [--t0 0 --dur 40 --tiktok] -o out.json

Qué mide (todo en unidades del aro: R = radio del círculo, así 480p y 1080p son comparables):
  - geometría del aro (centro, R) detectada sola
  - brazos/guantes: ángulos por frame (píxeles grises de baja saturación entre 0.45R y 0.93R)
  - golpes (los dos guantes juntos): instantes, intervalo, cuánto quedan cerrados, dónde caen
  - correlación de velocidad entre brazos (negativa = tijera/aplauso simétrico, positiva = barren juntos)
  - radio de bola en el tiempo (r/R)
  - gravedad efectiva: % de tiempo que la masa de bolas está en la mitad de ARRIBA
  - --machine jaws: pinzas LATERALES (montadas en el aro a las 9 y a las 3, entran hacia el centro):
    por frame y por lado, cuánto entra la pinza (reach = 1 - distancia mínima al centro de sus píxeles grises);
    de ahí: ciclo entre entradas, alternancia izq/der, profundidad, tiempo de entrada, tiempo activa, solapamiento
  - --tiktok: detecta tramos a 2x (la barra de comentarios desaparece) y los marca como NO válidos
"""
import argparse, json, subprocess
import numpy as np
from scipy import ndimage

FPS = 30


def probe(f):
    o = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                        "stream=width,height", "-of", "csv=p=0", f], capture_output=True, text=True).stdout
    return tuple(map(int, o.strip().split(",")[:2]))


def frames(f, t0, dur, w, h, fps=FPS, pix="rgb24"):
    """generador frame a frame (no carga todo en RAM)"""
    ch = 3 if pix == "rgb24" else 1
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", str(t0), "-t", str(dur), "-i", f, "-vf",
                          f"fps={fps},scale={w}:{h}", "-f", "rawvideo", "-pix_fmt", pix, "-"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    n = w * h * ch
    while True:
        b = p.stdout.read(n)
        if len(b) < n: break
        yield np.frombuffer(b, np.uint8).reshape(h, w, ch) if ch == 3 else np.frombuffer(b, np.uint8).reshape(h, w)
    p.kill()


def find_circle(f, w, h, t=0.5):
    g = next(frames(f, t, 1, w, h, pix="gray")).astype(float)
    th = np.linspace(0, 2 * np.pi, 360)

    def score(cx, cy, r):
        x = (cx + r * np.cos(th)).astype(int); y = (cy + r * np.sin(th)).astype(int)
        k = (x >= 0) & (x < w) & (y >= 0) & (y < h)
        return np.median(g[y[k], x[k]]) if k.mean() > .9 else 0

    best = (0, w / 2, h / 2, w * .4)
    for cx in np.linspace(w * .35, w * .65, 13):
        for cy in np.linspace(h * .3, h * .65, 25):
            for r in np.linspace(w * .3, w * .49, 20):
                s = score(cx, cy, r)
                if s > best[0]: best = (s, cx, cy, r)
    _, cx, cy, r = best
    for step in (4, 1):
        for cx2 in np.arange(cx - 4 * step, cx + 4 * step + 1, step):
            for cy2 in np.arange(cy - 4 * step, cy + 4 * step + 1, step):
                for r2 in np.arange(r - 4 * step, r + 4 * step + 1, step):
                    s = score(cx2, cy2, r2)
                    if s > best[0]: best = (s, cx2, cy2, r2)
        _, cx, cy, r = best
    return float(cx), float(cy), float(r)


def tiktok_2x(f, w, h):
    """en grabaciones de TikTok: la barra 'Agregar comentario' desaparece mientras se mantiene apretado a 2x"""
    sx, sy = w / 480, h / 1094
    bad = []
    for i, g in enumerate(frames(f, 0, 9999, w, h, fps=4, pix="gray")):
        y0, x0 = int(995 * sy), int(280 * sx)
        if g[y0:y0 + int(12 * sy), x0:x0 + int(60 * sx)].mean() < 15: bad.append(i / 4)
    segs = []
    for t in bad:
        if segs and t - segs[-1][1] <= .5: segs[-1][1] = t
        else: segs.append([t, t])
    return [s for s in segs if s[1] - s[0] >= .5]


def wrap(a): return (a + 180) % 360 - 180


def measure(f, t0=0, dur=40, tiktok=False, scale_to=540):
    W0, H0 = probe(f)
    w = scale_to; h = int(round(H0 * scale_to / W0 / 2) * 2)
    cx, cy, R = find_circle(f, w, h, t0 + .5)
    yy, xx = np.mgrid[0:h, 0:w]; dx, dy = (xx - cx) / R, (yy - cy) / R
    d = np.hypot(dx, dy); ang = np.degrees(np.arctan2(dy, dx)) % 360; inside = d < .93
    rows = []
    for i, a in enumerate(frames(f, t0, dur, w, h)):
        a = a.astype(np.int16); g = a.mean(2); sat = a.max(2) - a.min(2)
        ball = inside & (sat > 90) & (g > 60)
        arm = inside & (d > .45) & (sat < 30) & (g > 110)
        hist = np.bincount((ang[arm] // 5).astype(int), minlength=72).astype(float)
        hs = np.convolve(np.r_[hist[-2:], hist, hist[:2]], np.ones(5) / 5, "valid")
        pk = []
        for _ in range(2):
            j = int(hs.argmax())
            if hs[j] < 20 * (w / 480) ** 2: break
            pk.append(j * 5 + 2.5)
            for k in range(-5, 6): hs[(j + k) % 72] = 0
        rr = None
        if i % 15 == 0 and ball.sum():
            lab, n = ndimage.label(ball)
            ar = ndimage.sum(ball, lab, range(1, n + 1)); ar = ar[ar > 3]
            if len(ar): rr = float(np.sqrt(np.median(ar) / np.pi) / R)
        # pinzas laterales: gris medio (no el blanco del aro, ni textos ni destellos), por mitad izq/der
        jgray = (d < .9) & (sat < 30) & (g > 95) & (g < 215)
        jaw = []
        for side in (dx < 0, dx > 0):
            p = jgray & side
            jaw.append(round(float(1 - np.percentile(d[p], 0.5)), 3) if p.sum() > 25 * (w / 480) ** 2 else 0.0)
        rows.append({"t": round(t0 + i / FPS, 3), "arms": pk, "ball_px": int(ball.sum()), "jaw": jaw,
                     "mach": [int(x) for x in hist],
                     "my": float(dy[ball].mean()) if ball.any() else None,
                     "mx": float(dx[ball].mean()) if ball.any() else None, "r": rr})
    return {"video": f, "circle": [cx, cy, R], "res": [w, h], "rows": rows,
            "tiktok_2x": tiktok_2x(f, w, h) if tiktok else []}


def jaw_summary(rows, R_px, enter=0.2):
    """pinzas laterales: una 'entrada' = la pinza de un lado pasa de reach < enter a reach >= enter.
    Solo vale mientras las pinzas se ven sobre fondo libre: cuando las bolas tapan > 30% del círculo, los tonos
    sombreados de las bolas se confunden con el gris de la pinza → ese tramo se descarta."""
    full = 0.30 * np.pi * R_px ** 2
    cut = next((i for i, r in enumerate(rows) if r["ball_px"] > full), len(rows))
    rows = rows[:cut]
    J = np.array([r.get("jaw", [0, 0]) for r in rows], float)
    t = np.array([r["t"] for r in rows])
    if len(J) < 30:
        return {}
    J = ndimage.median_filter(J, size=(5, 1))          # saca destellos de 1-2 frames
    ent = []                                           # (t_inicio, lado, reach_max, t_hasta_max, duración)
    for s in (0, 1):
        on = J[:, s] >= enter
        i = 0
        while i < len(on):
            if on[i]:
                j = i
                while j < len(on) and on[j]: j += 1
                if j - i >= 6 and i > 0:               # descarta entradas ya empezadas en el frame 0
                    k = i + int(np.argmax(J[i:j, s]))
                    ent.append((t[i], s, float(J[k, s]), t[k] - t[i], t[min(j, len(t) - 1)] - t[i]))
                i = j
            else:
                i += 1
    ent.sort()
    if len(ent) < 3:
        return {"jaw_entries": len(ent)}
    ts = np.array([e[0] for e in ent])
    sides = [e[1] for e in ent]
    both = ((J[:, 0] >= enter) & (J[:, 1] >= enter)).mean()
    return {
        "jaw_entries": len(ent),
        "jaw_valid_until_s": round(float(t[-1]), 1),
        "jaw_cycle_s": round(float(np.median(np.diff(ts))), 2),
        "jaw_alternation": round(float(np.mean([a != b for a, b in zip(sides, sides[1:])])), 2),
        "jaw_reach": round(float(np.median([e[2] for e in ent])), 2),
        "jaw_in_s": round(float(np.median([e[3] for e in ent])), 2),
        "jaw_active_s": round(float(np.median([e[4] for e in ent])), 2),
        "jaw_overlap_pct": round(float(both * 100)),
    }


def summarize(m):
    rows = [r for r in m["rows"] if not any(a <= r["t"] <= b + .5 for a, b in m["tiktok_2x"])]
    closed = [len(r["arms"]) == 1 or (len(r["arms"]) == 2 and abs(wrap(r["arms"][0] - r["arms"][1])) < 40) for r in rows]
    ev, i = [], 0
    while i < len(rows):
        if closed[i]:
            j = i
            while j < len(rows) and closed[j]: j += 1
            if j - i >= 2:
                mid = rows[(i + j) // 2]; pk = mid["arms"]
                a = pk[0] if len(pk) == 1 else (pk[0] + wrap(pk[1] - pk[0]) / 2) % 360
                ba = None if mid["mx"] is None else float(np.degrees(np.arctan2(mid["my"], mid["mx"])) % 360)
                ev.append({"t": rows[i]["t"], "hold": (j - i) / FPS, "at": a, "mass_at": ba})
            i = j
        else: i += 1
    ts = [e["t"] for e in ev]; iv = np.diff(ts) if len(ts) > 1 else np.array([0.])
    vs, prev = [], None
    for r in rows:
        pk = r["arms"]
        if len(pk) < 2: prev = None; continue
        if prev:
            if abs(wrap(pk[0] - prev[1])) + abs(wrap(pk[1] - prev[0])) < abs(wrap(pk[0] - prev[0])) + abs(wrap(pk[1] - prev[1])):
                pk = [pk[1], pk[0]]
            vs.append((wrap(pk[0] - prev[0]), wrap(pk[1] - prev[1])))
        prev = pk
    v = np.array(vs) if vs else np.zeros((1, 2)); v = v[(abs(v) < 40).all(1)]
    mv = (abs(v) > 2)
    third = max(1, len(iv) // 3)
    aim = [abs(wrap(e["at"] - e["mass_at"])) for e in ev[:6] if e["mass_at"] is not None]
    radii = [(r["t"], round(r["r"], 4)) for r in rows if r["r"]]
    top = [r["my"] < 0 for r in rows if r["my"] is not None and r["ball_px"] > 300]
    # ritmo genérico de la máquina (sirve para cualquier formato): periodo dominante del movimiento angular
    H = np.array([r["mach"] for r in rows], float)
    period = None
    if len(H) > 60 and H.sum() > 0:
        mv_series = np.abs(np.diff(H, axis=0)).sum(1)
        x = mv_series - mv_series.mean()
        ac = np.correlate(x, x, "full")[len(x) - 1:]
        ac /= ac[0] if ac[0] else 1
        lo, hi = int(.25 * FPS), min(len(ac) - 1, int(4 * FPS))
        if hi > lo: period = round((lo + int(np.argmax(ac[lo:hi]))) / FPS, 2)
    return {
        "machine_period_s": period,
        "claps": len(ev),
        "clap_interval_early_s": round(float(np.median(iv[:third])), 2),
        "clap_interval_late_s": round(float(np.median(iv[-third:])), 2),
        "clap_hold_s": round(float(np.median([e["hold"] for e in ev])), 2) if ev else None,
        "first_claps_aim_error_deg": round(float(np.median(aim)), 0) if aim else None,
        "arm_velocity_corr": round(float(np.corrcoef(v[:, 0], v[:, 1])[0, 1]), 2) if len(v) > 5 else None,
        "arm_mean_speed_deg_s": round(float(np.abs(v).mean() * FPS)),
        "arm_moving_pct": [round(float(mv[:, 0].mean() * 100)), round(float(mv[:, 1].mean() * 100))],
        "ball_r_over_R_first": radii[0][1] if radii else None,
        "ball_r_over_R_last": radii[-1][1] if radii else None,
        "mass_in_top_half_pct": round(float(np.mean(top) * 100)) if top else None,
        "excluded_2x": m["tiktok_2x"],
        **({"machine": "jaws", **jaw_summary(m["rows"], m["circle"][2])} if m.get("machine") == "jaws" else {}),
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("video"); ap.add_argument("--t0", type=float, default=0); ap.add_argument("--dur", type=float, default=40)
    ap.add_argument("--tiktok", action="store_true"); ap.add_argument("-o", default=None)
    ap.add_argument("--machine", default="arms", choices=["arms", "jaws"])
    a = ap.parse_args()
    m = measure(a.video, a.t0, a.dur, a.tiktok)
    m["machine"] = a.machine
    s = summarize(m)
    if a.o: json.dump({"summary": s, **m}, open(a.o, "w"))
    print(json.dumps(s, indent=1))
