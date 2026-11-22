"""Estudio de una referencia (grabación de TikTok/YouTube o captura de pantalla).

python -m tools.refstudy reference/formats/hammer/video1.mp4 [--every 1.0]
  -> <video>.frames.png  hoja de frames (1 por segundo, 6 columnas)
  -> <video>.sound.json  golpes por segundo, brillo (centroide) y volumen por segundo
Con eso se escribe reference/formats/<formato>/SPEC.md antes de programar.
"""
import argparse, json, subprocess
import numpy as np


def duration(p):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p],
                       capture_output=True, text=True)
    return float(r.stdout.strip() or 0)


def frames(p, every, cols=6):
    d = duration(p)
    n = max(1, int(d / every))
    rows = (n + cols - 1) // cols
    out = p + ".frames.png"
    vf = (f"fps=1/{every},scale=240:-1,drawtext=text='%{{pts\\:hms}}':x=6:y=6:fontsize=20:fontcolor=yellow:"
          f"box=1:boxcolor=black@0.6,tile={cols}x{rows}")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", p, "-vf", vf, "-frames:v", "1", out], check=True)
    return out


def sound(p):
    sr = 22050
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", p, "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"],
                       capture_output=True)
    x = np.frombuffer(r.stdout, np.float32)
    if len(x) == 0:
        return {"audio": False}
    hop = 512
    nfr = len(x) // hop
    fr = x[: nfr * hop].reshape(nfr, hop)
    spec = np.abs(np.fft.rfft(fr * np.hanning(hop), axis=1))
    flux = np.maximum(0, np.diff(spec, axis=0)).sum(1)
    thr = np.median(flux) + 2.5 * np.std(flux)
    on = np.where((flux[1:-1] > thr) & (flux[1:-1] >= flux[:-2]) & (flux[1:-1] >= flux[2:]))[0]
    t_on = (on + 1) * hop / sr
    freqs = np.fft.rfftfreq(hop, 1 / sr)
    cent = (spec * freqs).sum(1) / (spec.sum(1) + 1e-9)
    rms = np.sqrt((fr ** 2).mean(1))
    secs = int(len(x) / sr)
    per = lambda a: [round(float(a[int(s * sr / hop):int((s + 1) * sr / hop)].mean()), 4) for s in range(secs)]
    return {"audio": True, "onsets_per_s": np.bincount(t_on.astype(int), minlength=secs)[:secs].tolist(),
            "centroid_hz_per_s": [round(v) for v in per(cent)], "rms_per_s": per(rms),
            "silences_s": [s for s, v in enumerate(per(rms)) if v < 0.01]}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--every", type=float, default=1.0)
    a = ap.parse_args()
    sheet = frames(a.video, a.every)
    rep = sound(a.video)
    with open(a.video + ".sound.json", "w") as f:
        json.dump(rep, f, indent=1)
    print(json.dumps({"frames": sheet, **{k: v for k, v in rep.items() if k != "rms_per_s"}}))
