"""Parse meeting invitations from email content."""

from __future__ import annotations

import base64
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from typing import Any

from bs4 import BeautifulSoup
from dateutil import parser as date_parser
from icalendar import Calendar

MEETING_LINK_RE = re.compile(
    r"https?://(?:[\w.-]+\.)?(?:zoom\.us|meet\.google\.com|teams\.microsoft\.com|"
    r"teams\.live\.com|webex\.com|whereby\.com)[^\s\"'<>]*",
    re.IGNORECASE,
)

ZOOM_LINK_RE = re.compile(
    r"https?://(?:[\w.-]+\.)?zoom\.us/(?:j|my)/[^\s\"'<>]+",
    re.IGNORECASE,
)

MEET_LINK_RE = re.compile(
    r"https?://meet\.google\.com/[a-z]{3}-[a-z]{4}-[a-z]{3}",
    re.IGNORECASE,
)

TEAMS_LINK_RE = re.compile(
    r"https?://teams\.(?:microsoft\.com|live\.com)/[^\s\"'<>]+",
    re.IGNORECASE,
)

DATE_PATTERNS = [
    re.compile(
        r"(?:senin|selasa|rabu|kamis|jumat|sabtu|minggu|monday|tuesday|wednesday|"
        r"thursday|friday|saturday|sunday)?,?\s*"
        r"(\d{1,2}[\s/.-]\w+[\s/.-]\d{2,4}|\d{1,2}[\s/.-]\d{1,2}[\s/.-]\d{2,4})"
        r"\s*(?:pukul|jam|at|@)?\s*(\d{1,2}[.:]\d{2}(?:\s*[ap]m)?)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(\d{4}-\d{2}-\d{2})[T\s](\d{2}:\d{2})",
        re.IGNORECASE,
    ),
]


@dataclass
class MeetingEvent:
    title: str
    start: datetime | None = None
    end: datetime | None = None
    location: str = ""
    meeting_url: str = ""
    zoom_url: str = ""
    meet_url: str = ""
    teams_url: str = ""
    description: str = ""
    attendees: list[str] = field(default_factory=list)
    source_email: str = ""
    source_message_id: str = ""
    ics_uid: str = ""
    confidence: float = 0.0

    def to_calendar_event(self) -> dict[str, Any]:
        start = self.start or datetime.now() + timedelta(hours=1)
        end = self.end or (start + timedelta(hours=1))
        url = self.zoom_url or self.meet_url or self.teams_url or self.meeting_url

        description_parts = [self.description]
        if url:
            description_parts.append(f"\n\nJoin meeting: {url}")
        if self.source_email:
            description_parts.append(f"\nSource: {self.source_email}")

        event: dict[str, Any] = {
            "summary": self.title,
            "description": "\n".join(p for p in description_parts if p),
            "start": {"dateTime": start.isoformat(), "timeZone": "Asia/Jakarta"},
            "end": {"dateTime": end.isoformat(), "timeZone": "Asia/Jakarta"},
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {"method": "popup", "minutes": 10},
                    {"method": "popup", "minutes": 2},
                ],
            },
        }

        if url:
            event["location"] = url
        elif self.location:
            event["location"] = self.location

        if self.ics_uid:
            event["iCalUID"] = self.ics_uid

        if self.attendees:
            event["attendees"] = [{"email": a} for a in self.attendees]

        if self.meet_url:
            event["conferenceData"] = {
                "createRequest": {
                    "requestId": f"meet-{self.ics_uid or start.timestamp()}",
                    "conferenceSolutionKey": {"type": "hangoutsMeet"},
                }
            }

        return event


def _html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text("\n", strip=True)


def _extract_links(text: str) -> dict[str, str]:
    links: dict[str, str] = {}
    for match in MEETING_LINK_RE.finditer(text):
        url = match.group(0).rstrip(".,;)")
        if "zoom.us" in url.lower():
            links["zoom"] = url
        elif "meet.google.com" in url.lower():
            links["meet"] = url
        elif "teams" in url.lower():
            links["teams"] = url
        else:
            links.setdefault("other", url)
    return links


def _parse_ics_attachment(data: bytes) -> MeetingEvent | None:
    try:
        cal = Calendar.from_ical(data)
    except Exception:
        return None

    for component in cal.walk():
        if component.name != "VEVENT":
            continue

        summary = str(component.get("summary", "Meeting"))
        start = component.get("dtstart")
        end = component.get("dtend")
        location = str(component.get("location", ""))
        description = str(component.get("description", ""))
        uid = str(component.get("uid", ""))

        start_dt = start.dt if start else None
        end_dt = end.dt if end else None

        if isinstance(start_dt, datetime) and start_dt.tzinfo is None:
            start_dt = start_dt.replace(tzinfo=None)
        if isinstance(end_dt, datetime) and end_dt.tzinfo is None:
            end_dt = end_dt.replace(tzinfo=None)

        links = _extract_links(f"{location}\n{description}")
        attendees = [
            str(a).replace("mailto:", "")
            for a in (component.get("attendee") or [])
        ]

        return MeetingEvent(
            title=summary,
            start=start_dt if isinstance(start_dt, datetime) else None,
            end=end_dt if isinstance(end_dt, datetime) else None,
            location=location,
            meeting_url=links.get("other", ""),
            zoom_url=links.get("zoom", ""),
            meet_url=links.get("meet", ""),
            teams_url=links.get("teams", ""),
            description=description,
            attendees=attendees,
            ics_uid=uid,
            confidence=0.95,
        )
    return None


def _guess_datetime(text: str, email_date: datetime | None = None) -> tuple[datetime | None, datetime | None]:
    for pattern in DATE_PATTERNS:
        match = pattern.search(text)
        if match:
            try:
                date_str = " ".join(match.groups())
                start = date_parser.parse(date_str, fuzzy=True, default=email_date or datetime.now())
                return start, start + timedelta(hours=1)
            except (ValueError, TypeError):
                continue

    try:
        start = date_parser.parse(text, fuzzy=True, default=email_date or datetime.now())
        if start.year > 2000:
            return start, start + timedelta(hours=1)
    except (ValueError, TypeError):
        pass

    return None, None


def parse_gmail_message(message: dict[str, Any], account_email: str = "") -> MeetingEvent | None:
    """Parse a Gmail API message resource into a MeetingEvent if it looks like a meeting."""
    payload = message.get("payload", {})
    headers = {h["name"].lower(): h["value"] for h in payload.get("headers", [])}

    subject = headers.get("subject", "")
    from_addr = headers.get("from", "")
    date_header = headers.get("date", "")

    email_date = None
    if date_header:
        try:
            email_date = parsedate_to_datetime(date_header)
        except (ValueError, TypeError):
            pass

    body_text = ""
    body_html = ""
    ics_data: bytes | None = None

    def walk_parts(part: dict) -> None:
        nonlocal body_text, body_html, ics_data
        mime = part.get("mimeType", "")
        filename = part.get("filename", "")

        if part.get("body", {}).get("attachmentId") and filename.endswith(".ics"):
            ics_data = base64.urlsafe_b64decode(
                part.get("body", {}).get("data", "") + "=="
            )
            return

        data = part.get("body", {}).get("data", "")
        if data:
            decoded = base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
            if mime == "text/plain":
                body_text += decoded
            elif mime == "text/html":
                body_html += decoded
            elif mime == "text/calendar" or mime == "application/ics":
                ics_data = base64.urlsafe_b64decode(data + "==")

        for sub in part.get("parts", []):
            walk_parts(sub)

    walk_parts(payload)

    if ics_data:
        event = _parse_ics_attachment(ics_data)
        if event:
            event.title = event.title or subject
            event.source_email = account_email
            event.source_message_id = message.get("id", "")
            return event

    full_text = body_text or (_html_to_text(body_html) if body_html else "")
    combined = f"{subject}\n{full_text}"

    links = _extract_links(combined)
    if not links and not any(
        kw in combined.lower()
        for kw in ["meeting", "undangan", "interview", "wawancara", "jadwal", "zoom", "invite"]
    ):
        return None

    start, end = _guess_datetime(combined, email_date)
    confidence = 0.5
    if links:
        confidence += 0.3
    if start:
        confidence += 0.15
    if "invitation" in subject.lower() or "undangan" in subject.lower():
        confidence += 0.1

    if confidence < 0.5:
        return None

    return MeetingEvent(
        title=subject or "Meeting",
        start=start,
        end=end,
        meeting_url=links.get("other", ""),
        zoom_url=links.get("zoom", ""),
        meet_url=links.get("meet", ""),
        teams_url=links.get("teams", ""),
        description=full_text[:2000],
        source_email=account_email,
        source_message_id=message.get("id", ""),
        confidence=confidence,
    )
