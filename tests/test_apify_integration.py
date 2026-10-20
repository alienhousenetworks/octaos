"""Comprehensive tests for OctaOS Apify Integration.
Covers ActorRegistry, ApifyTransportClient, ApifyAdapter, SalesPipeline waterfall,
MCPHub integration, and honest non-fabrication rules.
"""
from decimal import Decimal
from unittest.mock import MagicMock, patch
import pytest

from app.integrations.apify.actor_registry import ActorRegistry
from app.integrations.apify.client import ApifyTransportClient
from app.integrations.apify.schemas import ActorCapability
from app.services.sales_os.discovery.waterfall import plan_contact_waterfall
from app.services.sales_os.providers.adapters import build_adapter
from app.services.sales_os.providers.apify_adapter import ApifyAdapter
from app.services.sales_os.providers.registry import describe_source, ESTIMATED_COST


def test_actor_registry_curated_actors():
    actors = ActorRegistry.list()
    assert len(actors) >= 3

    keys = {a.actor_key for a in actors}
    assert "company_discovery" in keys
    assert "market_news" in keys
    assert "website_intelligence" in keys

    discovery_actor = ActorRegistry.get("company_discovery")
    assert discovery_actor is not None
    assert discovery_actor.actor_id == "compass/crawler-google-places"
    assert ActorCapability.ACCOUNT_DISCOVERY in discovery_actor.capabilities


def test_actor_registry_input_sanitization():
    # Enforces bounded limit on crawled places
    cleaned = ActorRegistry.validate_and_build_input(
        "company_discovery",
        {"query": "fintech in London", "maxCrawledPlacesPerSearch": 500},
    )
    assert cleaned["searchStringsArray"] == ["fintech in London"]
    assert cleaned["maxCrawledPlacesPerSearch"] == 50  # Capped to 50 max

    # Market news sanitization
    cleaned_news = ActorRegistry.validate_and_build_input(
        "market_news",
        {"query": "healthcare AI breakthroughs", "maxPagesPerQuery": 10},
    )
    assert cleaned_news["queries"] == "healthcare AI breakthroughs"
    assert cleaned_news["maxPagesPerQuery"] == 2  # Capped to 2


def test_actor_registry_rejects_unapproved():
    with pytest.raises(ValueError, match="not approved"):
        ActorRegistry.validate_and_build_input("unapproved_crypto_drainer", {})


def test_apify_transport_client_token_resolution(monkeypatch):
    monkeypatch.setenv("APIFY_TOKEN", "test_env_token_123")
    resolved = ApifyTransportClient.resolve_token()
    assert resolved == "test_env_token_123"

    # Explicit token overrides env
    override = ApifyTransportClient.resolve_token(explicit_token="explicit_token_456")
    assert override == "explicit_token_456"


@pytest.mark.asyncio
async def test_apify_transport_client_run_mocked():
    mock_run = {
        "id": "run_test_abc",
        "status": "SUCCEEDED",
        "defaultDatasetId": "ds_test_xyz",
        "usageTotalUsd": 0.042,
    }
    mock_items = [
        {"title": "Acme SaaS", "website": "https://acme.io", "categoryName": "Software"},
        {"title": "Beta Corp", "website": "https://beta.com", "categoryName": "Logistics"},
    ]

    with patch("app.integrations.apify.client.ApifyClient") as mock_client_cls:
        client_instance = MagicMock()
        mock_actor = MagicMock()
        mock_dataset = MagicMock()

        mock_actor.call.return_value = mock_run
        mock_dataset.list_items.return_value = MagicMock(items=mock_items)

        client_instance.actor.return_value = mock_actor
        client_instance.dataset.return_value = mock_dataset
        mock_client_cls.return_value = client_instance

        transport = ApifyTransportClient(token="mock_token")
        response = await transport.run_actor(
            actor_key="company_discovery",
            raw_input={"query": "SaaS companies"},
            max_charge_usd=1.50,
            limit=5,
        )

        assert response.status == "succeeded"
        assert response.provider_run_id == "run_test_abc"
        assert response.item_count == 2
        assert response.items[0]["title"] == "Acme SaaS"
        assert response.actual_cost == 0.042

        # Verify max_total_charge_usd was passed as Decimal
        mock_actor.call.assert_called_once()
        _, kwargs = mock_actor.call.call_args
        assert kwargs["max_total_charge_usd"] == Decimal("1.50")


@pytest.mark.asyncio
async def test_apify_adapter_discover_accounts_and_provenance():
    mock_items = [
        {
            "title": "Stripe Payments",
            "website": "https://stripe.com",
            "categoryName": "Fintech",
            "countryCode": "US",
            "city": "San Francisco",
            "phone": "+1-415-555-2671",
            "placeId": "place_stripe_123",
        }
    ]

    adapter = build_adapter("apify")
    assert isinstance(adapter, ApifyAdapter)
    assert "account_discovery" in adapter.capabilities()
    assert adapter.paid is True

    with patch.object(ApifyTransportClient, "run_actor") as mock_run:
        from app.integrations.apify.schemas import CollectionJobResponse
        mock_run.return_value = CollectionJobResponse(
            job_id="job_1",
            status="succeeded",
            actor_key="company_discovery",
            provider_run_id="run_123",
            dataset_id="ds_123",
            item_count=1,
            actual_cost=0.03,
            items=mock_items,
        )

        envelope = await adapter.discover_accounts("payment gateways", api_key="test_key", count=5)
        assert envelope.status == "ok"
        assert envelope.provider_key == "apify"
        assert len(envelope.accounts) == 1

        account = envelope.accounts[0]
        assert account.display_name == "Stripe Payments"
        assert account.canonical_domain == "stripe.com"
        assert account.industry == "Fintech"
        assert account.hq_country == "US"

        # Check honest contact creation
        assert len(envelope.contacts) == 1
        assert envelope.contacts[0].phone == "+1-415-555-2671"
        assert envelope.contacts[0].company_domain == "stripe.com"

        # Check evidence signal
        assert len(envelope.signals) == 1
        assert "apify_listing" in envelope.signals[0].independent_key


def test_sales_waterfall_includes_apify_as_co_equal():
    """Verifies Apify behaves as an additional tool in the candidate waterfall."""
    providers = ["apollo", "apify", "hunter"]
    costs = {"apollo": 0.10, "apify": 0.05, "hunter": 0.05}

    # Within $0.20 budget: all three can run
    steps = plan_contact_waterfall(
        qualified=True,
        providers=providers,
        costs=costs,
        budget=0.20,
    )
    assert len(steps) == 3
    assert all(s["action"] == "call" for s in steps)

    # Tight budget ($0.12): apollo ($0.10) runs, apify ($0.05) exceeds budget -> skipped
    tight_steps = plan_contact_waterfall(
        qualified=True,
        providers=providers,
        costs=costs,
        budget=0.12,
    )
    assert tight_steps[0]["provider_key"] == "apollo"
    assert tight_steps[0]["action"] == "call"
    assert tight_steps[1]["provider_key"] == "apify"
    assert tight_steps[1]["action"] == "skip"
    assert tight_steps[1]["reason"] == "budget_exceeded"


def test_mcp_hub_discovers_apify_tools():
    from app.services.mcp_hub import mcp_hub
    tools = mcp_hub.discover_tools(server_name="apify")
    tool_names = [t["name"] for t in tools]
    assert "mcp_apify_search_actors" in tool_names
    assert "mcp_apify_actor_details" in tool_names


def test_source_registry_metadata():
    desc = describe_source("apify", has_credentials=True)
    assert desc is not None
    assert desc["implementation"] == "live"
    assert desc["sales_os_callable"] is True
    assert desc["paid"] is True
    assert desc["estimated_cost_usd"] == ESTIMATED_COST["apify"]
