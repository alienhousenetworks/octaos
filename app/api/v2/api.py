from fastapi import APIRouter
from sqlalchemy import text
import logging
import redis

from app.db.session import SessionLocal
from app.core.config import settings

logger = logging.getLogger(__name__)
api_router = APIRouter()


@api_router.get("/health", tags=["system"])
def check_health():
    """Return dependency health without exposing connection details or secrets."""
    status = {
        "status": "healthy",
        "api_version": "v2",
        "checks": {},
    }

    db = None
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        status["checks"]["database"] = "ok"
    except Exception:
        logger.exception("Health check database dependency failed")
        status["checks"]["database"] = "unavailable"
        status["status"] = "degraded"
    finally:
        if db is not None:
            try:
                db.close()
            except Exception:
                logger.exception("Health check database session cleanup failed")

    try:
        client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            socket_connect_timeout=2,
        )
        if client.ping():
            status["checks"]["redis"] = "ok"
        else:
            status["checks"]["redis"] = "unavailable"
            status["status"] = "degraded"
    except Exception:
        logger.exception("Health check Redis dependency failed")
        status["checks"]["redis"] = "unavailable"
        status["status"] = "degraded"

    # Celery availability is useful operational information, but the public
    # health payload must not disclose broker URLs or exception messages.
    try:
        from app.core.celery_app import celery_app

        inspector = celery_app.control.inspect(timeout=1.0)
        ping = inspector.ping() if inspector else None
        status["checks"]["celery"] = "ok" if ping else "no_workers"
        if not ping:
            status["status"] = "degraded"
    except Exception:
        logger.exception("Health check Celery dependency failed")
        status["checks"]["celery"] = "unavailable"
        status["status"] = "degraded"

    return status
