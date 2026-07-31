"""Persistent processed-message state."""

from __future__ import annotations

import json
from typing import Any

from .settings import PROCESSED_FILE, ensure_dirs


def load_processed() -> dict[str, Any]:
    ensure_dirs()
    if not PROCESSED_FILE.exists():
        return {"messages": {}}
    try:
        return json.loads(PROCESSED_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"messages": {}}


def save_processed(state: dict[str, Any]) -> None:
    ensure_dirs()
    # Cap size
    messages = state.get("messages") or {}
    if len(messages) > 5000:
        # Keep newest by recorded_at
        items = sorted(messages.items(), key=lambda kv: kv[1].get("recorded_at", ""), reverse=True)
        state["messages"] = dict(items[:4000])
    PROCESSED_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def already_processed(state: dict[str, Any], account: str, message_id: str) -> bool:
    key = f"{account}:{message_id}"
    return key in (state.get("messages") or {})


def mark_processed(
    state: dict[str, Any],
    account: str,
    message_id: str,
    meta: dict[str, Any],
) -> None:
    from datetime import datetime, timezone

    key = f"{account}:{message_id}"
    state.setdefault("messages", {})[key] = {
        **meta,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }
