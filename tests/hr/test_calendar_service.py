import pytest
from datetime import datetime
from zoneinfo import ZoneInfo
from app.services.hr.calendar_service import CalendarService


def test_escape_text():
    raw = "Interview with John, Doe; Notes: Line1\nLine2 \\ Backslash"
    escaped = CalendarService.escape_text(raw)
    assert "\\," in escaped
    assert "\\;" in escaped
    assert "\\n" in escaped
    assert "\\\\" in escaped


def test_line_folding():
    long_line = "DESCRIPTION:" + "A" * 150
    folded = CalendarService.fold_line(long_line, max_octets=75)
    lines = folded.split("\r\n ")
    assert len(lines) >= 2
    for l in lines:
        assert len(l.encode("utf-8")) <= 75


def test_parse_to_utc():
    utc_dt = CalendarService.parse_to_utc("2026-11-15", "10:30 AM", "America/New_York")
    assert utc_dt.tzinfo == ZoneInfo("UTC")
    # 10:30 AM EST (UTC-5) -> 15:30 UTC
    assert utc_dt.hour == 15
    assert utc_dt.minute == 30


def test_generate_interview_ics():
    start_utc = datetime(2026, 11, 15, 15, 0, tzinfo=ZoneInfo("UTC"))
    ics = CalendarService.generate_interview_ics(
        summary="Round 1: Architecture",
        description="Interview for Senior Engineer role",
        meeting_url="https://meet.google.com/abc-defg-hij",
        start_utc=start_utc,
        duration_minutes=45,
        organizer_email="hr@octaos.ai",
        organizer_name="OctaOS HR",
        attendees=[
            {"name": "Alice Candidate", "email": "alice@example.com", "role": "REQ-PARTICIPANT"},
            {"name": "Bob Interviewer", "email": "bob@octaos.ai", "role": "REQ-PARTICIPANT"},
        ],
        calendar_uid="interview-12345@octaos.ai",
        sequence=0,
    )

    assert "BEGIN:VCALENDAR" in ics
    assert "METHOD:REQUEST" in ics
    assert "UID:interview-12345@octaos.ai" in ics
    assert "DTSTART:20261115T150000Z" in ics
    assert "DTEND:20261115T154500Z" in ics
    assert "ATTENDEE;" in ics
    assert "alice@example.com" in ics
    assert "bob@octaos.ai" in ics
    assert "END:VCALENDAR" in ics
