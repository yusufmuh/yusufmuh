"""Google Calendar create / dedupe helpers."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .auth import calendar_service
from .meeting_parser import MeetingEvent


def _rfc3339(dt: datetime) -> str:
    if dt.tzinfo is None:
        raise ValueError("datetime must be timezone-aware")
    return dt.isoformat()


def find_duplicate(
    calendar_account: str,
    event: MeetingEvent,
    calendar_id: str = "primary",
) -> dict[str, Any] | None:
    """Find an existing event with same source message id or similar title+start."""
    service = calendar_service(calendar_account, interactive=False)
    marker = f"source_message_id={event.source_message_id}"
    # Search a window around the start
    time_min = event.start.isoformat()
    time_max = event.end.isoformat()
    resp = (
        service.events()
        .list(
            calendarId=calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            maxResults=20,
            q=event.title[:40],
        )
        .execute()
    )
    for item in resp.get("items") or []:
        desc = item.get("description") or ""
        if marker in desc:
            return item
        # Soft match: same title + overlapping start within 2 minutes via extended props
        ext = (item.get("extendedProperties") or {}).get("private") or {}
        if ext.get("source_message_id") == event.source_message_id:
            return item
    return None


def upsert_event(
    calendar_account: str,
    event: MeetingEvent,
    calendar_id: str = "primary",
) -> dict[str, Any]:
    service = calendar_service(calendar_account, interactive=False)
    existing = find_duplicate(calendar_account, event, calendar_id=calendar_id)

    body: dict[str, Any] = {
        "summary": event.title,
        "description": event.description,
        "location": event.location,
        "start": {"dateTime": _rfc3339(event.start)},
        "end": {"dateTime": _rfc3339(event.end)},
        "extendedProperties": {
            "private": {
                "source_message_id": event.source_message_id,
                "source_account": event.source_account,
                "meeting_url": event.meeting_url or "",
                "imported_by": "meeting-automation",
            }
        },
        "reminders": {
            "useDefault": False,
            "overrides": [
                {"method": "popup", "minutes": 10},
                {"method": "popup", "minutes": 2},
            ],
        },
    }
    if event.meeting_url:
        body["description"] = event.description
        # ConferenceData only works for Meet created via API; keep URL in location/description

    if existing:
        updated = (
            service.events()
            .update(calendarId=calendar_id, eventId=existing["id"], body=body)
            .execute()
        )
        return {"action": "updated", "event": updated}

    created = service.events().insert(calendarId=calendar_id, body=body).execute()
    return {"action": "created", "event": created}


def list_upcoming_with_links(
    calendar_account: str,
    *,
    calendar_id: str = "primary",
    time_min: datetime,
    time_max: datetime,
) -> list[dict[str, Any]]:
    service = calendar_service(calendar_account, interactive=False)
    resp = (
        service.events()
        .list(
            calendarId=calendar_id,
            timeMin=_rfc3339(time_min),
            timeMax=_rfc3339(time_max),
            singleEvents=True,
            orderBy="startTime",
            maxResults=50,
        )
        .execute()
    )
    return resp.get("items") or []
