"""
RFC 5545 compliant iCalendar (.ics) generation service.
Provides timezone-safe calendar events, stable UIDs, SEQUENCE tracking,
proper text escaping, and 75-octet line folding.
"""
import uuid
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


class CalendarService:
    @staticmethod
    def escape_text(text: str) -> str:
        """Escapes backslashes, semicolons, commas, and newlines per RFC 5545 §3.3.11."""
        if not text:
            return ""
        # Order matters: escape backslash first
        text = text.replace("\\", "\\\\")
        text = text.replace(";", "\\;")
        text = text.replace(",", "\\,")
        text = text.replace("\r\n", "\\n").replace("\r", "\\n").replace("\n", "\\n")
        return text

    @staticmethod
    def fold_line(line: str, max_octets: int = 75) -> str:
        """
        Folds long lines according to RFC 5545 §3.1.
        Lines longer than 75 octets are split with CRLF followed by a single whitespace.
        """
        encoded = line.encode("utf-8")
        if len(encoded) <= max_octets:
            return line

        folded_chunks = []
        start = 0
        limit = max_octets

        while start < len(encoded):
            chunk = encoded[start:start + limit]
            # Ensure we do not slice in the middle of a multi-byte UTF-8 character
            while len(chunk) > 0:
                try:
                    decoded = chunk.decode("utf-8")
                    folded_chunks.append(decoded)
                    start += len(chunk)
                    limit = max_octets - 1  # 1 space prefix on continuation lines
                    break
                except UnicodeDecodeError:
                    chunk = chunk[:-1]

        return "\r\n ".join(folded_chunks)

    @staticmethod
    def parse_to_utc(date_str: str, time_str: str, tz_name: str) -> datetime:
        """
        Validates IANA timezone and converts local date & time strings into a timezone-aware UTC datetime.
        """
        try:
            tz = ZoneInfo(tz_name.strip() if tz_name else "UTC")
        except ZoneInfoNotFoundError:
            tz = ZoneInfo("UTC")

        # Normalize time_str: e.g. "11:00 AM", "14:30", "2:00 PM"
        time_clean = time_str.strip().upper()
        # Parse common time formats
        parsed_time = None
        for fmt in ("%I:%M %p", "%I:%M%p", "%H:%M", "%I %p"):
            try:
                parsed_time = datetime.strptime(time_clean, fmt).time()
                break
            except ValueError:
                continue

        if not parsed_time:
            # Fallback to noon UTC
            parsed_time = datetime.strptime("12:00", "%H:%M").time()

        # Parse date
        parsed_date = None
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y"):
            try:
                parsed_date = datetime.strptime(date_str.strip(), fmt).date()
                break
            except ValueError:
                continue

        if not parsed_date:
            parsed_date = datetime.utcnow().date()

        local_dt = datetime.combine(parsed_date, parsed_time, tzinfo=tz)
        utc_dt = local_dt.astimezone(ZoneInfo("UTC"))
        return utc_dt

    @classmethod
    def generate_interview_ics(
        cls,
        summary: str,
        description: str,
        meeting_url: str,
        start_utc: datetime,
        duration_minutes: int,
        organizer_email: str,
        organizer_name: str,
        attendees: List[Dict[str, str]],  # [{"name": "...", "email": "...", "role": "interviewer|candidate"}]
        calendar_uid: Optional[str] = None,
        sequence: int = 0,
        status: str = "CONFIRMED",  # 'CONFIRMED' or 'CANCELLED'
        method: str = "REQUEST",    # 'REQUEST' or 'CANCEL'
    ) -> str:
        """
        Generates a valid RFC 5545 iCalendar payload.
        """
        uid = calendar_uid or f"octaos-interview-{uuid.uuid4()}@octaos.ai"
        end_utc = start_utc + timedelta(minutes=duration_minutes)

        now_utc = datetime.now(ZoneInfo("UTC"))
        dtstamp = now_utc.strftime("%Y%m%dT%H%M%SZ")
        dtstart = start_utc.strftime("%Y%m%dT%H%M%SZ")
        dtend = end_utc.strftime("%Y%m%dT%H%M%SZ")

        escaped_summary = cls.escape_text(summary)
        escaped_desc = cls.escape_text(description)
        escaped_loc = cls.escape_text(meeting_url or "Online Meeting (Google Meet)")
        escaped_org_name = cls.escape_text(organizer_name or "Talent Acquisition")

        lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//OctaOS//Enterprise HR Interview Scheduler//EN",
            "CALSCALE:GREGORIAN",
            f"METHOD:{method}",
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{dtstamp}",
            f"DTSTART:{dtstart}",
            f"DTEND:{dtend}",
            f"SUMMARY:{escaped_summary}",
            f"DESCRIPTION:{escaped_desc}",
            f"LOCATION:{escaped_loc}",
            f"ORGANIZER;CN={escaped_org_name}:mailto:{organizer_email}",
            f"SEQUENCE:{sequence}",
            f"STATUS:{status}",
            "TRANSP:OPAQUE",
        ]

        # Attendees
        for att in attendees:
            att_email = att.get("email", "").strip()
            if not att_email:
                continue
            att_name = cls.escape_text(att.get("name") or att_email)
            role = att.get("role", "REQ-PARTICIPANT")
            rsvp = "TRUE" if method == "REQUEST" else "FALSE"
            lines.append(
                f"ATTENDEE;CUTYPE=INDIVIDUAL;ROLE={role};PARTSTAT=NEEDS-ACTION;RSVP={rsvp};CN={att_name}:mailto:{att_email}"
            )

        # Alarm reminder 15 minutes prior
        if method == "REQUEST":
            lines.extend([
                "BEGIN:VALARM",
                "TRIGGER:-PT15M",
                "ACTION:DISPLAY",
                f"DESCRIPTION:Reminder: {escaped_summary}",
                "END:VALARM",
            ])

        lines.extend([
            "END:VEVENT",
            "END:VCALENDAR",
        ])

        # Apply RFC line folding to each line
        folded_lines = [cls.fold_line(line) for line in lines]
        return "\r\n".join(folded_lines) + "\r\n"
