"""Shared paths, env, and config loading."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
TOKENS_DIR = ROOT / "tokens"
DATA_DIR = ROOT / "data"
CREDENTIALS_FILE = ROOT / "credentials.json"
CONFIG_FILE = ROOT / "config.yaml"
STATE_FILE = DATA_DIR / "state.json"
PROCESSED_FILE = DATA_DIR / "processed_messages.json"

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar",
]


def load_env() -> None:
    load_dotenv(ROOT / ".env")


def env(key: str, default: str | None = None) -> str | None:
    return os.getenv(key, default)


def load_config() -> dict[str, Any]:
    with CONFIG_FILE.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def ensure_dirs() -> None:
    TOKENS_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
