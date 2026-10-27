from pydantic import ValidationError
import pytest

from app.api.v1.endpoints.research import (
    ResearchSearchRequest,
    _public_job,
)


def test_research_request_normalizes_and_deduplicates_filters():
    request = ResearchSearchRequest(
        query="  ERP   implementation   market  ",
        geography=[" India ", "india", "United States"],
        industries=["Manufacturing", " manufacturing "],
        buyer_roles=["CIO", "CIO"],
        exclusions=["competitor", "competitor"],
    )

    assert request.query == "ERP implementation market"
    assert request.geography == ["India", "United States"]
    assert request.industries == ["Manufacturing"]
    assert request.buyer_roles == ["CIO"]
    assert request.exclusions == ["competitor"]


@pytest.mark.parametrize(
    "payload",
    [
        {"query": "x"},
        {"query": "valid research", "count": 101},
        {"query": "valid research", "budget_inr": 701},
        {"query": "valid research", "freshness": "forever"},
        {"query": "valid research", "geography": ["a"] * 9},
    ],
)
def test_research_request_rejects_invalid_or_unbounded_input(payload):
    with pytest.raises(ValidationError):
        ResearchSearchRequest(**payload)


def test_public_job_projection_preserves_provenance_and_omits_internal_spec():
    payload = {
        "job_id": "job-1",
        "status": "succeeded",
        "spec": {
            "tenant_id": "tenant-private",
            "query": "ERP research",
            "freshness": "14_days",
            "geography": ["India"],
        },
        "tasks": [
            {
                "task_id": "task-1",
                "method": "web",
                "provider": "duckduckgo",
                "operation": "search",
                "query": "ERP India",
                "status": "succeeded",
                "reason": "",
                "attempt": 1,
            }
        ],
        "records": [
            {
                "record_id": "record-1",
                "title": "Official ERP page",
                "original_url": "https://example.com/erp",
                "canonical_url": "example.com/erp",
                "snippet": "An official product page.",
                "page_excerpt": "Source passage about ERP.",
                "provider": "duckduckgo",
                "method": "web",
                "published_at": None,
                "retrieved_at": "2026-10-27T00:00:00Z",
                "company_name": "Example",
            }
        ],
        "assessments": [
            {
                "evidence": {
                    "claim": "The company offers ERP software.",
                    "passage": "Source passage about ERP.",
                    "source_url": "https://example.com/erp",
                    "verification_state": "supported",
                    "freshness_ok": True,
                    "notes": [],
                }
            }
        ],
        "ledger": [],
        "notes": [],
        "expansion_round": 1,
    }

    result = _public_job(payload)
    assert result["job_id"] == "job-1"
    assert result["sources"][0]["url"] == "https://example.com/erp"
    assert result["claims"][0]["passage"] == "Source passage about ERP."
    assert result["claims"][0]["verification_state"] == "supported"
    assert "tenant_id" not in result
    assert result["counts"] == {
        "tasks": 1,
        "sources": 1,
        "claims": 1,
        "succeeded": 1,
        "failed": 0,
    }
