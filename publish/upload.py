"""Sube a YouTube los videos del día, programados en 3 horarios (publishAt), con la API de YouTube.

    python -m publish.upload --dir release
Credenciales SOLO por variables de entorno: YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN.
Si faltan, no sube nada y no falla (los mp4 igual quedan en el Release de GitHub).
"""
import argparse, datetime as dt, glob, json, os, sys

SLOTS_UTC = [(15, 7), (19, 13), (23, 37)]   # 12:07, 16:13 y 20:37 en Argentina (minutos corridos de la hora en punto)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="release")
    a = ap.parse_args()
    need = ["YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN"]
    if not all(os.environ.get(k) for k in need):
        print("Faltan las credenciales de YouTube: no se sube nada (los videos quedan en el Release).")
        return 0
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    creds = Credentials(None, refresh_token=os.environ["YT_REFRESH_TOKEN"], client_id=os.environ["YT_CLIENT_ID"],
                        client_secret=os.environ["YT_CLIENT_SECRET"], token_uri="https://oauth2.googleapis.com/token",
                        scopes=["https://www.googleapis.com/auth/youtube.upload"])
    yt = build("youtube", "v3", credentials=creds)
    now = dt.datetime.now(dt.timezone.utc)
    ok = 0
    for path in sorted(glob.glob(os.path.join(a.dir, "*.json"))):
        m = json.load(open(path))
        h, mi = SLOTS_UTC[m["slot"] % len(SLOTS_UTC)]
        when = now.replace(hour=h, minute=mi, second=0, microsecond=0)
        if when < now + dt.timedelta(minutes=20):
            when += dt.timedelta(days=1)
        body = {"snippet": {"title": m["title"], "description": m["description"], "tags": m["tags"], "categoryId": "24"},
                "status": {"privacyStatus": "private", "publishAt": when.isoformat().replace("+00:00", "Z"),
                           "selfDeclaredMadeForKids": False}}
        try:
            r = yt.videos().insert(part="snippet,status", body=body,
                                   media_body=MediaFileUpload(path[:-5] + ".mp4", resumable=True)).execute()
            print("subido", r["id"], m["title"], "→ se publica", when.isoformat())
            ok += 1
        except Exception as e:                       # un video que falla no frena a los demás
            print("ERROR al subir", path, ":", e, file=sys.stderr)
    print(f"{ok} videos subidos y programados")
    return 0


if __name__ == "__main__":
    sys.exit(main())
