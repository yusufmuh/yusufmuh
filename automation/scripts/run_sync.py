#!/usr/bin/env python3
"""Run email-to-calendar sync once."""

import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.email_calendar_sync import sync_all

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    result = sync_all()
    print(json.dumps(result, indent=2, default=str))
