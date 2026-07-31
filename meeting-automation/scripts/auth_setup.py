#!/usr/bin/env python3
"""Interactive OAuth setup for each configured Gmail account."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.main import cmd_auth  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description="Authorize Gmail/Calendar OAuth tokens")
    p.add_argument("--email", help="Single account email to authorize")
    args = p.parse_args()
    return cmd_auth(args)


if __name__ == "__main__":
    raise SystemExit(main())
