from pathlib import Path

import logging

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, Response

from app.api.v1.api import api_router
from app.api.v2.api import api_router as api_router_v2
from app.core.config import settings
from app.core.middleware import TenantMiddleware
from app.core.observability import PrometheusMiddleware, metrics_registry
from app.api.deps import require_metrics_token

app = FastAPI(title=settings.PROJECT_NAME, openapi_url=f"{settings.API_V1_STR}/openapi.json")

# Public media files for social platform APIs (Meta, LinkedIn)
_media_dir = Path(settings.MEDIA_UPLOAD_DIR)
_media_dir.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=str(_media_dir)), name="media")

app.add_middleware(TenantMiddleware)
app.add_middleware(PrometheusMiddleware)
# Outermost so browser clients still receive CORS headers on error responses.
origins = settings.cors_origin_list()
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)
app.include_router(api_router_v2, prefix="/api/v2")


@app.exception_handler(Exception)
async def unhandled_exception(request: Request, exc: Exception):
    # Return a normal response so CORS headers are attached. An escaped
    # exception becomes a bare 500 and the browser reports it as a CORS failure.
    logging.getLogger("uvicorn.error").exception("Unhandled error on %s", request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})


@app.on_event("startup")
def startup_db_check():
    from app.db.session import engine
    from sqlalchemy import text
    try:
        with engine.begin() as conn:
            conn.execute(text("SELECT 1"))
        print("Database connection check successful.")
    except Exception as e:
        print(f"Error checking database connection: {e}")

    # Seed subscription plans (non-fatal)
    try:
        from app.db.session import SessionLocal
        from app.services.subscription_service import SubscriptionService
        db = SessionLocal()
        SubscriptionService(db).seed_plans()
        db.close()
        print("Subscription plans seeded.")
    except Exception as e:
        print(f"Plan seed skipped: {e}")

    # Ensure Flow Engine tables and seeded agents/packages exist
    try:
        from app.models.base import Base
        from app.models import enterprise, flow_engine, automations, schedules, verticals  # noqa: F401
        from app.db.session import SessionLocal
        from app.services.agents.seeder import seed_system_agents, seed_system_packages
        # One failing CREATE (pgvector) must not roll back the other tables.
        for table in Base.metadata.sorted_tables:
            try:
                with engine.begin() as conn:
                    table.create(bind=conn, checkfirst=True)
            except Exception as table_error:
                print(f"Skipped table {table.name}: {table_error.__class__.__name__}")
        db = SessionLocal()
        seed_system_agents(db)
        seed_system_packages(db)
        db.close()
        print("System agents and marketplace packages verified.")

        # Ensure schema migrations for new columns on existing tables
        try:
            from sqlalchemy import text
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE business_profiles ADD COLUMN IF NOT EXISTS lead_freshness VARCHAR DEFAULT '30_days';"))
                conn.execute(text("ALTER TABLE tickets ADD COLUMN IF NOT EXISTS owner_type VARCHAR DEFAULT 'ai';"))
                conn.execute(text("ALTER TABLE tickets ADD COLUMN IF NOT EXISTS handoff_started_at TIMESTAMP WITH TIME ZONE;"))
                conn.execute(text("ALTER TABLE tickets ADD COLUMN IF NOT EXISTS handoff_deadline_at TIMESTAMP WITH TIME ZONE;"))
                conn.execute(text("ALTER TABLE tickets ADD COLUMN IF NOT EXISTS handoff_generation INTEGER DEFAULT 0;"))
                conn.execute(text("ALTER TABLE tickets ADD COLUMN IF NOT EXISTS customer_id VARCHAR;"))
                conn.execute(text("ALTER TABLE ticket_messages ADD COLUMN IF NOT EXISTS direction VARCHAR DEFAULT 'inbound';"))
                conn.execute(text("ALTER TABLE ticket_messages ADD COLUMN IF NOT EXISTS channel VARCHAR;"))
                conn.execute(text("ALTER TABLE ticket_messages ADD COLUMN IF NOT EXISTS provider_message_id VARCHAR;"))
                conn.execute(text("ALTER TABLE ticket_messages ADD COLUMN IF NOT EXISTS delivery_status VARCHAR DEFAULT 'sent';"))
                conn.execute(text("ALTER TABLE ticket_messages ADD COLUMN IF NOT EXISTS extra_data JSON DEFAULT '{}'::json;"))
            print("Schema column extensions verified.")
        except Exception as col_error:
            print(f"Skipped schema column alter: {col_error}")
    except Exception as e:
        print(f"Flow engine startup check: {e}")


@app.get("/metrics")
def get_metrics(_: None = Depends(require_metrics_token)):
    return Response(content=metrics_registry.generate_prometheus_format(), media_type="text/plain")


@app.get("/")
def root():
    return {"message": "Welcome to OctaOS API", "enterprise": True}
