"""MCP server exposing Gmail + Calendar tools for multiple Google accounts."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from .email_calendar_sync import create_calendar_events, scan_account, sync_all
from .google_auth import get_calendar_service, get_gmail_service
from .meeting_parser import parse_gmail_message

logger = logging.getLogger(__name__)
mcp = FastMCP("meeting-automation")

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config" / "accounts.json"


def _load_accounts() -> list[dict]:
    return json.loads(CONFIG_PATH.read_text())["accounts"]


@mcp.tool()
def accounts_list() -> str:
    """List all configured Gmail accounts to monitor."""
    accounts = _load_accounts()
    return json.dumps(
        [{"email": a["email"], "nickname": a["nickname"], "role": a["role"]} for a in accounts],
        indent=2,
    )


@mcp.tool()
def gmail_search(email: str, query: str = "", max_results: int = 20) -> str:
    """Search Gmail for meeting-related emails. Uses meeting query if query is empty."""
    from .email_calendar_sync import GMAIL_QUERY

    gmail = get_gmail_service(email)
    q = query or GMAIL_QUERY
    results = gmail.users().messages().list(userId="me", q=q, maxResults=max_results).execute()

    messages = []
    for ref in results.get("messages", []):
        msg = gmail.users().messages().get(userId="me", id=ref["id"], format="metadata",
                                            metadataHeaders=["Subject", "From", "Date"]).execute()
        headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
        messages.append({
            "id": ref["id"],
            "subject": headers.get("Subject", ""),
            "from": headers.get("From", ""),
            "date": headers.get("Date", ""),
        })

    return json.dumps(messages, indent=2)


@mcp.tool()
def gmail_read_meeting(email: str, message_id: str) -> str:
    """Read a Gmail message and parse it as a meeting event."""
    gmail = get_gmail_service(email)
    message = gmail.users().messages().get(userId="me", id=message_id, format="full").execute()
    event = parse_gmail_message(message, account_email=email)
    if not event:
        return json.dumps({"error": "Not a meeting email"})
    return json.dumps({
        "title": event.title,
        "start": event.start.isoformat() if event.start else None,
        "end": event.end.isoformat() if event.end else None,
        "zoom_url": event.zoom_url,
        "meet_url": event.meet_url,
        "teams_url": event.teams_url,
        "confidence": event.confidence,
        "description": event.description[:500],
    }, indent=2)


@mcp.tool()
def calendar_list_events(email: str, max_results: int = 10) -> str:
    """List upcoming calendar events for an account."""
    from datetime import datetime, timezone

    calendar = get_calendar_service(email)
    now = datetime.now(timezone.utc).isoformat()
    results = calendar.events().list(
        calendarId="primary",
        timeMin=now,
        maxResults=max_results,
        singleEvents=True,
        orderBy="startTime",
    ).execute()

    events = []
    for item in results.get("items", []):
        events.append({
            "id": item["id"],
            "title": item.get("summary", ""),
            "start": item.get("start", {}).get("dateTime", item.get("start", {}).get("date")),
            "location": item.get("location", ""),
            "link": item.get("htmlLink", ""),
        })
    return json.dumps(events, indent=2)


@mcp.tool()
def calendar_create_event(
    email: str,
    title: str,
    start_iso: str,
    end_iso: str,
    description: str = "",
    location: str = "",
    meeting_url: str = "",
) -> str:
    """Create a Google Calendar event with optional meeting link."""
    from datetime import datetime

    from .meeting_parser import MeetingEvent

    event = MeetingEvent(
        title=title,
        start=datetime.fromisoformat(start_iso),
        end=datetime.fromisoformat(end_iso),
        description=description,
        location=location or meeting_url,
        meeting_url=meeting_url,
        zoom_url=meeting_url if "zoom" in meeting_url.lower() else "",
        meet_url=meeting_url if "meet.google" in meeting_url.lower() else "",
    )
    created = create_calendar_events([event], email)
    return json.dumps(created, indent=2, default=str)


@mcp.tool()
def sync_emails_to_calendar() -> str:
    """Scan all configured Gmail accounts and sync meeting invitations to Google Calendar."""
    result = sync_all()
    return json.dumps(result, indent=2, default=str)


if __name__ == "__main__":
    mcp.run()
