from app.services.agents.connected_systems import (
    correct_assistant_reply,
    format_connection_report,
    reply_claims_live_send,
    request_asks_about_connections,
    request_checks_company_services,
)


GROK_SNAPSHOT = {
    "mcp_clients": [
        {
            "name": "Grok Bot",
            "client_type": "grok_deepseek",
            "role": "admin",
            "active": True,
            "last_used_at": "2026-10-28T08:22:34+00:00",
        }
    ],
    "connectors": [
        {"name": "OctaOS Core Services", "slug": "octaos", "connector_type": "internal_octaos", "status": "active"}
    ],
    "collaboration": "RUNNING",
    "outbound_providers": [],
    "mailbox_connected": False,
    "whatsapp_configured": False,
}


def test_connection_questions_are_recognized():
    assert request_asks_about_connections("can you reach to grok bot")
    assert request_asks_about_connections("but you areconnected using mcp check")
    assert request_asks_about_connections("is it conencted to gtrok?")
    assert not request_asks_about_connections("find leads and draft an email")


def test_connection_report_names_the_grok_mcp_client_and_the_closed_mailbox():
    report = format_connection_report(GROK_SNAPSHOT)
    assert "Grok Bot" in report
    assert "grok_deepseek" in report
    assert "inbound MCP client" in report
    assert "Mailbox: not connected" in report
    assert "octa_mcp_" not in report
    assert "encrypted" not in report.lower()


def test_mcp_refusal_is_replaced_with_the_live_report():
    corrected = correct_assistant_reply(
        "I cannot reach out to Grok bot or any external AI service. I don't have a direct MCP diagnostic.",
        "can you reach to grok bot",
        [],
        GROK_SNAPSHOT,
    )
    assert "Grok Bot" in corrected["message"]
    assert "cannot reach out" not in corrected["message"].lower()


def test_service_check_drops_tasks_and_send_claims_stay_unsent():
    assert request_checks_company_services("check ai house do buisnedd cosnultant ,marketing,hirnng too")
    reply = (
        "Yes, the Sales agent can help you find leads and do outreach via email and WhatsApp. "
        "You have 12 leads already in the CRM."
    )
    assert reply_claims_live_send(reply)
    corrected = correct_assistant_reply(reply, "can sales find leads and email them", [], GROK_SNAPSHOT)
    assert "A mailbox is not connected" in corrected["message"]
    assert corrected["drop_tasks"] is False


def test_knowledge_denial_is_replaced_with_the_stored_page():
    hits = [{
        "source_url": "https://alienhousenetworks.com/about-us/",
        "content": "AlienHouse Networks is a professionally managed technology solutions company and strategic consultancy.",
    }]
    corrected = correct_assistant_reply(
        "I don't have specific information about Alienhouse Networks in my current company knowledge base. Please paste the crawled content.",
        "what is alienhouse networks",
        hits,
        GROK_SNAPSHOT,
    )
    assert "https://alienhousenetworks.com/about-us/" in corrected["message"]
    assert "technology solutions company" in corrected["message"]
    assert "paste" not in corrected["message"].lower()
