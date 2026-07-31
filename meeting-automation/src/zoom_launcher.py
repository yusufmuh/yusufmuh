"""Open Zoom / Meet links on the local device when meetings start."""

from __future__ import annotations

import re
import subprocess
import sys
import webbrowser
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlparse, parse_qs
from zoneinfo import ZoneInfo

from .calendar_client import list_upcoming_with_links
from .settings import DATA_DIR, env, ensure_dirs

OPENED_FILE = DATA_DIR / "opened_meetings.json"


def _load_opened() -> set[str]:
    ensure_dirs()
    if not OPENED_FILE.exists():
        return set()
    import json

    try:
        data = json.loads(OPENED_FILE.read_text(encoding="utf-8"))
        return set(data.get("ids") or [])
    except Exception:
        return set()


def _save_opened(ids: set[str]) -> None:
    import json

    ensure_dirs()
    # Keep last 500
    trimmed = list(ids)[-500:]
    OPENED_FILE.write_text(json.dumps({"ids": trimmed}, indent=2), encoding="utf-8")


def extract_join_url(event: dict[str, Any]) -> str | None:
    private = ((event.get("extendedProperties") or {}).get("private") or {})
    if private.get("meeting_url"):
        return private["meeting_url"]

    location = event.get("location") or ""
    description = event.get("description") or ""
    hangout = event.get("hangoutLink")
    if hangout:
        return hangout

    blob = f"{location}\n{description}"
    patterns = [
        r"https?://[\w.-]*zoom\.us/[^\s<>\"']+",
        r"https?://meet\.google\.com/[a-z0-9\-]+",
        r"https?://teams\.microsoft\.com/l/meetup-join/[^\s<>\"']+",
    ]
    for pat in patterns:
        m = re.search(pat, blob, re.I)
        if m:
            return m.group(0).rstrip(").,;]>\"'")
    return None


def zoom_desktop_uri(https_url: str) -> str | None:
    """Convert https://zoom.us/j/ID?pwd=... to zoommtg:// deep link when possible."""
    try:
        parsed = urlparse(https_url)
        if "zoom.us" not in parsed.netloc and "zoom.com" not in parsed.netloc:
            return None
        # /j/123456789 or /w/…
        m = re.search(r"/(?:j|w)/(\d+)", parsed.path)
        if not m:
            return None
        meeting_id = m.group(1)
        qs = parse_qs(parsed.query)
        pwd = (qs.get("pwd") or [None])[0]
        uri = f"zoommtg://zoom.us/join?action=join&confno={meeting_id}"
        if pwd:
            uri += f"&pwd={pwd}"
        return uri
    except Exception:
        return None


def open_meeting_link(url: str) -> bool:
    """Open Zoom desktop app when possible, otherwise default browser."""
    deep = zoom_desktop_uri(url)
    targets = [t for t in [deep, url] if t]

    for target in targets:
        try:
            if sys.platform == "darwin":
                subprocess.run(["open", target], check=False)
                return True
            if sys.platform.startswith("linux"):
                # Prefer zoommtg handler / xdg-open
                subprocess.run(["xdg-open", target], check=False)
                return True
            if sys.platform.startswith("win"):
                os_start = getattr(__import__("os"), "startfile", None)
                if os_start:
                    os_start(target)
                    return True
            webbrowser.open(target)
            return True
        except Exception:
            continue
    return False


def _event_start(event: dict[str, Any], default_tz: ZoneInfo) -> datetime | None:
    start = event.get("start") or {}
    raw = start.get("dateTime") or start.get("date")
    if not raw:
        return None
    if "T" not in raw:
        # All-day — skip auto-open
        return None
    dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=default_tz)
    return dt


def open_due_meetings(
    calendar_account: str,
    *,
    calendar_id: str = "primary",
    minutes_before: int | None = None,
    default_timezone: str = "Asia/Jakarta",
) -> list[dict[str, Any]]:
    """Open join links for meetings starting within the lead window."""
    lead = minutes_before
    if lead is None:
        lead = int(env("ZOOM_OPEN_MINUTES_BEFORE", "2") or "2")

    tz = ZoneInfo(default_timezone)
    now = datetime.now(timezone.utc)
    window_end = now + timedelta(minutes=max(lead, 1) + 1)

    events = list_upcoming_with_links(
        calendar_account,
        calendar_id=calendar_id,
        time_min=now - timedelta(minutes=5),
        time_max=window_end,
    )
    opened_ids = _load_opened()
    results: list[dict[str, Any]] = []

    for event in events:
        eid = event.get("id")
        if not eid or eid in opened_ids:
            continue
        start = _event_start(event, tz)
        if not start:
            continue
        # Open when now is within [start - lead, start + 5m]
        if not (start - timedelta(minutes=lead) <= now <= start + timedelta(minutes=5)):
            continue
        url = extract_join_url(event)
        if not url:
            continue
        ok = open_meeting_link(url)
        opened_ids.add(eid)
        results.append(
            {
                "id": eid,
                "summary": event.get("summary"),
                "url": url,
                "opened": ok,
                "start": start.isoformat(),
            }
        )

    if results:
        _save_opened(opened_ids)
    return results
