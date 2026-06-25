from __future__ import annotations

import json
import os
from pathlib import Path

APP_DIR = Path(os.environ.get("APP_DIR", "/app"))
OUTPUT_PATH = APP_DIR / "output" / "report.json"


def _deliveries() -> list[dict[str, object]]:
    return json.loads(OUTPUT_PATH.read_text())["deliveries"]


def test_report_exists() -> None:
    assert OUTPUT_PATH.exists()


def test_minimum_spacing_is_ten_seconds() -> None:
    assert [item["sentAtSec"] for item in _deliveries()] == [0, 10, 20, 30, 40, 50, 60, 70]


def test_scheduler_uses_grace_window_after_poll_end() -> None:
    ticks = [item["sentAtSec"] for item in _deliveries()]
    assert 20 in ticks
    assert 70 in ticks
    assert 80 not in ticks


def test_messages_rotate_in_sequence() -> None:
    assert [item["message"] for item in _deliveries()[:4]] == ["Poll kahan dena hai koi batao mujhe", "Pi Lens app se poll dena hai na?", "How to attempt this poll on Pi Lens?", "Poll kahan dena hai koi batao mujhe"]
