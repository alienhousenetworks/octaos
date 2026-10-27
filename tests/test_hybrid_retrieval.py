"""Tests for Hybrid RAG Engine, RRF scoring, and non-dumping prompt injection."""
import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base, Tenant
from app.models.agents import KnowledgeDocument
from app.models.enterprise import KnowledgeChunk
from app.services.rag.hybrid_engine import HybridRAGEngine
from app.services.agents.base import BaseAgent
from app.services.llm_gateway import LLMGateway


@pytest.fixture
def hybrid_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    tenant = Tenant(id="tenant-hybrid-1", name="Acme Corp", company_website="https://acme.com")
    session.add(tenant)
    session.commit()

    yield session
    session.close()


def test_sparse_keyword_retrieval_and_citations(hybrid_db):
    tenant_id = "tenant-hybrid-1"
    engine = HybridRAGEngine(hybrid_db, tenant_id)

    # Seed knowledge chunks
    c1 = KnowledgeChunk(
        id="chunk-11111111",
        tenant_id=tenant_id,
        document_id="doc-1",
        title="Enterprise Pricing Guide",
        content="Our enterprise tier costs $999 per month with unlimited API calls and dedicated support.",
        page_start=4,
        page_end=4,
        source_url="https://acme.com/pricing",
        embedding_hint="pricing cost subscription plans tiers",
        is_active=True,
        version=1,
    )
    c2 = KnowledgeChunk(
        id="chunk-22222222",
        tenant_id=tenant_id,
        document_id="doc-2",
        title="Security & Compliance",
        content="We are SOC2 Type II certified and adhere to GDPR data protection standards.",
        page_start=12,
        page_end=14,
        source_url="https://acme.com/security",
        embedding_hint="security compliance soc2 gdpr audits",
        is_active=True,
        version=1,
    )
    c3 = KnowledgeChunk(
        id="chunk-33333333",
        tenant_id=tenant_id,
        document_id="doc-3",
        title="Inactive Document",
        content="Old pricing $500 per month.",
        is_active=False,
        version=1,
    )
    hybrid_db.add_all([c1, c2, c3])
    hybrid_db.commit()

    # Query for pricing
    results = engine.retrieve("What does the enterprise tier cost?", top_k=5)
    assert len(results) == 1
    assert results[0]["chunk_id"] == "chunk-11111111"
    assert "Enterprise Pricing Guide" in results[0]["citation"]
    assert "p.4" in results[0]["citation"]
    assert "https://acme.com/pricing" in results[0]["citation"]
    assert results[0]["score"] > 0

    # Query for security
    sec_results = engine.retrieve("Tell me about GDPR and SOC2 compliance", top_k=5)
    assert len(sec_results) == 1
    assert sec_results[0]["chunk_id"] == "chunk-22222222"
    assert "p.12" in sec_results[0]["citation"]


def test_reciprocal_rank_fusion_scoring(hybrid_db):
    tenant_id = "tenant-hybrid-1"
    engine = HybridRAGEngine(hybrid_db, tenant_id)

    # Add two chunks
    c1 = KnowledgeChunk(
        id="chunk-alpha",
        tenant_id=tenant_id,
        document_id="doc-a",
        title="Alpha Product",
        content="Alpha provides fast automated outbound prospecting campaigns.",
        is_active=True,
        version=1,
    )
    c2 = KnowledgeChunk(
        id="chunk-beta",
        tenant_id=tenant_id,
        document_id="doc-b",
        title="Beta Analytics",
        content="Beta provides detailed sales analytics and revenue forecasting.",
        is_active=True,
        version=1,
    )
    hybrid_db.add_all([c1, c2])
    hybrid_db.commit()

    # Sparse query matching both, but alpha higher
    results = engine.retrieve("automated outbound prospecting campaigns", top_k=2)
    assert len(results) >= 1
    assert results[0]["chunk_id"] == "chunk-alpha"
    # RRF formula: 1 / (60 + 1) = 0.01639... -> 0.0164
    assert results[0]["score"] == 0.0164


def test_assemble_context(hybrid_db):
    tenant_id = "tenant-hybrid-1"
    engine = HybridRAGEngine(hybrid_db, tenant_id)

    c = KnowledgeChunk(
        id="chunk-refund",
        tenant_id=tenant_id,
        document_id="doc-refund",
        title="Refund Policy",
        content="Customers can request a full refund within 30 days of purchase.",
        page_start=1,
        source_url="https://acme.com/refund",
        is_active=True,
        version=1,
    )
    hybrid_db.add(c)
    hybrid_db.commit()

    ctx = engine.assemble_context("What is the refund policy?")
    assert ctx["mode"] == "grounded"
    assert ctx["hits"] == 1
    assert "Refund Policy" in ctx["context"]
    assert len(ctx["citations"]) == 1

    # Empty query fallback
    empty_ctx = engine.assemble_context("Unrelated topic that definitely has no hits xyz123")
    assert empty_ctx["mode"] == "empty"
    assert empty_ctx["hits"] == 0


def test_pinned_directives_vs_selective_retrieval_in_agent(hybrid_db):
    tenant_id = "tenant-hybrid-1"

    # Seed 1 pinned directive
    pinned = KnowledgeDocument(
        id="pinned-1",
        tenant_id=tenant_id,
        doc_type="Prompt Directives",
        department="General",
        content="Always speak in a professional, polite, and confident tone. Never disclose competitor names.",
        is_active=True,
    )

    # Seed 1 regular document that should NOT be dumped entirely unless retrieved via chunks
    regular_doc = KnowledgeDocument(
        id="regular-1",
        tenant_id=tenant_id,
        doc_type="Internal Policy",
        department="HR",
        content="Office hours are from 9 AM to 5 PM Monday through Friday. Lunch break is 1 hour.",
        is_active=True,
    )

    # Seed a relevant knowledge chunk for sales
    chunk = KnowledgeChunk(
        id="sales-chunk-1",
        tenant_id=tenant_id,
        document_id="sales-doc",
        title="Sales Playbook",
        department="Sales",
        content="Highlight our 99.99% uptime guarantee and fast 24/7 onboarding.",
        is_active=True,
        version=1,
    )

    hybrid_db.add_all([pinned, regular_doc, chunk])
    hybrid_db.commit()

    agent = BaseAgent(hybrid_db, tenant_id, "SalesBot", department="Sales")
    context = agent.get_knowledge_context("sales onboarding guarantee", department="Sales")

    # 1. Pinned directive MUST be present
    assert "Always speak in a professional, polite, and confident tone" in context
    assert "[Prompt Directives]" in context

    # 2. Retrieved sales chunk MUST be present
    assert "Sales Playbook" in context
    assert "99.99% uptime guarantee" in context

    # 3. Irrelevant HR handbook MUST NOT be dumped into the context
    assert "Office hours are from 9 AM to 5 PM" not in context
    assert "Lunch break is 1 hour" not in context


def test_company_question_uses_crawled_site_not_application_form(hybrid_db):
    tenant_id = "tenant-hybrid-1"
    about = KnowledgeChunk(
        id="chunk-about",
        tenant_id=tenant_id,
        document_id="doc-about",
        title="About AlienHouse Networks",
        department="General",
        content="Who We Are. AlienHouse Networks is a professionally managed technology solutions company.",
        source_url="https://alienhousenetworks.com/about-us/",
        is_active=True,
        version=1,
    )
    form = KnowledgeChunk(
        id="chunk-form",
        tenant_id=tenant_id,
        document_id="doc-form",
        title="HR Recruitment Associate",
        department="General",
        content="Apply for this Role. Full Name. Email Address. Resume / CV. Cover Letter.",
        source_url="https://alienhousenetworks.com/careers/hr-recruitment-associate/",
        is_active=True,
        version=1,
    )
    hybrid_db.add_all([about, form])
    hybrid_db.commit()

    engine = HybridRAGEngine(hybrid_db, tenant_id)
    named = engine.retrieve("what is alienhouse networks", department="General", top_k=4)
    assert named
    assert named[0]["source_url"] == "https://alienhousenetworks.com/about-us/"
    assert "technology solutions company" in named[0]["content"]
    assert "Full Name" not in named[0]["content"]

    follow_up = engine.retrieve("it is there it just crawled the full website check", department="General", top_k=4)
    assert follow_up
    assert follow_up[0]["source_url"] == "https://alienhousenetworks.com/about-us/"
    assert all("Full Name" not in (hit["content"] or "") for hit in follow_up[:1])


def test_assistant_knowledge_query_uses_the_user_question(hybrid_db):
    from app.services.agents.orchestrator import knowledge_query_for_turn
    from app.services.agents.runtime import AgentRuntime

    tenant_id = "tenant-hybrid-1"
    hybrid_db.add(KnowledgeChunk(
        id="chunk-home",
        tenant_id=tenant_id,
        document_id="doc-home",
        title="AlienHouse Networks",
        department="General",
        content="Who We Are. AlienHouse Networks is a professionally managed technology solutions company.",
        source_url="https://alienhousenetworks.com/",
        is_active=True,
        version=1,
    ))
    hybrid_db.commit()

    query = knowledge_query_for_turn(
        "it is there it just crawled the full website check",
        [{"role": "user", "content": "what is alienhouse networks"}, {"role": "assistant", "content": "I don't have that."}],
    )
    assert "what is alienhouse networks" in query
    assert "crawled" in query

    agent = BaseAgent(hybrid_db, tenant_id, "Orchestrator AI", department="general")
    context = agent.get_knowledge_context(query, department="General")
    assert "technology solutions company" in context
    assert "https://alienhousenetworks.com/" in context
    assert "Do not say the knowledge base has no information" in context

    runtime_context = AgentRuntime()._retrieve_knowledge(
        hybrid_db, tenant_id, ["Sales"], query="what is alienhouse networks",
    )
    assert "technology solutions company" in runtime_context


def test_company_page_is_used_when_only_the_document_was_stored(hybrid_db):
    tenant_id = "tenant-hybrid-1"
    hybrid_db.add(KnowledgeDocument(
        id="doc-only-about",
        tenant_id=tenant_id,
        department="General",
        doc_type="Web Source",
        source_type="web",
        source_url="https://alienhousenetworks.com/about-us/",
        content="Source URL: https://alienhousenetworks.com/about-us/\n\nAlienHouse Networks builds hyper-advanced digital ecosystems.",
        is_active=True,
    ))
    hybrid_db.commit()

    hits = HybridRAGEngine(hybrid_db, tenant_id).retrieve("what is alienhouse networks", top_k=3)
    assert hits
    assert "digital ecosystems" in hits[0]["content"]
    assert hits[0]["source_url"] == "https://alienhousenetworks.com/about-us/"
