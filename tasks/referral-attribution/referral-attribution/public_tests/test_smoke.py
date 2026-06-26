from __future__ import annotations

import json
import os
from pathlib import Path

APP_DIR = Path(os.environ.get("APP_DIR", "/app"))
OUTPUT_PATH = APP_DIR / "output" / "report.json"


def test_report_exists() -> None:
    assert OUTPUT_PATH.exists()


def test_report_has_expected_shape() -> None:
    payload = json.loads(OUTPUT_PATH.read_text())
    assert isinstance(payload.get("records"), list)
    assert payload["records"]
    row = payload["records"][0]
    assert {"userId", "referralCount", "referredUsers"} <= set(row)
