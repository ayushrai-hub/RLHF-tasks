from __future__ import annotations

import json
import os
from pathlib import Path

from referral_processor import build_report

APP_DIR = Path(os.environ.get("APP_DIR", "/app"))
OUTPUT_PATH = APP_DIR / "output" / "report.json"


def _report_by_user() -> dict[str, dict[str, object]]:
    payload = json.loads(OUTPUT_PATH.read_text())
    return {row["userId"]: row for row in payload["records"]}


def test_report_exists() -> None:
    assert OUTPUT_PATH.exists()


def test_signin_events_still_count_as_successful_referrals() -> None:
    rows = _report_by_user()
    assert rows["u-alice"]["referralCount"] >= 1
    assert "u-zoe" in rows["u-alice"]["referredUsers"]


def test_same_referee_can_credit_two_different_referrers() -> None:
    rows = _report_by_user()
    assert rows["u-bob"] == {"userId": "u-bob", "referralCount": 1, "referredUsers": ["u-zoe"]}


def test_self_referrals_do_not_count() -> None:
    rows = _report_by_user()
    assert "u-alice" not in rows["u-alice"]["referredUsers"]


def test_same_referrer_same_referee_pair_is_idempotent() -> None:
    rows = _report_by_user()
    assert rows["u-alice"] == {"userId": "u-alice", "referralCount": 2, "referredUsers": ["u-yuki", "u-zoe"]}


def test_hidden_rollout_rules_use_pair_scoped_idempotency() -> None:
    referrers = [
        {
            "userId": "u-first",
            "referralData": {
                "referralCode": "FIRST111",
                "referralCount": 0,
                "referredUsers": [],
            },
        },
        {
            "userId": "u-second",
            "referralData": {
                "referralCode": "SECOND22",
                "referralCount": 0,
                "referredUsers": [],
            },
        },
    ]
    events = [
        {"referralCode": "FIRST111", "referredUserId": "u-shared", "eventType": "signin"},
        {"referralCode": "FIRST111", "referredUserId": "u-shared", "eventType": "signup"},
        {"referralCode": "SECOND22", "referredUserId": "u-shared", "eventType": "signup"},
        {"referralCode": "SECOND22", "referredUserId": "u-second", "eventType": "signin"},
        {"referralCode": "FIRST111", "referredUserId": "u-purchase", "eventType": "purchase"},
    ]

    rows = {row["userId"]: row for row in build_report(referrers, events)["records"]}

    assert rows["u-first"] == {
        "userId": "u-first",
        "referralCount": 1,
        "referredUsers": ["u-shared"],
    }
    assert rows["u-second"] == {
        "userId": "u-second",
        "referralCount": 1,
        "referredUsers": ["u-shared"],
    }
