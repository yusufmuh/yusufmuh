"""Google API authentication helpers for multiple accounts."""

from __future__ import annotations

import json
import os
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/calendar.events",
]

BASE_DIR = Path(__file__).resolve().parent.parent
CREDENTIALS_DIR = BASE_DIR / "credentials"
TOKENS_DIR = CREDENTIALS_DIR / "tokens"


def _token_path(email: str) -> Path:
    safe_name = email.replace("@", "_at_").replace(".", "_")
    return TOKENS_DIR / f"{safe_name}.json"


def get_credentials(email: str) -> Credentials:
    """Load or refresh OAuth credentials for a given email account."""
    TOKENS_DIR.mkdir(parents=True, exist_ok=True)
    token_file = _token_path(email)
    creds = None

    if token_file.exists():
        creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        token_file.write_text(creds.to_json())
        return creds

    creds_path = os.environ.get(
        "GOOGLE_CREDENTIALS_PATH",
        str(CREDENTIALS_DIR / "credentials.json"),
    )
    if not Path(creds_path).exists():
        raise FileNotFoundError(
            f"OAuth credentials not found at {creds_path}. "
            "Download credentials.json from Google Cloud Console."
        )

    flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
    creds = flow.run_local_server(port=0, prompt="consent", login_hint=email)
    token_file.write_text(creds.to_json())
    return creds


def get_gmail_service(email: str):
    return build("gmail", "v1", credentials=get_credentials(email))


def get_calendar_service(email: str):
    return build("calendar", "v3", credentials=get_credentials(email))


def list_connected_accounts() -> list[str]:
    """Return list of emails that have stored OAuth tokens."""
    if not TOKENS_DIR.exists():
        return []
    accounts = []
    for token_file in TOKENS_DIR.glob("*.json"):
        name = token_file.stem.replace("_at_", "@").replace("_", ".")
        # Fix domain dots that were over-replaced
        parts = name.split("@")
        if len(parts) == 2:
            local, domain = parts
            domain = domain.replace(".", ".", 1) if "." not in domain else domain
            # Reconstruct properly
            raw = token_file.stem
            email = raw.replace("_at_", "@").replace("_", ".")
            # Better: read email from token
            try:
                data = json.loads(token_file.read_text())
                # Token doesn't store email; use filename mapping from config
                accounts.append(email)
            except json.JSONDecodeError:
                pass
    return accounts
