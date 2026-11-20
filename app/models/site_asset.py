import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, JSON, String, Text
from app.models.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TenantSiteAsset(Base):
    """Tenant-owned physical site, camera feed, or production telemetry source."""

    __tablename__ = "tenant_site_assets"

    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(64), index=True, nullable=False)
    name = Column(String(255), nullable=False)
    industry = Column(String(128), default="general")  # real_estate, manufacturing, logistics, retail
    site_type = Column(String(64), default="facility")  # construction_site, factory, warehouse, office
    lat = Column(Float, nullable=True)
    lon = Column(Float, nullable=True)
    camera_url = Column(String(1024), nullable=True)
    telemetry_url = Column(String(1024), nullable=True)
    metrics_json = Column(JSON, default=dict)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
