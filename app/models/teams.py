from sqlalchemy import Column, String, DateTime, ForeignKey, Float, JSON
from app.models.base import Base
import uuid
from sqlalchemy.sql import func

class AITeam(Base):
    __tablename__ = "ai_teams"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    name = Column(String, nullable=False)
    agents = Column(JSON, nullable=False) # List of agent names like ["Sales AI", "Marketing AI"]
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class InstalledApp(Base):
    __tablename__ = "installed_apps"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    app_name = Column(String, nullable=False)
    config = Column(JSON, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class AgentMetric(Base):
    __tablename__ = "agent_metrics"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    metric_name = Column(String, nullable=False) # "leads_generated", "revenue_impact", "posts_published", "meetings_booked"
    value = Column(Float, default=0.0)
    date = Column(DateTime(timezone=True), server_default=func.now())
