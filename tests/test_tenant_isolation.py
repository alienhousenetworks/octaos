import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timezone

from app.models.base import Base
from app.models.verticals import Lead, ContentPost, Ticket, Transaction, Candidate
from app.models.deal_room import DealRoom
from app.models.agents import ActivityLog
from app.services.analytics.metrics_service import MetricsService
from app.services.analytics.detectors import detect_all_findings


@pytest.fixture
def multi_tenant_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[
        Lead.__table__,
        ContentPost.__table__,
        Ticket.__table__,
        DealRoom.__table__,
        Transaction.__table__,
        Candidate.__table__,
        ActivityLog.__table__,
    ])
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_tenant_isolation_no_data_leakage(multi_tenant_db):
    now = datetime.now(timezone.utc)
    tenant_a = "tenant-enterprise-alpha"
    tenant_b = "tenant-startup-beta"

    # Seed Tenant A: 100 leads, $500,000 deal pipeline
    for i in range(100):
        multi_tenant_db.add(Lead(
            id=f"lead-a-{i}",
            tenant_id=tenant_a,
            name=f"Alpha Lead {i}",
            status="converted",
            assigned_to="Sales AI Agent",
            created_at=now,
        ))
    multi_tenant_db.add(DealRoom(
        id="deal-a-1",
        tenant_id=tenant_a,
        company_name="Mega Corp Alpha",
        domain="megacorpalpha.com",
        stage="won",
        annual_revenue_usd=500000.0,
        created_at=now,
    ))

    # Seed Tenant B: 5 leads, $10,000 deal pipeline, stalled tickets
    for i in range(5):
        multi_tenant_db.add(Lead(
            id=f"lead-b-{i}",
            tenant_id=tenant_b,
            name=f"Beta Lead {i}",
            status="captured",
            assigned_to="unassigned",
            created_at=now,
        ))
    multi_tenant_db.add(DealRoom(
        id="deal-b-1",
        tenant_id=tenant_b,
        company_name="Micro Beta",
        domain="microbeta.com",
        stage="discovered",
        annual_revenue_usd=10000.0,
        created_at=now,
    ))

    multi_tenant_db.commit()

    # Harvest Tenant A
    service_a = MetricsService(multi_tenant_db, tenant_a)
    payload_a = service_a.harvest()
    assert payload_a.items["leads.total"].value == 100.0
    assert payload_a.items["deals.pipeline_value"].value == 500000.0
    assert payload_a.items["leads.unassigned_count"].value == 0.0

    # Harvest Tenant B
    service_b = MetricsService(multi_tenant_db, tenant_b)
    payload_b = service_b.harvest()
    assert payload_b.items["leads.total"].value == 5.0
    assert payload_b.items["deals.pipeline_value"].value == 10000.0
    assert payload_b.items["leads.unassigned_count"].value == 5.0

    # Assert zero cross-contamination
    assert payload_a.items["leads.total"].value != payload_b.items["leads.total"].value
    assert payload_a.items["deals.pipeline_value"].value != payload_b.items["deals.pipeline_value"].value
