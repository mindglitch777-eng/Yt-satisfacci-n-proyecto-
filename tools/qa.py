"""QA de un video: 6 frames en una hoja de contacto + loudness/true-peak.

python -m tools.qa out/hammer_3.mp4   -> out/hammer_3.mp4.qa.png y reporte JSON
"""
import json, subprocess, sys


def probe_dur(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                       capture_output=True, text=True)
    return float(r.stdout.strip())


def loudness(path):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", path, "-af", "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True)
    s = r.stderr[r.stderr.rfind("Summary:"):]
    def val(key):
        i = s.find(key)
        return float(s[i + len(key):].split()[0]) if i >= 0 else None
    return {"lufs": val("I:"), "true_peak_dbfs": val("Peak:"), "lra": val("LRA:")}


def contact_sheet(path, n=6):
    d = probe_dur(path)
    times = [0.05] + [d * k / (n - 1) for k in range(1, n - 1)] + [d - 0.6]
    out = path + ".qa.png"
    inputs = []
    for t in times:
        inputs += ["-ss", f"{t:.2f}", "-i", path]
    filt = "".join(f"[{i}:v]scale=360:-1,trim=end_frame=1[v{i}];" for i in range(n))
    filt += "".join(f"[v{i}]" for i in range(n)) + f"hstack=inputs={n}"
    subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", filt, "-frames:v", "1", out], check=True)
    return out, [round(t, 2) for t in times]


if __name__ == "__main__":
    p = sys.argv[1]
    sheet, times = contact_sheet(p)
    rep = {"file": p, "duration": probe_dur(p), **loudness(p), "sheet": sheet, "times": times}
    rep["ok_audio"] = rep["lufs"] is not None and abs(rep["lufs"] + 14) < 1.0 and rep["true_peak_dbfs"] < -0.5
    print(json.dumps(rep, indent=1))
