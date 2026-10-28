import json

from app.services.agents.connected_systems import (
    clients_addressed_by,
    connection_facts,
    correct_assistant_reply,
    ensure_mcp_message_task,
    mcp_handoff_note,
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


def test_connection_facts_name_what_is_saved_and_what_is_absent():
    snapshot = {
        **GROK_SNAPSHOT,
        "providers": [
            {"name": "anthropic", "display_name": "Anthropic Claude", "configured": False},
            {"name": "grok", "display_name": "xAI Grok", "configured": False},
        ],
        "inbuilt_model_route": "nvidia",
    }
    report = connection_facts(snapshot, "can you reach claude")
    facts = json.loads(report)
    assert facts["mcp_clients"][0]["name"] == "Grok Bot"
    assert facts["mcp_clients"][0]["client_type"] == "grok_deepseek"
    assert "id" not in facts["mcp_clients"][0]
    assert facts["mailbox_connected"] is False
    assert facts["whatsapp_configured"] is False
    assert facts["inbuilt_model_route"] == "nvidia"
    claude = facts["asked_about"][0]
    assert claude["name"] == "Claude"
    assert claude["provider"] == "anthropic"
    assert claude["provider_configured"] is False
    assert claude["mcp_clients"] == []
    assert "Connected systems for this workspace" not in report
    assert "cannot open a new chat" not in report
    assert "two-way MCP channel" not in report
    assert "octa_mcp_" not in report
    assert "encrypted" not in report.lower()


def test_a_claude_question_does_not_select_the_grok_client_or_send():
    ask = "can you reach claude"
    assert not request_asks_to_message_connection(ask)
    assert not request_asks_about_connections(ask)
    assert clients_addressed_by(GROK_SNAPSHOT, ask) == []
    assert ensure_mcp_message_task([], ask) == []


def test_mcp_refusal_is_not_replaced_by_a_connection_script():
    original = "I cannot reach out to Grok bot or any external AI service. I don't have a direct MCP diagnostic."
    corrected = correct_assistant_reply(original, "can you reach to grok bot", [], GROK_SNAPSHOT)
    assert corrected["message"] == original
    assert "Connected systems for this workspace" not in corrected["message"]


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
    assert clients_addressed_by(GROK_SNAPSHOT, "message the bot")[0]["name"] == "Grok Bot"
    assert not request_asks_to_message_connection("can you reach to grok bot")
    tasks = ensure_mcp_message_task([], ask)
    assert tasks[0]["action"] == "message_mcp_client"
    kept = ensure_mcp_message_task(
        [{"department": "System", "action": "message_mcp_client", "parameters": {"text": "hello"}}],
        ask,
    )
    assert len(kept) == 1
    assert kept[0]["parameters"]["text"] == "hello"


def test_handoff_note_does_not_claim_the_client_displayed_it():
    note = mcp_handoff_note({"client_name": "Grok Bot", "status": "queued", "open_streams": 0})
    assert "Grok Bot" in note
    assert "queued" in note
    assert "displayed it" in note
    assert "cannot open a new chat" not in note
    assert "Connected systems" not in note


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
