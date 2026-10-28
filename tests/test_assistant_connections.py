from app.services.agents.connected_systems import (
    clients_addressed_by,
    correct_assistant_reply,
    format_connection_report,
    reply_claims_live_send,
    request_asks_about_connections,
    request_asks_to_message_connection,
    request_checks_company_services,
)


GROK_SNAPSHOT = {
    "mcp_clients": [
        {
            "id": "grok-credential",
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
    assert "two-way MCP channel" in report
    assert "cannot open a new chat" not in report
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


def test_a_message_request_is_not_only_a_status_check():
    ask = "but it is aboth direction conention happend try to message grok"
    assert request_asks_to_message_connection(ask)
    assert clients_addressed_by(GROK_SNAPSHOT, ask)[0]["name"] == "Grok Bot"
    assert not request_asks_to_message_connection("can you reach to grok bot")


def test_queued_mcp_message_is_returned_on_the_client_call():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.models.base import Tenant
    from app.models.collaborative_workforce import AgentMessage
    from app.services.mcp.client_channel import attach_pending_messages, queue_client_message

    engine = create_engine("sqlite:///:memory:")
    Tenant.__table__.create(engine)
    AgentMessage.__table__.create(engine)
    db = sessionmaker(bind=engine)()
    db.add(Tenant(id="tenant-1", name="AlienHouse"))
    db.commit()

    class Credential:
        id = "grok-credential"
        tenant_id = "tenant-1"

    placed = queue_client_message(
        db,
        tenant_id="tenant-1",
        credential_id="grok-credential",
        client_name="Grok Bot",
        text="Message from the OctaOS assistant: try to message grok",
    )
    assert placed["status"] == "queued"
    assert placed["open_streams"] == 0

    delivered = attach_pending_messages(db, Credential(), {"result": "ok"})
    assert delivered["messages_from_octaos"][0]["text"].startswith("Message from the OctaOS assistant")
    again = attach_pending_messages(db, Credential(), {"result": "ok"})
    assert "messages_from_octaos" not in again
    db.close()


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
