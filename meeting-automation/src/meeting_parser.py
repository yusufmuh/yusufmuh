"""Detect meeting invites and extract event fields from email content."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Any
from zoneinfo import ZoneInfo

from dateutil import parser as date_parser

MEETING_LINK_PATTERNS = [
    re.compile(r"https?://[\w.-]*zoom\.us/[^\s<>\"']+", re.I),
    re.compile(r"https?://[\w.-]*zoom\.com/[^\s<>\"']+", re.I),
    re.compile(r"https?://meet\.google\.com/[a-z0-9\-]+", re.I),
    re.compile(r"https?://teams\.microsoft\.com/l/meetup-join/[^\s<>\"']+", re.I),
    re.compile(r"https?://[\w.-]*webex\.com/[^\s<>\"']+", re.I),
    re.compile(r"https?://[\w.-]*whereby\.com/[^\s<>\"']+", re.I),
    re.compile(r"https?://[\w.-]*meet\.jit\.si/[^\s<>\"']+", re.I),
]

ZOOM_ID_PATTERN = re.compile(
    r"(?:zoom|meeting)\s*(?:id|ID)\s*[:=]?\s*(\d[\d\s\-]{8,})",
    re.I,
)
ZOOM_PASS_PATTERN = re.compile(
    r"(?:pass(?:code|word)|pwd)\s*[:=]?\s*([A-Za-z0-9]+)",
    re.I,
)

# Common "when" cues near a datetime
WHEN_CUES = re.compile(
    r"(?:when|waktu|tanggal|jadwal|schedule|starts?(?:\s+at)?|mulai|"
    r"date\s*[&/]\s*time|hari)\s*[:\-]?\s*(.+)",
    re.I,
)

ICS_DTSTART = re.compile(r"DTSTART(?:;[^:]*)?:(\d{8}T\d{6}Z?)", re.I)
ICS_DTEND = re.compile(r"DTEND(?:;[^:]*)?:(\d{8}T\d{6}Z?)", re.I)
ICS_SUMMARY = re.compile(r"SUMMARY:(.+)", re.I)
ICS_LOCATION = re.compile(r"LOCATION:(.+)", re.I)
ICS_URL = re.compile(r"URL:(.+)", re.I)


@dataclass
class MeetingEvent:
    title: str
    start: datetime
    end: datetime
    description: str = ""
    location: str = ""
    meeting_url: str | None = None
    source_account: str = ""
    source_message_id: str = ""
    source_subject: str = ""
    source_from: str = ""
    confidence: str = "medium"
    keywords_matched: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "description": self.description,
            "location": self.location,
            "meeting_url": self.meeting_url,
            "source_account": self.source_account,
            "source_message_id": self.source_message_id,
            "source_subject": self.source_subject,
            "source_from": self.source_from,
            "confidence": self.confidence,
            "keywords_matched": self.keywords_matched,
        }


def _strip_html(text: str) -> str:
    text = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", text)
    text = re.sub(r"(?s)<br\s*/?>", "\n", text)
    text = re.sub(r"(?s)</p>", "\n", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&lt;", "<", text)
    text = re.sub(r"&gt;", ">", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def extract_meeting_links(text: str) -> list[str]:
    links: list[str] = []
    for pattern in MEETING_LINK_PATTERNS:
        for match in pattern.findall(text):
            cleaned = match.rstrip(").,;]>\"'")
            if cleaned not in links:
                links.append(cleaned)
    return links


def looks_like_meeting(subject: str, body: str, keywords: list[str]) -> tuple[bool, list[str]]:
    haystack = f"{subject}\n{body}".lower()
    matched = [kw for kw in keywords if kw.lower() in haystack]
    links = extract_meeting_links(f"{subject}\n{body}")
    if links:
        matched.append("meeting-link")
    # ICS calendar invite markers
    if "text/calendar" in haystack or "begin:vcalendar" in haystack or "dtstart" in haystack:
        matched.append("ics")
    return (bool(matched), matched)


def _parse_ics_datetime(value: str, default_tz: ZoneInfo) -> datetime | None:
    value = value.strip()
    try:
        if value.endswith("Z"):
            return datetime.strptime(value, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
        dt = datetime.strptime(value[:15], "%Y%m%dT%H%M%S")
        return dt.replace(tzinfo=default_tz)
    except ValueError:
        return None


def parse_ics_fields(text: str, default_tz: ZoneInfo) -> dict[str, Any]:
    out: dict[str, Any] = {}
    m = ICS_DTSTART.search(text)
    if m:
        out["start"] = _parse_ics_datetime(m.group(1), default_tz)
    m = ICS_DTEND.search(text)
    if m:
        out["end"] = _parse_ics_datetime(m.group(1), default_tz)
    m = ICS_SUMMARY.search(text)
    if m:
        out["title"] = m.group(1).strip()
    m = ICS_LOCATION.search(text)
    if m:
        out["location"] = m.group(1).strip()
    m = ICS_URL.search(text)
    if m:
        out["url"] = m.group(1).strip()
    return out


def _guess_datetime(text: str, default_tz: ZoneInfo, reference: datetime) -> datetime | None:
    candidates: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        cue = WHEN_CUES.search(line)
        if cue:
            candidates.append(cue.group(1)[:120])
        # Lines that look like dates
        if re.search(r"\b\d{1,2}[/-]\d{1,2}([/-]\d{2,4})?\b", line) or re.search(
            r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|"
            r"senin|selasa|rabu|kamis|jumat|sabtu|minggu|"
            r"monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
            line,
            re.I,
        ):
            candidates.append(line[:120])

    for raw in candidates[:12]:
        try:
            dt = date_parser.parse(raw, fuzzy=True, default=reference)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=default_tz)
            # Ignore clearly ancient / far-future junk
            if abs((dt - reference).days) > 366:
                continue
            return dt
        except (ValueError, OverflowError, TypeError):
            continue
    return None


def build_meeting_from_email(
    *,
    subject: str,
    body: str,
    sender: str,
    message_id: str,
    account: str,
    keywords_matched: list[str],
    email_date: datetime | None,
    default_timezone: str = "Asia/Jakarta",
) -> MeetingEvent | None:
    tz = ZoneInfo(default_timezone)
    plain = _strip_html(body)
    combined = f"{subject}\n{plain}"
    links = extract_meeting_links(combined)
    ics = parse_ics_fields(body + "\n" + plain, tz)

    reference = email_date or datetime.now(tz)
    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=tz)

    start = ics.get("start")
    end = ics.get("end")
    if not start:
        start = _guess_datetime(combined, tz, reference)
    if not start:
        # No usable time → skip calendar write (still not an event)
        return None

    if not end:
        end = start + timedelta(hours=1)

    title = (ics.get("title") or subject or "Meeting").strip() or "Meeting"
    location = ics.get("location") or ""
    meeting_url = links[0] if links else ics.get("url")

    if meeting_url and not location:
        location = meeting_url

    # Zoom meeting id → join URL if no link found
    if not meeting_url:
        mid = ZOOM_ID_PATTERN.search(combined)
        if mid:
            digits = re.sub(r"\D", "", mid.group(1))
            meeting_url = f"https://zoom.us/j/{digits}"
            pwd = ZOOM_PASS_PATTERN.search(combined)
            if pwd:
                meeting_url += f"?pwd={pwd.group(1)}"
            location = meeting_url

    confidence = "high" if ("ics" in keywords_matched or links) else "medium"

    description_parts = [
        f"Auto-imported from email ({account})",
        f"From: {sender}",
        f"Subject: {subject}",
        f"Matched: {', '.join(keywords_matched)}",
    ]
    if meeting_url:
        description_parts.append(f"Join: {meeting_url}")
    description_parts.append("")
    description_parts.append(plain[:2500])

    return MeetingEvent(
        title=title[:200],
        start=start,
        end=end,
        description="\n".join(description_parts),
        location=location[:1024],
        meeting_url=meeting_url,
        source_account=account,
        source_message_id=message_id,
        source_subject=subject,
        source_from=sender,
        confidence=confidence,
        keywords_matched=keywords_matched,
    )


def parse_email_date(header_value: str | None, default_tz: ZoneInfo) -> datetime | None:
    if not header_value:
        return None
    try:
        dt = parsedate_to_datetime(header_value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=default_tz)
        return dt
    except (TypeError, ValueError, IndexError):
        return None
