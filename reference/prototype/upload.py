"""Sube a YouTube todos los out/*.mp4 que no estén en uploaded.json.
Secrets (GitHub Actions o env): YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN.
Programa la publicación escalonada (publishAt) para no tirar todo junto."""
import glob, json, os, datetime as dt
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SLOTS_UTC = [14, 18, 22, 1]  # 11h/15h/19h/22h ARG → prime time US/LatAm

creds = Credentials(None, refresh_token=os.environ["YT_REFRESH_TOKEN"], client_id=os.environ["YT_CLIENT_ID"],
                    client_secret=os.environ["YT_CLIENT_SECRET"], token_uri="https://oauth2.googleapis.com/token")
yt = build("youtube", "v3", credentials=creds)
done = json.load(open("uploaded.json")) if os.path.exists("uploaded.json") else []
now = dt.datetime.now(dt.timezone.utc)
for i, mp4 in enumerate(sorted(set(glob.glob("out/*.mp4")) - set(done))):
    m = json.load(open(mp4[:-4] + ".json"))
    when = (now + dt.timedelta(days=i // len(SLOTS_UTC))).replace(hour=SLOTS_UTC[i % len(SLOTS_UTC)], minute=0, second=0)
    if when < now: when += dt.timedelta(days=1)
    body = {"snippet": {"title": m["title"], "description": m["description"], "tags": m["tags"], "categoryId": "24"},
            "status": {"privacyStatus": "private", "publishAt": when.isoformat().replace("+00:00", "Z"),
                       "selfDeclaredMadeForKids": False}}
    r = yt.videos().insert(part="snippet,status", body=body, media_body=MediaFileUpload(mp4, resumable=True)).execute()
    print("subido", r["id"], "→", when); done.append(mp4)
    json.dump(done, open("uploaded.json", "w"), indent=1)
