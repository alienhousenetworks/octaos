import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class CompanyProfile(Base):
    __tablename__ = "company_profiles"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(128), nullable=True)
    country: Mapped[str | None] = mapped_column(String(64), nullable=True)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lon: Mapped[float | None] = mapped_column(Float, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    products_json: Mapped[list] = mapped_column(JSON, default=list)
    competitors_json: Mapped[list] = mapped_column(JSON, default=list)
    opportunities_json: Mapped[list] = mapped_column(JSON, default=list)
    risks_json: Mapped[list] = mapped_column(JSON, default=list)
    evidence_json: Mapped[list] = mapped_column(JSON, default=list)
    classification: Mapped[str] = mapped_column(String(32), default="DERIVED")
    confidence: Mapped[float] = mapped_column(Float, default=0.7)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class IntelligenceLead(Base):
    __tablename__ = "intelligence_leads"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True, nullable=False)
    company_profile_id: Mapped[str | None] = mapped_column(ForeignKey("company_profiles.id"), nullable=True)
    company_name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    contact_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_role: Mapped[str | None] = mapped_column(String(128), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    industry: Mapped[str | None] = mapped_column(String(128), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lon: Mapped[float | None] = mapped_column(Float, nullable=True)
    opportunity: Mapped[str] = mapped_column(Text, nullable=False)
    trigger_signal: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_json: Mapped[list] = mapped_column(JSON, default=list)
    classification: Mapped[str] = mapped_column(String(32), default="DERIVED")
    fit_score: Mapped[float] = mapped_column(Float, default=0.5)
    priority: Mapped[str] = mapped_column(String(32), default="medium")
    next_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="new")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class MarketSignal(Base):
    __tablename__ = "market_signals"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True, nullable=False)
    topic: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    region: Mapped[str | None] = mapped_column(String(128), nullable=True)
    signal_type: Mapped[str] = mapped_column(String(64), default="trend")
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_json: Mapped[list] = mapped_column(JSON, default=list)
    classification: Mapped[str] = mapped_column(String(32), default="DERIVED")
    confidence: Mapped[float] = mapped_column(Float, default=0.7)
    business_impact: Mapped[str | None] = mapped_column(Text, nullable=True)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lon: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class StrategyBrief(Base):
    __tablename__ = "strategy_briefs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True, nullable=False)
    company_profile_id: Mapped[str | None] = mapped_column(ForeignKey("company_profiles.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    target_audience: Mapped[str | None] = mapped_column(Text, nullable=True)
    sales_strategy: Mapped[str] = mapped_column(Text, nullable=False)
    marketing_strategy: Mapped[str] = mapped_column(Text, nullable=False)
    campaign_brief: Mapped[str] = mapped_column(Text, nullable=False)
    recommended_channels: Mapped[list] = mapped_column(JSON, default=list)
    evidence_json: Mapped[list] = mapped_column(JSON, default=list)
    classification: Mapped[str] = mapped_column(String(32), default="DERIVED")
    status: Mapped[str] = mapped_column(String(32), default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
