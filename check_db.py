from app.models.video import VideoProject, VideoRender
from app.db.session import SessionLocal

db = SessionLocal()
projects = db.query(VideoProject).filter(VideoProject.status == 'rendering').all()
for p in projects:
    print(f"Project {p.id}: title={p.title}, status={p.status}")
    renders = db.query(VideoRender).filter(VideoRender.project_id == p.id).all()
    print(f"  Renders: {len(renders)}")
    for r in renders:
        print(f"  - Render {r.id}: status={r.status}")
