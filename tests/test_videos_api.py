from app.db.session import SessionLocal
from app.models.video import VideoProject
from sqlalchemy import text

db = SessionLocal()
try:
    db.execute(text("SELECT * FROM video_projects LIMIT 1"))
    print("Table exists")
except Exception as e:
    print("Error:", e)
