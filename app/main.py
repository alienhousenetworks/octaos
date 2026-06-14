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
            if "media_prompt" not in columns:
                with engine.begin() as conn:
                    conn.execute(text("ALTER TABLE content_posts ADD COLUMN media_prompt TEXT"))
                print("Successfully added media_prompt column to content_posts table.")
            if "media_prompt_enabled" not in columns:
                with engine.begin() as conn:
                    conn.execute(text("ALTER TABLE content_posts ADD COLUMN media_prompt_enabled BOOLEAN DEFAULT FALSE"))
                print("Successfully added media_prompt_enabled column to content_posts table.")
            if "is_manual_media" not in columns:
                with engine.begin() as conn:
                    conn.execute(text("ALTER TABLE content_posts ADD COLUMN is_manual_media BOOLEAN DEFAULT FALSE"))
                print("Successfully added is_manual_media column to content_posts table.")
            if "image_prompt" not in columns:
                with engine.begin() as conn:
                    conn.execute(text("ALTER TABLE content_posts ADD COLUMN image_prompt TEXT"))
                print("Successfully added image_prompt column to content_posts table.")
            if "image_prompt_enabled" not in columns:
                with engine.begin() as conn:
                    conn.execute(text("ALTER TABLE content_posts ADD COLUMN image_prompt_enabled BOOLEAN DEFAULT FALSE"))
                print("Successfully added image_prompt_enabled column to content_posts table.")
            if "video_prompt" not in columns:
                with engine.begin() as conn:
                    conn.execute(text("ALTER TABLE content_posts ADD COLUMN video_prompt TEXT"))
                print("Successfully added video_prompt column to content_posts table.")
            if "video_prompt_enabled" not in columns:
                with engine.begin() as conn:
                    conn.execute(text("ALTER TABLE content_posts ADD COLUMN video_prompt_enabled BOOLEAN DEFAULT FALSE"))
                print("Successfully added video_prompt_enabled column to content_posts table.")
                
        if "tickets" in inspector.get_table_names():
            columns = [col["name"] for col in inspector.get_columns("tickets")]
            if "customer_contact" not in columns:
                with engine.begin() as conn:
                    conn.execute(text("ALTER TABLE tickets ADD COLUMN customer_contact VARCHAR"))
                print("Successfully added customer_contact column to tickets table.")

        if "leads" in inspector.get_table_names():
            columns = [col["name"] for col in inspector.get_columns("leads")]
            columns_to_add = {
                "personal_email": "VARCHAR",
                "company_email": "VARCHAR",
                "mobile_no": "VARCHAR",
                "company_contact_no": "VARCHAR",
                "need_of_what": "TEXT",
                "how_much": "VARCHAR",
                "why": "TEXT",
                "target_context": "TEXT",
                "priority": "VARCHAR DEFAULT 'medium'",
                "assigned_to": "VARCHAR DEFAULT 'Sales AI Agent'",
                "updated_at": "TIMESTAMP"
            }
            with engine.begin() as conn:
                for col_name, col_type in columns_to_add.items():
                    if col_name not in columns:
                        conn.execute(text(f"ALTER TABLE leads ADD COLUMN {col_name} {col_type}"))
                        print(f"Successfully added column {col_name} to leads table.")

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

        if "ai_teams" in inspector.get_table_names():
            columns = [col["name"] for col in inspector.get_columns("ai_teams")]
            if "config" not in columns:
                with engine.begin() as conn:
                    conn.execute(text("ALTER TABLE ai_teams ADD COLUMN config JSON"))
                print("Successfully added config column to ai_teams table.")

        if "users" in inspector.get_table_names():
            columns = [col["name"] for col in inspector.get_columns("users")]
            columns_to_add = {
                "name": "VARCHAR",
                "phone_no": "VARCHAR",
                "is_verified": "BOOLEAN DEFAULT FALSE",
                "otp": "VARCHAR",
                "otp_expires_at": "TIMESTAMP",
                "role": "VARCHAR DEFAULT 'member'",
                "allowed_sections": "JSON",
                "is_system_admin": "BOOLEAN DEFAULT FALSE"
            }
            with engine.begin() as conn:
                for col_name, col_type in columns_to_add.items():
                    if col_name not in columns:
                        conn.execute(text(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}"))
                        print(f"Successfully added column {col_name} to users table.")
                conn.execute(text("UPDATE users SET is_verified = TRUE WHERE is_verified IS NULL"))
                conn.execute(text("UPDATE users SET role = 'member' WHERE role IS NULL"))
                conn.execute(text("UPDATE users SET is_system_admin = FALSE WHERE is_system_admin IS NULL"))

        if "invitations" not in inspector.get_table_names():
            with engine.begin() as conn:
                conn.execute(text("""
                    CREATE TABLE invitations (
                        id VARCHAR PRIMARY KEY,
                        tenant_id VARCHAR NOT NULL,
                        created_by_id VARCHAR NOT NULL,
                        email VARCHAR,
                        token VARCHAR UNIQUE NOT NULL,
                        is_used BOOLEAN DEFAULT FALSE,
                        expires_at TIMESTAMP NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY(tenant_id) REFERENCES tenants(id),
                        FOREIGN KEY(created_by_id) REFERENCES users(id)
                    )
                """))
            print("Successfully created invitations table.")

        if "tenants" in inspector.get_table_names():
            columns = [col["name"] for col in inspector.get_columns("tenants")]
            columns_to_add = {
                "company_website": "VARCHAR",
                "company_email": "VARCHAR",
                "company_address": "VARCHAR"
            }
            with engine.begin() as conn:
                for col_name, col_type in columns_to_add.items():
                    if col_name not in columns:
                        conn.execute(text(f"ALTER TABLE tenants ADD COLUMN {col_name} {col_type}"))
                        print(f"Successfully added column {col_name} to tenants table.")
        if "system_settings" not in inspector.get_table_names():
            with engine.begin() as conn:
                conn.execute(text("""
                    CREATE TABLE system_settings (
                        key VARCHAR PRIMARY KEY,
                        value VARCHAR
                    )
                """))
            print("Successfully created system_settings table.")
    except Exception as e:
        print(f"Error checking/migrating database: {e}")



@app.get("/")
def root():
    return {"message": "Welcome to OctaOS API"}
