"""Sync meeting invitations from Gmail to Google Calendar."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from .google_auth import get_calendar_service, get_gmail_service
from .meeting_parser import MeetingEvent, parse_gmail_message

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config" / "accounts.json"
PROCESSED_PATH = BASE_DIR / "data" / "processed_messages.json"

GMAIL_QUERY = (
    'in:inbox ('
    'subject:(undangan OR invitation OR invite OR meeting OR interview OR wawancara OR jadwal OR schedule OR zoom OR webinar OR rapat) '
    'OR "zoom.us" OR "meet.google.com" OR "teams.microsoft.com" '
    'OR has:attachment filename:ics'
    ') newer_than:7d'
)


def _load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text())


def _load_processed() -> set[str]:
    if not PROCESSED_PATH.exists():
        return set()
    data = json.loads(PROCESSED_PATH.read_text())
    return set(data.get("message_ids", []))


def _save_processed(processed: set[str]) -> None:
    PROCESSED_PATH.parent.mkdir(parents=True, exist_ok=True)
    PROCESSED_PATH.write_text(
        json.dumps({"message_ids": sorted(processed), "updated_at": datetime.now(timezone.utc).isoformat()}, indent=2)
    )


def _event_exists(calendar_service, event: MeetingEvent, calendar_id: str = "primary") -> bool:
    """Check if a similar event already exists in calendar."""
    if event.ics_uid:
        try:
            existing = calendar_service.events().list(
                calendarId=calendar_id,
                iCalUID=event.ics_uid,
            ).execute()
            if existing.get("items"):
                return True
        except Exception:
            pass

    if event.start:
        time_min = event.start.replace(hour=0, minute=0, second=0).isoformat() + "Z"
        time_max = event.start.replace(hour=23, minute=59, second=59).isoformat() + "Z"
        try:
            results = calendar_service.events().list(
                calendarId=calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                q=event.title[:50],
            ).execute()
            for item in results.get("items", []):
                if item.get("summary", "").lower() == event.title.lower():
                    return True
        except Exception:
            pass

    return False


def scan_account(email: str, processed: set[str]) -> list[MeetingEvent]:
    """Scan one Gmail account for meeting emails."""
    gmail = get_gmail_service(email)
    events: list[MeetingEvent] = []

    try:
        results = gmail.users().messages().list(
            userId="me",
            q=GMAIL_QUERY,
            maxResults=50,
        ).execute()
    except Exception as e:
        logger.error("Failed to list messages for %s: %s", email, e)
        return events

    for msg_ref in results.get("messages", []):
        msg_id = msg_ref["id"]
        dedup_key = f"{email}:{msg_id}"
        if dedup_key in processed:
            continue

        try:
            message = gmail.users().messages().get(
                userId="me",
                id=msg_id,
                format="full",
            ).execute()
        except Exception as e:
            logger.error("Failed to read message %s: %s", msg_id, e)
            continue

        event = parse_gmail_message(message, account_email=email)
        if event:
            events.append(event)
            processed.add(dedup_key)

    return events


def create_calendar_events(
    events: list[MeetingEvent],
    calendar_email: str,
) -> list[dict]:
    """Create calendar events for parsed meetings."""
    calendar = get_calendar_service(calendar_email)
    created = []

    for event in events:
        if _event_exists(calendar, event):
            logger.info("Skipping duplicate: %s", event.title)
            continue

        body = event.to_calendar_event()
        try:
            kwargs = {"calendarId": "primary", "body": body}
            if event.meet_url or "meet.google.com" in (event.location or ""):
                kwargs["conferenceDataVersion"] = 1

            result = calendar.events().insert(**kwargs).execute()
            created.append({
                "title": event.title,
                "start": event.start.isoformat() if event.start else None,
                "url": result.get("htmlLink"),
                "meeting_url": event.zoom_url or event.meet_url or event.teams_url,
                "event_id": result.get("id"),
            })
            logger.info("Created event: %s", event.title)
        except Exception as e:
            logger.error("Failed to create event '%s': %s", event.title, e)

    return created


def sync_all() -> dict:
    """Main sync: scan all accounts, create calendar events."""
    config = _load_config()
    primary = config["primary_calendar"]
    processed = _load_processed()
    all_events: list[MeetingEvent] = []

    for account in config["accounts"]:
        email = account["email"]
        logger.info("Scanning %s...", email)
        events = scan_account(email, processed)
        all_events.extend(events)
        logger.info("Found %d meeting(s) in %s", len(events), email)

    created = create_calendar_events(all_events, primary)
    _save_processed(processed)

    return {
        "scanned_accounts": len(config["accounts"]),
        "meetings_found": len(all_events),
        "events_created": len(created),
        "created": created,
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    result = sync_all()
    print(json.dumps(result, indent=2, default=str))
