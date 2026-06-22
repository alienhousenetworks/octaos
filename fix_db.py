from app.db.session import SessionLocal
from app.models.video import VideoProject, VideoRender

db = SessionLocal()
try:
    projects = db.query(VideoProject).filter(VideoProject.status == 'rendering').all()
    for p in projects:
        print(f"Failing project {p.id}")
        p.status = 'failed'
    db.commit()
    print("Done")
except Exception as e:
    print(e)
