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
    # Refuse to boot a production/staging app with unsafe default configuration.
    settings.validate_production_configuration()

    from app.db.session import engine
    from sqlalchemy import text
    try:
        with engine.begin() as conn:
            conn.execute(text("SELECT 1"))
        print("Database connection check successful.")
    except Exception as e:
        logging.getLogger("uvicorn.error").exception("Database startup check failed")
        if (settings.ENVIRONMENT or "").strip().lower() in {"production", "prod", "staging"}:
            raise RuntimeError(
                "Required database is unavailable; refusing to start in production/staging."
            ) from e
        print(f"Error checking database connection: {e}")

    # Seed subscription plans (non-fatal in development; schema/migration work is tracked separately).
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
        from app.models import enterprise, flow_engine, automations, schedules, verticals, rooms, hr, field_sales, real_estate, rbac, autonomous_work, workforce_events, collaborative_workforce  # noqa: F401
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
        try:
            from app.services.rbac_service import ensure_system_permissions
            ensure_system_permissions(db)
        except Exception as rbac_seed_err:
            print(f"RBAC permissions seed skipped: {rbac_seed_err}")
        db.close()
        print("System agents and marketplace packages verified.")

        # Ensure schema migrations for new columns on existing tables
        try:
            from sqlalchemy import text
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE business_profiles ADD COLUMN IF NOT EXISTS lead_freshness VARCHAR DEFAULT '30_days';"))
                conn.execute(text("ALTER TABLE business_profiles ADD COLUMN IF NOT EXISTS industry_pack_id VARCHAR;"))
                conn.execute(text("ALTER TABLE business_profiles ADD COLUMN IF NOT EXISTS sales_industry_pack_id VARCHAR;"))
                conn.execute(text("ALTER TABLE business_profiles ADD COLUMN IF NOT EXISTS marketing_industry_pack_id VARCHAR;"))
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
                conn.execute(text("ALTER TABLE candidates ADD COLUMN IF NOT EXISTS room_id VARCHAR;"))
                conn.execute(text("ALTER TABLE content_posts ADD COLUMN IF NOT EXISTS room_id VARCHAR;"))
                conn.execute(text("ALTER TABLE tickets ADD COLUMN IF NOT EXISTS room_id VARCHAR;"))
                conn.execute(text("ALTER TABLE deal_rooms ADD COLUMN IF NOT EXISTS room_id VARCHAR;"))
                conn.execute(text("ALTER TABLE leads ADD COLUMN IF NOT EXISTS room_id VARCHAR;"))
                conn.execute(text("ALTER TABLE leads ADD COLUMN IF NOT EXISTS sales_company_id VARCHAR;"))
                conn.execute(text("ALTER TABLE leads ADD COLUMN IF NOT EXISTS sales_contact_id VARCHAR;"))
                conn.execute(text("ALTER TABLE leads ADD COLUMN IF NOT EXISTS sales_opportunity_id VARCHAR;"))
                conn.execute(text("ALTER TABLE content_posts ADD COLUMN IF NOT EXISTS used_model VARCHAR;"))
                conn.execute(text("ALTER TABLE content_posts ADD COLUMN IF NOT EXISTS fallback_reason TEXT;"))
                conn.execute(text("ALTER TABLE content_posts ADD COLUMN IF NOT EXISTS cost_usd DOUBLE PRECISION DEFAULT 0.0;"))
                conn.execute(text("ALTER TABLE suppression_records ADD COLUMN IF NOT EXISTS channel VARCHAR;"))
                conn.execute(text("ALTER TABLE suppression_records ADD COLUMN IF NOT EXISTS jurisdiction VARCHAR;"))
                conn.execute(text("ALTER TABLE suppression_records ADD COLUMN IF NOT EXISTS scope VARCHAR DEFAULT 'tenant';"))
                conn.execute(text("ALTER TABLE tenant_document_templates ADD COLUMN IF NOT EXISTS category VARCHAR DEFAULT 'onboarding';"))
                conn.execute(text("ALTER TABLE tenant_document_templates ADD COLUMN IF NOT EXISTS folder_path VARCHAR DEFAULT '/';"))
                conn.execute(text("ALTER TABLE tenant_document_templates ADD COLUMN IF NOT EXISTS tags JSON DEFAULT '[]'::json;"))
                conn.execute(text("ALTER TABLE tenant_document_templates ADD COLUMN IF NOT EXISTS description TEXT;"))
                conn.execute(text("ALTER TABLE tenant_document_templates ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;"))
                conn.execute(text("ALTER TABLE tenant_document_templates ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_tenant_document_templates_category ON tenant_document_templates(category);"))
                conn.execute(text("ALTER TABLE template_versions ADD COLUMN IF NOT EXISTS docx_structure JSON DEFAULT '{}'::json;"))
                conn.execute(text("ALTER TABLE template_versions ADD COLUMN IF NOT EXISTS detected_clauses JSON DEFAULT '[]'::json;"))
                conn.execute(text("ALTER TABLE template_versions ADD COLUMN IF NOT EXISTS proposed_mappings JSON DEFAULT '[]'::json;"))
                conn.execute(text("ALTER TABLE template_versions ADD COLUMN IF NOT EXISTS raw_content TEXT;"))
                conn.execute(text("ALTER TABLE template_versions ADD COLUMN IF NOT EXISTS published_at TIMESTAMP WITH TIME ZONE;"))
                conn.execute(text("ALTER TABLE template_versions ADD COLUMN IF NOT EXISTS published_by_user_id VARCHAR;"))
                # Real Estate & Field Sales extensions
                conn.execute(text("ALTER TABLE real_estate_projects ADD COLUMN IF NOT EXISTS latitude DOUBLE PRECISION;"))
                conn.execute(text("ALTER TABLE real_estate_projects ADD COLUMN IF NOT EXISTS longitude DOUBLE PRECISION;"))
                conn.execute(text("ALTER TABLE real_estate_projects ADD COLUMN IF NOT EXISTS address VARCHAR;"))
                conn.execute(text("ALTER TABLE real_estate_projects ADD COLUMN IF NOT EXISTS geocoded_at TIMESTAMP WITH TIME ZONE;"))
                conn.execute(text("ALTER TABLE real_estate_site_visits ADD COLUMN IF NOT EXISTS duration_minutes INTEGER DEFAULT 45;"))
                conn.execute(text("ALTER TABLE real_estate_site_visits ADD COLUMN IF NOT EXISTS sequence_order INTEGER DEFAULT 1;"))
                conn.execute(text("ALTER TABLE real_estate_site_visits ADD COLUMN IF NOT EXISTS estimated_travel_minutes INTEGER DEFAULT 0;"))
                conn.execute(text("ALTER TABLE real_estate_site_visits ADD COLUMN IF NOT EXISTS estimated_arrival_at TIMESTAMP WITH TIME ZONE;"))
                conn.execute(text("ALTER TABLE real_estate_site_visits ADD COLUMN IF NOT EXISTS actual_arrival_at TIMESTAMP WITH TIME ZONE;"))
                conn.execute(text("ALTER TABLE real_estate_site_visits ADD COLUMN IF NOT EXISTS actual_departure_at TIMESTAMP WITH TIME ZONE;"))
                conn.execute(text("ALTER TABLE real_estate_site_visits ADD COLUMN IF NOT EXISTS check_in_latitude DOUBLE PRECISION;"))
                conn.execute(text("ALTER TABLE real_estate_site_visits ADD COLUMN IF NOT EXISTS check_in_longitude DOUBLE PRECISION;"))
                conn.execute(text("ALTER TABLE real_estate_site_visits ADD COLUMN IF NOT EXISTS check_in_accuracy DOUBLE PRECISION;"))
                conn.execute(text("ALTER TABLE real_estate_site_visits ADD COLUMN IF NOT EXISTS check_in_verified BOOLEAN DEFAULT FALSE;"))
                conn.execute(text("ALTER TABLE real_estate_site_visits ADD COLUMN IF NOT EXISTS check_in_exception_reason VARCHAR;"))
                conn.execute(text("ALTER TABLE real_estate_site_visits ADD COLUMN IF NOT EXISTS buyer_interest_level VARCHAR;"))
                conn.execute(text("ALTER TABLE real_estate_site_visits ADD COLUMN IF NOT EXISTS buyer_objections JSON DEFAULT '[]'::json;"))
                conn.execute(text("ALTER TABLE real_estate_site_visits ADD COLUMN IF NOT EXISTS agreed_next_step VARCHAR;"))
                conn.execute(text("ALTER TABLE real_estate_site_visits ADD COLUMN IF NOT EXISTS recovery_notes TEXT;"))
                # RBAC & Django-style user attributes
                conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_staff BOOLEAN DEFAULT FALSE;"))
                conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS department VARCHAR;"))
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
