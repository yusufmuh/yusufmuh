"""Unit tests for meeting detection/parsing (no Google API required)."""

from __future__ import annotations

import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from src.meeting_parser import (
    build_meeting_from_email,
    extract_meeting_links,
    looks_like_meeting,
)


KEYWORDS = [
    "undangan",
    "meeting",
    "interview",
    "jadwal",
    "kalender",
    "zoom",
    "google meet",
    "rapat",
]


class MeetingParserTests(unittest.TestCase):
    def test_detects_zoom_invite(self):
        subject = "Undangan Meeting Project Kickoff"
        body = """
        Halo, undangan rapat berikut:
        Waktu: 15 August 2026 14:00
        Join Zoom: https://zoom.us/j/12345678901?pwd=abcXYZ
        """
        ok, matched = looks_like_meeting(subject, body, KEYWORDS)
        self.assertTrue(ok)
        self.assertTrue(any(m in matched for m in ("undangan", "meeting", "zoom", "meeting-link")))

        event = build_meeting_from_email(
            subject=subject,
            body=body,
            sender="boss@example.com",
            message_id="m1",
            account="yusuf.consultan@gmail.com",
            keywords_matched=matched,
            email_date=datetime(2026, 8, 1, tzinfo=ZoneInfo("Asia/Jakarta")),
        )
        self.assertIsNotNone(event)
        assert event is not None
        self.assertIn("zoom.us/j/12345678901", event.meeting_url or "")
        self.assertEqual(event.start.hour, 14)

    def test_detects_google_meet(self):
        links = extract_meeting_links("join https://meet.google.com/abc-defg-hij please")
        self.assertEqual(links[0], "https://meet.google.com/abc-defg-hij")

    def test_ics_priority(self):
        body = """BEGIN:VCALENDAR
BEGIN:VEVENT
DTSTART:20260820T090000Z
DTEND:20260820T100000Z
SUMMARY:Interview Backend
LOCATION:https://zoom.us/j/99988877766
END:VEVENT
END:VCALENDAR"""
        ok, matched = looks_like_meeting("Interview", body, KEYWORDS)
        self.assertTrue(ok)
        event = build_meeting_from_email(
            subject="Interview",
            body=body,
            sender="hr@company.com",
            message_id="m2",
            account="a@b.com",
            keywords_matched=matched,
            email_date=None,
        )
        self.assertIsNotNone(event)
        assert event is not None
        self.assertEqual(event.title, "Interview Backend")
        self.assertIn("99988877766", event.meeting_url or event.location)

    def test_skips_without_time(self):
        ok, matched = looks_like_meeting("Hello", "lihat dokumen undangan di lampiran", KEYWORDS)
        self.assertTrue(ok)
        event = build_meeting_from_email(
            subject="Hello",
            body="lihat dokumen undangan di lampiran tanpa jam",
            sender="x@y.com",
            message_id="m3",
            account="a@b.com",
            keywords_matched=matched,
            email_date=datetime(2026, 7, 31, tzinfo=ZoneInfo("Asia/Jakarta")),
        )
        self.assertIsNone(event)


if __name__ == "__main__":
    unittest.main()
