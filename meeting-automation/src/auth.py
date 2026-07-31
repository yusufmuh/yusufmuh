"""Google OAuth helpers for multi-account Gmail + Calendar."""

from __future__ import annotations

from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from .settings import CREDENTIALS_FILE, SCOPES, TOKENS_DIR, ensure_dirs


def token_path(email: str) -> Path:
    safe = email.strip().lower().replace("@", "_at_").replace(".", "_")
    return TOKENS_DIR / f"{safe}.json"


def get_credentials(email: str, interactive: bool = True) -> Credentials:
    """Load or create OAuth credentials for one Google account."""
    ensure_dirs()
    path = token_path(email)
    creds: Credentials | None = None

    if path.exists():
        creds = Credentials.from_authorized_user_file(str(path), SCOPES)

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        path.write_text(creds.to_json(), encoding="utf-8")
        return creds

    if not interactive:
        raise RuntimeError(
            f"No valid token for {email}. Run: python scripts/auth_setup.py --email {email}"
        )

    if not CREDENTIALS_FILE.exists():
        raise FileNotFoundError(
            f"Missing {CREDENTIALS_FILE}. Download OAuth Desktop client JSON "
            "from Google Cloud Console and save it as credentials.json "
            "(see README)."
        )

    flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
    print(f"\n>>> Authorize Google account: {email}")
    print("    Sign in with THAT exact account in the browser window.\n")
    creds = flow.run_local_server(port=0, prompt="consent")
    path.write_text(creds.to_json(), encoding="utf-8")
    return creds


def gmail_service(email: str, interactive: bool = False):
    creds = get_credentials(email, interactive=interactive)
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def calendar_service(email: str, interactive: bool = False):
    creds = get_credentials(email, interactive=interactive)
    return build("calendar", "v3", credentials=creds, cache_discovery=False)


def verify_account_email(email: str, interactive: bool = True) -> str:
    """Return the authenticated profile email (may differ if user picked wrong account)."""
    service = gmail_service(email, interactive=interactive)
    profile = service.users().getProfile(userId="me").execute()
    return profile.get("emailAddress", email)
