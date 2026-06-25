from __future__ import annotations

import json
import os
from pathlib import Path

APP_DIR = Path(os.environ.get("APP_DIR", "/app"))
OUTPUT_PATH = APP_DIR / "output" / "report.json"


def _by_user() -> dict[str, dict[str, object]]:
    payload = json.loads(OUTPUT_PATH.read_text())
    return {row["userId"]: row for row in payload["records"]}


def test_report_exists() -> None:
    assert OUTPUT_PATH.exists()


def test_thresholds_lock_at_the_boundary() -> None:
    rows = _by_user()
    assert rows["u-pdf-boundary"]["pdfBankLocked"] is True
    assert rows["u-sim-boundary"]["simulationsLocked"] is True
    assert rows["u-sim-boundary"]["mindmapsLocked"] is True


def test_referral_quota_unlocks_all_surfaces_at_exact_target() -> None:
    rows = _by_user()
    assert rows["u-quota-exact"] == {
        "userId": "u-quota-exact",
        "pdfBankLocked": False,
        "simulationsLocked": False,
        "mindmapsLocked": False,
    }


def test_partial_progress_does_not_unlock_any_exhausted_surface() -> None:
    rows = _by_user()
    assert rows["u-partial"] == {
        "userId": "u-partial",
        "pdfBankLocked": True,
        "simulationsLocked": True,
        "mindmapsLocked": True,
    }
