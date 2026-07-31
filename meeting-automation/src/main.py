"""CLI entrypoints: sync emails → calendar, watch & open Zoom."""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone

from .auth import get_credentials, verify_account_email
from .calendar_client import upsert_event
from .gmail_client import fetch_message, list_candidate_messages, message_to_meeting
from .settings import env, load_config, load_env
from .state import already_processed, load_processed, mark_processed, save_processed
from .zoom_launcher import open_due_meetings


def _enabled_accounts(cfg: dict) -> list[dict]:
    return [a for a in (cfg.get("accounts") or []) if a.get("enabled", True)]


def cmd_auth(args: argparse.Namespace) -> int:
    load_env()
    cfg = load_config()
    accounts = _enabled_accounts(cfg)
    if args.email:
        accounts = [a for a in accounts if a["email"].lower() == args.email.lower()]
        if not accounts:
            accounts = [{"email": args.email, "label": args.email}]

    for acc in accounts:
        email = acc["email"]
        print(f"Authorizing {email} ...")
        get_credentials(email, interactive=True)
        actual = verify_account_email(email, interactive=False)
        if actual.lower() != email.lower():
            print(
                f"  WARNING: you signed in as {actual}, but config expects {email}. "
                "Re-run auth and pick the correct Google account."
            )
        else:
            print(f"  OK: {actual}")
    return 0


def cmd_sync(args: argparse.Namespace) -> int:
    load_env()
    cfg = load_config()
    keywords = cfg.get("meeting_keywords") or []
    default_tz = env("DEFAULT_TIMEZONE", "Asia/Jakarta") or "Asia/Jakarta"
    calendar_account = (
        args.calendar_account
        or cfg.get("target_calendar_account")
        or _enabled_accounts(cfg)[0]["email"]
    )
    calendar_id = env("PRIMARY_CALENDAR_ID", "primary") or "primary"
    lookback = int(args.lookback or env("EMAIL_LOOKBACK_DAYS", "14") or "14")

    state = load_processed()
    summary = {"scanned": 0, "meetings": 0, "created": 0, "updated": 0, "skipped": 0, "errors": []}

    accounts = _enabled_accounts(cfg)
    if args.email:
        accounts = [a for a in accounts if a["email"].lower() == args.email.lower()]

    for acc in accounts:
        email = acc["email"]
        print(f"\n=== Scanning {email} ===")
        try:
            messages = list_candidate_messages(email, lookback_days=lookback)
        except Exception as exc:
            msg = f"{email}: list failed: {exc}"
            print(msg)
            summary["errors"].append(msg)
            continue

        for ref in messages:
            mid = ref["id"]
            summary["scanned"] += 1
            if already_processed(state, email, mid) and not args.force:
                summary["skipped"] += 1
                continue
            try:
                raw = fetch_message(email, mid)
                meeting = message_to_meeting(email, raw, keywords, default_tz)
                if not meeting:
                    mark_processed(state, email, mid, {"status": "not_a_meeting"})
                    continue
                summary["meetings"] += 1
                if args.dry_run:
                    print(f"  [dry-run] {meeting.title} @ {meeting.start.isoformat()}")
                    mark_processed(
                        state,
                        email,
                        mid,
                        {"status": "dry_run", "title": meeting.title},
                    )
                    continue
                result = upsert_event(calendar_account, meeting, calendar_id=calendar_id)
                action = result["action"]
                summary[action] = summary.get(action, 0) + 1
                cal_event = result["event"]
                print(
                    f"  {action.upper()}: {meeting.title} "
                    f"({meeting.start.isoformat()}) "
                    f"→ {cal_event.get('htmlLink', cal_event.get('id'))}"
                )
                mark_processed(
                    state,
                    email,
                    mid,
                    {
                        "status": action,
                        "title": meeting.title,
                        "calendar_event_id": cal_event.get("id"),
                        "meeting_url": meeting.meeting_url,
                    },
                )
            except Exception as exc:
                msg = f"{email}/{mid}: {exc}"
                print(f"  ERROR: {msg}")
                summary["errors"].append(msg)

    save_processed(state)
    print("\n--- Sync summary ---")
    print(json.dumps(summary, indent=2))
    return 1 if summary["errors"] else 0


def cmd_watch(args: argparse.Namespace) -> int:
    load_env()
    cfg = load_config()
    calendar_account = (
        args.calendar_account
        or cfg.get("target_calendar_account")
        or _enabled_accounts(cfg)[0]["email"]
    )
    calendar_id = env("PRIMARY_CALENDAR_ID", "primary") or "primary"
    default_tz = env("DEFAULT_TIMEZONE", "Asia/Jakarta") or "Asia/Jakarta"
    poll = int(args.interval or env("POLL_INTERVAL_SECONDS", "120") or "120")
    sync_every = max(1, int(args.sync_every or 5))

    print(
        f"Watching… sync every {sync_every} polls, open Zoom window every {poll}s\n"
        f"Calendar account: {calendar_account}"
    )
    print("Press Ctrl+C to stop.\n")

    iteration = 0
    while True:
        iteration += 1
        try:
            if iteration == 1 or iteration % sync_every == 0:
                print(f"[{datetime.now(timezone.utc).isoformat()}] Running email sync…")
                # Reuse sync without exiting
                ns = argparse.Namespace(
                    email=args.email,
                    lookback=args.lookback,
                    force=False,
                    dry_run=False,
                    calendar_account=calendar_account,
                )
                cmd_sync(ns)

            opened = open_due_meetings(
                calendar_account,
                calendar_id=calendar_id,
                default_timezone=default_tz,
            )
            if opened:
                for item in opened:
                    print(
                        f"OPENED: {item['summary']} → {item['url']} "
                        f"(ok={item['opened']})"
                    )
            else:
                print(f"[{datetime.now(timezone.utc).isoformat()}] No meetings due.")
        except KeyboardInterrupt:
            print("\nStopped.")
            return 0
        except Exception as exc:
            print(f"Watch error: {exc}")

        time.sleep(poll)


def cmd_open_due(args: argparse.Namespace) -> int:
    load_env()
    cfg = load_config()
    calendar_account = (
        args.calendar_account
        or cfg.get("target_calendar_account")
        or _enabled_accounts(cfg)[0]["email"]
    )
    calendar_id = env("PRIMARY_CALENDAR_ID", "primary") or "primary"
    default_tz = env("DEFAULT_TIMEZONE", "Asia/Jakarta") or "Asia/Jakarta"
    opened = open_due_meetings(
        calendar_account,
        calendar_id=calendar_id,
        default_timezone=default_tz,
    )
    print(json.dumps(opened, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Email meeting → Google Calendar → auto-open Zoom"
    )
    sub = p.add_subparsers(dest="command", required=True)

    auth = sub.add_parser("auth", help="OAuth authorize configured Gmail accounts")
    auth.add_argument("--email", help="Authorize a single email only")
    auth.set_defaults(func=cmd_auth)

    sync = sub.add_parser("sync", help="Scan emails and upsert calendar events")
    sync.add_argument("--email", help="Scan a single account only")
    sync.add_argument("--lookback", type=int, help="Days of email history")
    sync.add_argument("--force", action="store_true", help="Reprocess already seen messages")
    sync.add_argument("--dry-run", action="store_true", help="Parse only, do not write calendar")
    sync.add_argument("--calendar-account", help="Google account that owns the target calendar")
    sync.set_defaults(func=cmd_sync)

    watch = sub.add_parser("watch", help="Continuously sync + open Zoom when due")
    watch.add_argument("--email", help="Limit sync to one mailbox")
    watch.add_argument("--lookback", type=int, default=3)
    watch.add_argument("--interval", type=int, help="Seconds between Zoom checks")
    watch.add_argument("--sync-every", type=int, default=5, help="Run email sync every N polls")
    watch.add_argument("--calendar-account")
    watch.set_defaults(func=cmd_watch)

    open_due = sub.add_parser("open-due", help="Open meetings that are starting now")
    open_due.add_argument("--calendar-account")
    open_due.set_defaults(func=cmd_open_due)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
