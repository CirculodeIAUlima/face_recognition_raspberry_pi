import psycopg2
import os
from pathlib import Path
from datetime import datetime

# Connect to your database
DB = dict(
    host     = os.getenv("PG_HOST", "localhost"),
    port     = int(os.getenv("PG_PORT", 5432)),
    user     = os.getenv("PG_USER", "postgres"),
    password = os.getenv("PG_PASSWORD", "root"),
    dbname   = os.getenv("PG_DBNAME", "attendance_db"),
)
conn = psycopg2.connect(**DB)

# Output directory
output_dir = Path("exported_unknown_videos")
output_dir.mkdir(exist_ok=True)

# Export videos
with conn.cursor() as cur:
    cur.execute("SELECT id, ts, mp4 FROM unknown_videos ORDER BY ts DESC;")
    for video_id, ts, video_data in cur.fetchall():
        filename = output_dir / f"unknown_{video_id}_{ts:%Y%m%d_%H%M%S}.mp4"
        with open(filename, "wb") as f:
            f.write(video_data)
        print(f"Saved video: {filename}")

conn.close()
