#!/usr/bin/env python3
"""Local webhook server that opens Zoom/meeting links when meeting time arrives."""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import webbrowser
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import parse_qs, urlparse

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

PORT = int(os.environ.get("LOCAL_WEBHOOK_PORT", "8765"))
ZOOM_ACCOUNT = os.environ.get("ZOOM_ACCOUNT_EMAIL", "yusuf.consultan@gmail.com")


def open_meeting_url(url: str) -> bool:
    """Open meeting URL in default browser or Zoom app."""
    if not url:
        return False

    logger.info("Opening meeting: %s", url)

    # Try zoommtg:// protocol for Zoom links
    if "zoom.us" in url.lower():
        meeting_id = url.split("/j/")[-1].split("?")[0] if "/j/" in url else ""
        if meeting_id:
            zoom_uri = f"zoommtg://zoom.us/join?confno={meeting_id}"
            try:
                if sys.platform == "darwin":
                    subprocess.run(["open", zoom_uri], check=False)
                    return True
                elif sys.platform == "linux":
                    subprocess.run(["xdg-open", zoom_uri], check=False)
                    return True
                elif sys.platform == "win32":
                    os.startfile(zoom_uri)  # type: ignore[attr-defined]
                    return True
            except Exception as e:
                logger.warning("zoommtg:// failed, falling back to browser: %s", e)

    # Fallback: open in browser
    webbrowser.open(url)
    return True


def check_upcoming_meetings() -> None:
    """Poll Google Calendar for meetings starting in the next 2 minutes."""
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        from src.google_auth import get_calendar_service

        calendar = get_calendar_service(ZOOM_ACCOUNT)
        now = datetime.now(timezone.utc)
        soon = now + timedelta(minutes=2)

        results = calendar.events().list(
            calendarId="primary",
            timeMin=now.isoformat(),
            timeMax=soon.isoformat(),
            singleEvents=True,
            orderBy="startTime",
        ).execute()

        for item in results.get("items", []):
            location = item.get("location", "")
            description = item.get("description", "")
            url = location
            if not url or not url.startswith("http"):
                for text in [description, location]:
                    for line in text.split("\n"):
                        if any(d in line.lower() for d in ["zoom.us", "meet.google", "teams"]):
                            url = line.strip()
                            break

            if url:
                logger.info("Meeting starting soon: %s", item.get("summary"))
                open_meeting_url(url)

    except Exception as e:
        logger.error("Calendar poll failed: %s", e)


class WebhookHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        logger.info(format % args)

    def _send_json(self, code: int, data: dict) -> None:
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)

        try:
            payload = json.loads(body) if body else {}
        except json.JSONDecodeError:
            self._send_json(400, {"error": "Invalid JSON"})
            return

        event_type = payload.get("event", payload.get("type", "meeting_start"))
        url = (
            payload.get("url")
            or payload.get("meeting_url")
            or payload.get("zoom_url")
            or payload.get("location", "")
        )
        title = payload.get("title", payload.get("summary", "Meeting"))

        if event_type in ("meeting_start", "meeting_reminder", "open_zoom"):
            success = open_meeting_url(url)
            self._send_json(200, {
                "status": "opened" if success else "no_url",
                "title": title,
                "url": url,
            })
        else:
            self._send_json(200, {"status": "ignored", "event": event_type})

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            self._send_json(200, {"status": "ok", "port": PORT})
        elif parsed.path == "/open":
            params = parse_qs(parsed.query)
            url = params.get("url", [""])[0]
            if url:
                open_meeting_url(url)
                self._send_json(200, {"status": "opened", "url": url})
            else:
                self._send_json(400, {"error": "url parameter required"})
        else:
            self._send_json(404, {"error": "not found"})


def poll_loop(interval_seconds: int = 60) -> None:
    import time
    while True:
        check_upcoming_meetings()
        time.sleep(interval_seconds)


def main() -> None:
    logger.info("Starting meeting launcher on port %d", PORT)
    logger.info("Zoom account: %s", ZOOM_ACCOUNT)

    poll_thread = Thread(target=poll_loop, daemon=True)
    poll_thread.start()

    server = HTTPServer(("0.0.0.0", PORT), WebhookHandler)
    logger.info("Webhook ready at http://localhost:%d", PORT)
    logger.info("POST meeting payload or GET /open?url=<meeting_url>")
    server.serve_forever()


if __name__ == "__main__":
    main()
