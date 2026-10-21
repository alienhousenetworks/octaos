"""Industry packs, workforce registry, and the grounded record copilot."""
from app.services.sales_os.copilot.record import advise_record
from app.services.sales_os.verticals.packs import PACKS
from app.services.sales_os.verticals.registry import preview_switch
from app.services.sales_os.workforce.organization import organization


def test_eighteen_packs_are_separate_configurations():
    assert len(PACKS) == 18
    assert len({pack["id"] for pack in PACKS.values()}) == 18
    banking = PACKS["banking"]["terminology"]["lead"]
    saas = PACKS["saas"]["terminology"]["lead"]
    estate = PACKS["real_estate"]["terminology"]["opportunity"]
    assert banking == "Prospect"
    assert saas == "Lead"
    assert estate == "Booking"
    for pack in PACKS.values():
        assert pack["domain_status"] == "not_built"
        assert pack["version"] == "1.0.0"


def test_pack_switch_keeps_records():
    preview = preview_switch("saas", "real_estate", record_count=12)
    assert preview["records_deleted"] == 0
    assert preview["records_preserved"] == 12
    assert preview["incompatible"] == []
    assert preview["to_pack_id"] == "real_estate"
    assert "stay" in preview["effect"]


def test_representative_packs_are_marked():
    assert PACKS["saas"]["representative"] is True
    assert PACKS["manufacturing"]["representative"] is True
    assert PACKS["real_estate"]["representative"] is True
    assert PACKS["pharma"]["representative"] is False


def test_workforce_registers_the_canonical_twenty_four():
    payload = organization()
    assert payload["canonical_count"] == 24
    assert payload["registered_canonical_count"] == 24
    ids = [payload["orchestrator"]["agent_id"]]
    for group in payload["departments"]:
        ids.extend(agent["agent_id"] for agent in group["agents"])
    assert len(ids) == 24
    assert len(set(ids)) == 24
    assert all(agent["present"] for group in payload["departments"] for agent in group["agents"])


def test_copilot_cites_stored_email_and_does_not_invent_contact():
    advice = advise_record(
        {
            "id": "lead-1",
            "name": "Olivia Johnson",
            "company": "Alpha Business",
            "email": "olivia@alpha.example",
            "status": "contacted",
            "score": 0,
            "data": {},
        },
        "saas",
        "What should we do next with this customer?",
    )
    assert advice["invented"] is False
    assert any("olivia@alpha.example" in item["claim"] for item in advice["evidence"])
    assert advice["readiness"]["value"] is None
    assert advice["readiness"]["verification_status"] == "UNAVAILABLE"
    assert advice["deal_health"]["value"] == "contacted"
    assert all(action["executes"] is False for action in advice["actions"])
    joined = " ".join(item["claim"] for item in advice["evidence"])
    assert "phone" not in joined.lower()


def test_copilot_refuses_missing_attendance_and_loan_approval():
    record = {"id": "lead-2", "name": "Asha", "company": "Northwind", "data": {}}
    attendance = advise_record(record, "saas", "Increase attendance from the 148 people awaiting confirmation.")
    assert "not stored" in attendance["answer"]
    assert attendance["actions"] == []
    assert "148" not in attendance["answer"]

    loan = advise_record(record, "mortgage", "Approve the loan for this applicant.")
    assert "was not changed" in loan["answer"]
    assert loan["actions"] == []
