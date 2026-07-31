"""Gmail fetch helpers."""

from __future__ import annotations

import base64
from datetime import datetime, timedelta
from email.header import decode_header, make_header
from typing import Any
from zoneinfo import ZoneInfo

from .auth import gmail_service
from .meeting_parser import (
    build_meeting_from_email,
    looks_like_meeting,
    parse_email_date,
)
from .settings import env


def _decode_header(value: str | None) -> str:
    if not value:
        return ""
    try:
        return str(make_header(decode_header(value)))
    except Exception:
        return value


def _header_map(payload: dict[str, Any]) -> dict[str, str]:
    headers = payload.get("headers") or []
    return {h["name"].lower(): h.get("value", "") for h in headers}


def _walk_parts(payload: dict[str, Any]) -> list[tuple[str, str]]:
    """Return list of (mimeType, decoded text)."""
    results: list[tuple[str, str]] = []
    mime = payload.get("mimeType", "")
    body = payload.get("body") or {}
    data = body.get("data")
    if data:
        try:
            text = base64.urlsafe_b64decode(data.encode("utf-8")).decode("utf-8", errors="replace")
            results.append((mime, text))
        except Exception:
            pass
    for part in payload.get("parts") or []:
        results.extend(_walk_parts(part))
    return results


def extract_body(payload: dict[str, Any]) -> str:
    parts = _walk_parts(payload)
    # Prefer text/calendar + text/plain + text/html
    calendar = "\n".join(t for m, t in parts if "calendar" in m)
    plains = [t for m, t in parts if m == "text/plain"]
    htmls = [t for m, t in parts if m == "text/html"]
    chunks = []
    if calendar:
        chunks.append(calendar)
    if plains:
        chunks.append(plains[0])
    elif htmls:
        chunks.append(htmls[0])
    elif parts:
        chunks.append(parts[0][1])
    return "\n".join(chunks)


def list_candidate_messages(
    email: str,
    *,
    lookback_days: int | None = None,
    max_results: int = 100,
) -> list[dict[str, str]]:
    days = lookback_days or int(env("EMAIL_LOOKBACK_DAYS", "14") or "14")
    after = (datetime.utcnow() - timedelta(days=days)).strftime("%Y/%m/%d")
    # Broad query; precise filtering happens in parser
    query = (
        f"after:{after} "
        "(undangan OR meeting OR interview OR wawancara OR jadwal OR kalender "
        "OR invite OR invitation OR zoom OR \"google meet\" OR meet.google "
        "OR appointment OR rapat OR pertemuan OR filename:ics OR has:attachment)"
    )
    service = gmail_service(email, interactive=False)
    resp = (
        service.users()
        .messages()
        .list(userId="me", q=query, maxResults=max_results)
        .execute()
    )
    return resp.get("messages") or []


def fetch_message(email: str, message_id: str) -> dict[str, Any]:
    service = gmail_service(email, interactive=False)
    return (
        service.users()
        .messages()
        .get(userId="me", id=message_id, format="full")
        .execute()
    )


def message_to_meeting(
    email: str,
    raw: dict[str, Any],
    keywords: list[str],
    default_timezone: str,
):
    payload = raw.get("payload") or {}
    headers = _header_map(payload)
    subject = _decode_header(headers.get("subject"))
    sender = _decode_header(headers.get("from"))
    body = extract_body(payload)
    tz = ZoneInfo(default_timezone)
    email_date = parse_email_date(headers.get("date"), tz)

    is_meeting, matched = looks_like_meeting(subject, body, keywords)
    if not is_meeting:
        return None

    return build_meeting_from_email(
        subject=subject,
        body=body,
        sender=sender,
        message_id=raw.get("id", ""),
        account=email,
        keywords_matched=matched,
        email_date=email_date,
        default_timezone=default_timezone,
    )
