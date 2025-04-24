import os
import sys
import time
import pickle
import tempfile
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Thread, Timer
from collections import deque
from dotenv import load_dotenv

import cv2
import numpy as np
import face_recognition
import psycopg2
import psycopg2.extras
import pyttsx3
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from zoneinfo import ZoneInfo

load_dotenv()

COOLDOWN          = timedelta(minutes=3)
TMP_DIR           = Path(tempfile.gettempdir())
BASE_DIR          = Path(__file__).resolve().parent
PERU_TZ           = ZoneInfo("America/Lima")

TOLERANCE   = float(os.getenv("FR_TOLERANCE", 0.45))
DETECTOR    = os.getenv("FR_DET_MODEL",  "hog")
FRAME_SCALE = int  (os.getenv("FR_SCALE",       4))
VOTE_LEN    = int  (os.getenv("FR_VOTE_FRAMES", 3))
recent_names: deque[str] = deque(maxlen=VOTE_LEN)

DB_PARAMS = dict(
    host     = os.getenv("PG_HOST", "localhost"),
    port     = int(os.getenv("PG_PORT", 5432)),
    user     = os.getenv("PG_USER", "postgres"),
    password = os.getenv("PG_PASSWORD", "root"),
    dbname   = os.getenv("PG_DBNAME", "attendance_db"),
)

SQL_ATTENDANCE = """
CREATE TABLE IF NOT EXISTS attendance(
    id SERIAL PRIMARY KEY,
    person TEXT NOT NULL,
    ts TIMESTAMPTZ NOT NULL,
    record_type CHAR(3) NOT NULL
);
"""
SQL_UNKNOWN = """
CREATE TABLE IF NOT EXISTS unknown_videos(
    id SERIAL PRIMARY KEY,
    ts TIMESTAMPTZ NOT NULL,
    mp4 BYTEA NOT NULL
);
"""

conn = psycopg2.connect(**DB_PARAMS)
conn.autocommit = True
with conn.cursor() as cur:
    cur.execute(SQL_ATTENDANCE)
    cur.execute(SQL_UNKNOWN)

def last_record(name: str):
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(
            "SELECT record_type, ts FROM attendance WHERE person=%s "
            "ORDER BY ts DESC LIMIT 1;",
            (name,),
        )
        row = cur.fetchone()
        return (row["record_type"], row["ts"]) if row else (None, None)

def add_record(name: str, rec_type: str, ts: datetime):
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO attendance(person, ts, record_type) VALUES(%s, %s, %s);",
            (name, ts, rec_type),
        )
    status = "entrada" if rec_type == "IN" else "salida"
    speak(f"{ts:%Y-%m-%d %H:%M:%S}  {name}  {status} registrada.")

def save_unknown_video(mp4_path: Path):
    with open(mp4_path, "rb") as f, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO unknown_videos(ts, mp4) VALUES(%s, %s);",
            (datetime.now(timezone.utc), psycopg2.Binary(f.read())),
        )
    speak("Vídeo de usuario desconocido guardado en la base de datos.")

def record_unknown(cam, seconds: int = 3):
    tmp = TMP_DIR / f"unknown_{datetime.now():%Y%m%d_%H%M%S}.mp4"
    fps = cam.get(cv2.CAP_PROP_FPS) or 20
    w   = int(cam.get(cv2.CAP_PROP_FRAME_WIDTH))
    h   = int(cam.get(cv2.CAP_PROP_FRAME_HEIGHT))
    vw  = cv2.VideoWriter(str(tmp), cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
    end = time.time() + seconds
    while time.time() < end:
        ok, fr = cam.read()
        if ok:
            vw.write(fr)
    vw.release()
    save_unknown_video(tmp)
    tmp.unlink(missing_ok=True)

engine = pyttsx3.init()
for v in engine.getProperty("voices"):
    if "es" in v.id.lower() or "spanish" in v.name.lower():
        engine.setProperty("voice", v.id)
        break

def speak(msg: str):
    print(msg)
    engine.say(msg)
    engine.runAndWait()

with open("encodings.pickle", "rb") as f:
    enc_data = pickle.load(f)
known_encs   = enc_data["encodings"]
known_names  = enc_data["names"]
authorized   = set(known_names)

def run_script(script_name: str):
    subprocess.Popen([sys.executable, str(BASE_DIR / script_name)])

def schedule_weekly_reports():
    sched = BackgroundScheduler()
    trigger = CronTrigger(
        day_of_week="thu",
        hour=12,
        minute=20,
        timezone=PERU_TZ,
    )
    sched.add_job(run_script, trigger, args=("automatically_send_weekly_reports.py",))
    sched.start()
    return sched

def export_videos_delayed(delay_seconds: int = 15):
    Timer(delay_seconds, run_script, args=("export_videos.py",)).start()

cam = cv2.VideoCapture(0)
face_locs = face_names = []
fps = cnt = 0
t0 = time.time()
last_unknown_ts = datetime.min.replace(tzinfo=timezone.utc)

scheduler = schedule_weekly_reports()

try:
    while True:
        ok, frame = cam.read()
        if not ok:
            speak("Error de cámara."); break

        small = cv2.resize(frame, (0, 0), fx=1/FRAME_SCALE, fy=1/FRAME_SCALE)
        rgb   = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
        face_locs = face_recognition.face_locations(rgb, model=DETECTOR)
        face_encs = face_recognition.face_encodings(rgb, face_locs, model="large")
        face_names = []

        now = datetime.now(timezone.utc)
        for enc in face_encs:
            dists = face_recognition.face_distance(known_encs, enc)
            idx = int(np.argmin(dists))
            match = dists[idx] <= TOLERANCE
            name = known_names[idx] if match else "Desconocido"
            face_names.append(name)

            recent_names.append(name)
            if len(recent_names) == VOTE_LEN and len(set(recent_names)) == 1:
                voted_name = recent_names[0]
            else:
                voted_name = None

            if voted_name == "Desconocido":
                if now - last_unknown_ts >= COOLDOWN:
                    last_unknown_ts = now
                    speak("Usuario desconocido, por favor busque a Juler y regístrese.")
                    Thread(target=record_unknown, args=(cam,)).start()
                    export_videos_delayed(15)
                continue

            if voted_name and voted_name != "Desconocido":
                last_type, last_ts = last_record(voted_name)
                if last_ts is None or now - last_ts >= COOLDOWN:
                    next_type = "IN" if last_type in (None, "OUT") else "OUT"
                    add_record(voted_name, next_type, now)

        for (t, r, b, l), nm in zip(face_locs, face_names):
            t*=FRAME_SCALE; r*=FRAME_SCALE; b*=FRAME_SCALE; l*=FRAME_SCALE
            cv2.rectangle(frame, (l, t), (r, b), (0, 140, 255), 2)
            cv2.rectangle(frame, (l, b-25), (r, b), (0, 140, 255), cv2.FILLED)
            cv2.putText(frame, nm, (l+6, b-6),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)

        cnt += 1
        if time.time() - t0 >= 1:
            fps = cnt / (time.time() - t0)
            cnt = 0
            t0  = time.time()
        cv2.putText(frame, f"FPS:{fps:.1f}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

        cv2.imshow("Attendance", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
finally:
    cam.release()
    cv2.destroyAllWindows()
    conn.close()
    scheduler.shutdown()
