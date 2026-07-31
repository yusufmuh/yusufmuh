#!/usr/bin/env python3
"""Connect a Google account via OAuth. Run once per account."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.google_auth import get_credentials, _token_path

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "accounts.json"


def main() -> None:
    if len(sys.argv) > 1:
        email = sys.argv[1]
    else:
        accounts = json.loads(CONFIG_PATH.read_text())["accounts"]
        print("Available accounts:")
        for i, acc in enumerate(accounts, 1):
            token_exists = _token_path(acc["email"]).exists()
            status = "✓ connected" if token_exists else "✗ not connected"
            print(f"  {i}. {acc['email']} ({acc['nickname']}) — {status}")
        print()
        choice = input("Enter account number or email: ").strip()
        if choice.isdigit():
            email = accounts[int(choice) - 1]["email"]
        else:
            email = choice

    print(f"\nConnecting {email}...")
    print("A browser window will open. Sign in with this account and grant permissions.\n")

    creds = get_credentials(email)
    print(f"\n✓ Successfully connected: {email}")
    print(f"  Token saved to: {_token_path(email)}")


if __name__ == "__main__":
    main()
