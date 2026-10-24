"""Performance tests verifying N+1 query elimination in SalesIntelligenceStore."""
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.sales_intelligence import SalesCompany, SalesOpportunity
from app.services.sales_os.orchestration.store import SalesIntelligenceStore


@pytest.fixture
def perf_db():
    engine = create_engine("sqlite:///:memory:")
    # Import all models attached to Base so tables create properly
    import app.models.sales_intelligence  # noqa: F401
    import app.models.enterprise  # noqa: F401
    import app.models.verticals  # noqa: F401

    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    tenant_id = "perf-tenant"

    # Seed 20 companies with multiple opportunities each
    for i in range(20):
        comp = SalesCompany(
            id=f"comp_{i}",
            tenant_id=tenant_id,
            display_name=f"Company {i}",
            canonical_domain=f"company{i}.com",
            field_provenance={},
            conflicts=[],
            aliases=[],
        )
        session.add(comp)
        session.flush()

        from datetime import datetime, timezone
        opp1 = SalesOpportunity(
            id=f"opp_{i}_v1",
            tenant_id=tenant_id,
            company_id=comp.id,
            stage="discovered",
            score=45.0,
            tier6_state="NEEDS_RESEARCH",
            score_version="v1",
            created_at=datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
        )
        opp2 = SalesOpportunity(
            id=f"opp_{i}_v2",
            tenant_id=tenant_id,
            company_id=comp.id,
            stage="qualified",
            score=85.0,
            tier6_state="READY",
            score_version="v2",
            created_at=datetime(2026, 1, 2, 10, 0, 0, tzinfo=timezone.utc),
        )
        session.add_all([opp1, opp2])

    session.commit()
    yield session, engine, tenant_id
    session.close()


def test_list_companies_with_opportunity_eliminates_n_plus_one(perf_db):
    session, engine, tenant_id = perf_db
    store = SalesIntelligenceStore(session, tenant_id)

    query_count = 0

    def query_listener(conn, cursor, statement, parameters, context, executemany):
        nonlocal query_count
        query_count += 1

    event.listen(engine, "before_cursor_execute", query_listener)

    try:
        # Fetch 20 companies with their latest opportunities
        results = store.list_companies_with_opportunity(limit=20)
        assert len(results) == 20

        for company, opp in results:
            assert company is not None
            assert opp is not None
            # Verify latest opportunity is returned (opp2 with score 85.0)
            assert opp.score == 85.0
            assert opp.tier6_state == "READY"

        # In an N+1 architecture, fetching 20 companies would take 1 + 20 = 21 queries.
        # With batched execution, it takes exactly 2 queries (1 for companies, 1 for opportunities IN company_ids).
        assert query_count <= 2, f"Expected <= 2 queries, but executed {query_count} queries (N+1 regression)"
    finally:
        event.remove(engine, "before_cursor_execute", query_listener)


def test_list_companies_with_opportunity_handles_empty(perf_db):
    session, _, _ = perf_db
    store = SalesIntelligenceStore(session, "nonexistent-tenant")
    results = store.list_companies_with_opportunity(limit=10)
    assert results == []
