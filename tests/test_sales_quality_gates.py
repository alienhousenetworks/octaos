"""Deterministic safety and evidence gates for Sales AI outreach."""
from app.services.sales_os.quality_gates import (
    assess_channel_authorization,
    assess_outreach_readiness,
    has_real_contact_name,
)


def valid_prospect(**overrides):
    prospect = {
        "company_name": "Acme",
        "contact_status": "READY",
        "evidence_url": "https://acme.example/news/expansion",
        "evidence_quote": "Acme announced a new regional sales team.",
        "buying_signal": "Expansion announcement",
        "pain_points": ["regional lead routing"],
        "contact": {
            "name": "Ada Lovelace",
            "title": "VP Sales",
            "email": "ada@acme.example",
            "phone": "",
        },
    }
    prospect.update(overrides)
    return prospect


def test_real_contact_name_rejects_placeholder_values():
    assert has_real_contact_name("Ada Lovelace")
    assert not has_real_contact_name("")
    assert not has_real_contact_name("Decision Maker")
    assert not has_real_contact_name("Founder/Owner")


def test_outreach_is_blocked_by_default_even_when_research_is_present():
    result = assess_outreach_readiness(
        valid_prospect(),
        auto_send_enabled=False,
        permission_state="granted",
    )
    assert result["ready"] is False
    assert "automatic_sending_not_enabled" in result["blockers"]


def test_outreach_requires_explicit_permission():
    result = assess_outreach_readiness(
        valid_prospect(),
        auto_send_enabled=True,
        permission_state="unknown",
    )
    assert result["ready"] is False
    assert "outbound_permission_not_granted" in result["blockers"]


def test_outreach_requires_source_and_specific_evidence():
    prospect = valid_prospect(evidence_url="", evidence_quote="", buying_signal="", pain_points=[], news=[], jobs=[])
    result = assess_outreach_readiness(
        prospect,
        auto_send_enabled=True,
        permission_state="granted",
    )
    assert result["ready"] is False
    assert "source_url_missing_or_invalid" in result["blockers"]
    assert "need_evidence_missing" in result["blockers"]


def test_outreach_rejects_placeholder_identity_and_partial_contact():
    prospect = valid_prospect()
    prospect["contact"]["name"] = "Decision Maker"
    prospect["contact_status"] = "PARTIAL"
    result = assess_outreach_readiness(
        prospect,
        auto_send_enabled=True,
        permission_state="granted",
    )
    assert result["ready"] is False
    assert "contact_identity_unverified" in result["blockers"]
    assert "contact_not_qualified_by_discovery" in result["blockers"]


def test_outreach_ready_only_when_every_gate_passes():
    result = assess_outreach_readiness(
        valid_prospect(),
        auto_send_enabled=True,
        permission_state="granted",
    )
    assert result["ready"] is True
    assert result["blockers"] == []


def test_suppression_always_blocks_outreach():
    result = assess_outreach_readiness(
        valid_prospect(),
        auto_send_enabled=True,
        permission_state="granted",
        suppressed=True,
    )
    assert result["ready"] is False
    assert "suppressed" in result["blockers"]


def test_central_channel_gate_requires_explicit_email_authorization():
    blocked = assess_channel_authorization({}, "email")
    assert blocked["ready"] is False
    assert "automatic_sending_not_enabled" in blocked["blockers"]
    assert "outbound_permission_not_granted" in blocked["blockers"]

    allowed = assess_channel_authorization(
        {
            "sales_ai_auto_send_enabled": True,
            "outbound_permission_state": "granted",
        },
        "email",
    )
    assert allowed["ready"] is True


def test_central_channel_gate_requires_whatsapp_permission_and_opt_in():
    settings = {
        "sales_ai_auto_send_enabled": True,
        "outbound_permission_state": "granted",
    }
    blocked = assess_channel_authorization(settings, "whatsapp")
    assert blocked["ready"] is False
    assert "whatsapp_permission_not_granted" in blocked["blockers"]
    assert "whatsapp_opt_in_missing" in blocked["blockers"]

    allowed = assess_channel_authorization(
        {
            **settings,
            "whatsapp_permission_state": "granted",
        },
        "whatsapp",
        recipient_opt_in=True,
    )
    assert allowed["ready"] is True


def test_outreach_rejects_non_http_source_reference():
    prospect = valid_prospect(evidence_url="company website")
    result = assess_outreach_readiness(
        prospect,
        auto_send_enabled=True,
        permission_state="granted",
    )
    assert result["ready"] is False
    assert "source_url_missing_or_invalid" in result["blockers"]


def test_llm_pain_point_guess_without_source_evidence_does_not_authorize_outreach():
    prospect = valid_prospect(
        evidence_quote="",
        buying_signal="",
        pain_points=["operational bottlenecks"],
        news=[],
        jobs=[],
    )
    result = assess_outreach_readiness(
        prospect,
        auto_send_enabled=True,
        permission_state="granted",
    )
    assert result["ready"] is False
    assert "need_evidence_missing" in result["blockers"]
