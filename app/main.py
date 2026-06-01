from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.api.v1.api import api_router
from app.core.config import settings

app = FastAPI(title=settings.PROJECT_NAME, openapi_url=f"{settings.API_V1_STR}/openapi.json")

# Public media files for social platform APIs (Meta, LinkedIn)
_media_dir = Path(settings.MEDIA_UPLOAD_DIR)
_media_dir.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=str(_media_dir)), name="media")

# Set all CORS enabled origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.on_event("startup")
def startup_db_check():
    from app.db.session import engine
    from app.models.base import Base
    import app.models.verticals
    import app.models.workflows
    from sqlalchemy import text, inspect
    try:
        Base.metadata.create_all(bind=engine)
        print("Database tables initialized.")
        
        inspector = inspect(engine)
        
        if "workflow_tasks" in inspector.get_table_names():
            columns = [col["name"] for col in inspector.get_columns("workflow_tasks")]
            columns_to_add = {
                "task_type": "VARCHAR",
                "payload": "JSON",
                "scheduled_at": "TIMESTAMP"
            }
            with engine.begin() as conn:
                for col_name, col_type in columns_to_add.items():
                    if col_name not in columns:
                        conn.execute(text(f"ALTER TABLE workflow_tasks ADD COLUMN {col_name} {col_type}"))
                        print(f"Successfully added column {col_name} to workflow_tasks table.")

        if "content_posts" in inspector.get_table_names():
            columns = [col["name"] for col in inspector.get_columns("content_posts")]
            if "video_url" not in columns:
                with engine.begin() as conn:
                    conn.execute(text("ALTER TABLE content_posts ADD COLUMN video_url VARCHAR"))
                print("Successfully added video_url column to content_posts table.")
                
        if "tickets" in inspector.get_table_names():
            columns = [col["name"] for col in inspector.get_columns("tickets")]
            if "customer_contact" not in columns:
                with engine.begin() as conn:
                    conn.execute(text("ALTER TABLE tickets ADD COLUMN customer_contact VARCHAR"))
                print("Successfully added customer_contact column to tickets table.")

        if "provider_usage" in inspector.get_table_names():
            columns = [col["name"] for col in inspector.get_columns("provider_usage")]
            columns_to_add = {
                "latency": "FLOAT DEFAULT 0.0",
                "cache_hit": "BOOLEAN DEFAULT FALSE",
                "cached_tokens": "INTEGER DEFAULT 0",
                "is_batch": "BOOLEAN DEFAULT FALSE",
                "task_type": "VARCHAR DEFAULT 'general'",
                "status": "VARCHAR DEFAULT 'success'",
                "error_message": "VARCHAR",
                "failover_from": "VARCHAR"
            }
            with engine.begin() as conn:
                for col_name, col_type in columns_to_add.items():
                    if col_name not in columns:
                        conn.execute(text(f"ALTER TABLE provider_usage ADD COLUMN {col_name} {col_type}"))
                        print(f"Successfully added column {col_name} to provider_usage table.")
    except Exception as e:
        print(f"Error checking/migrating database: {e}")



@app.get("/")
def root():
    return {"message": "Welcome to NexusOS API"}
