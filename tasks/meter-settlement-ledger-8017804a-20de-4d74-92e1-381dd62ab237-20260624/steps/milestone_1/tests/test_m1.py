"""Verifier tests for the normalized meter event feed."""

import hashlib
import json
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path


APP = Path("/app")
RAW_DIR = APP / "raw-events"
OUTPUT = APP / "output" / "normalized-events.jsonl"
EXPECTED_RAW_HASH = "aef0ec4c2e586fab6920ff1c1354ff0cfc98282ec34128831c5b775af2f81725"
KWH_QUANT = Decimal("0.001")

METERS = {
    "MTR-1001": ("ACC-110", "north", 1.015, "2025-12-01T00:00:00Z", None),
    "MTR-1002": ("ACC-110", "north", 0.982, "2025-12-01T00:00:00Z", None),
    "MTR-2001": ("ACC-220", "central", 1.044, "2026-01-01T00:00:00Z", "2026-03-10T00:00:00Z"),
    "MTR-3001": ("ACC-330", "south", 0.956, "2025-11-15T00:00:00Z", None),
    "MTR-4001": ("ACC-440", "west", 1.128, "2026-02-15T00:00:00Z", None),
    "MTR-5001": ("ACC-550", "east", 1.0, "2026-01-20T00:00:00Z", None),
}


def round_kwh(value: float) -> float:
    return float(Decimal(str(value)).quantize(KWH_QUANT, rounding=ROUND_HALF_UP))


def round_kwh_product(kwh: float, multiplier: float) -> float:
    value = Decimal(str(kwh)) * Decimal(str(multiplier))
    return float(value.quantize(KWH_QUANT, rounding=ROUND_HALF_UP))


def combined_raw_hash() -> str:
    digest = hashlib.sha256()
    for path in sorted(RAW_DIR.glob("*.jsonl")):
        digest.update(path.name.encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def load_events() -> list[dict]:
    events = []
    for path in sorted(RAW_DIR.glob("*.jsonl")):
        for line in path.read_text().splitlines():
            if line.strip():
                events.append(json.loads(line))
    return events


def expected_rows() -> list[dict]:
    chosen = {}
    for event in load_events():
        current = chosen.get(event["event_id"])
        candidate_key = (event["revision"], event["source_priority"])
        current_key = None if current is None else (current["revision"], current["source_priority"])
        if current is None or candidate_key > current_key:
            chosen[event["event_id"]] = event

    rows = []
    for event in chosen.values():
        meter = METERS.get(event["meter_id"])
        if event["quality"] != "valid" or meter is None:
            continue
        account_id, district, multiplier, active_from, active_to = meter
        observed_at = event["observed_at"]
        if observed_at < active_from:
            continue
        if active_to is not None and observed_at >= active_to:
            continue
        rows.append(
            {
                "event_id": event["event_id"],
                "observed_at": observed_at,
                "account_id": account_id,
                "meter_id": event["meter_id"],
                "service_month": observed_at[:7],
                "district": district,
                "adjusted_kwh": round_kwh_product(event["kwh"], multiplier),
                "source_quality": event["quality"],
            }
        )
    return sorted(rows, key=lambda row: (row["service_month"], row["account_id"], row["observed_at"], row["event_id"]))


def actual_rows() -> list[dict]:
    assert OUTPUT.exists(), "normalized event file is missing"
    text = OUTPUT.read_text().strip()
    assert text, "normalized event file is empty"
    return [json.loads(line) for line in text.splitlines()]


class TestMilestone1:
    def test_source_event_files_are_unchanged(self):
        """The raw event fixtures should remain unchanged during processing."""
        assert combined_raw_hash() == EXPECTED_RAW_HASH

    def test_normalized_feed_matches_catalog_rules(self):
        """The normalized feed should match the catalog join, filter, duplicate, and multiplier rules."""
        assert actual_rows() == expected_rows()

    def test_normalized_schema_is_exact(self):
        """Each normalized row should use the required field names and JSON value types."""
        required_keys = {
            "event_id",
            "observed_at",
            "account_id",
            "meter_id",
            "service_month",
            "district",
            "adjusted_kwh",
            "source_quality",
        }
        for row in actual_rows():
            assert set(row) == required_keys
            assert isinstance(row["event_id"], str)
            assert isinstance(row["observed_at"], str)
            assert isinstance(row["account_id"], str)
            assert isinstance(row["meter_id"], str)
            assert isinstance(row["service_month"], str)
            assert isinstance(row["district"], str)
            assert isinstance(row["adjusted_kwh"], (int, float))
            assert isinstance(row["source_quality"], str)

    def test_filtered_and_duplicate_events_do_not_leak(self):
        """Rejected, inactive, unknown, and superseded duplicate events should not appear."""
        rows = actual_rows()
        ids = [row["event_id"] for row in rows]
        assert len(ids) == len(set(ids))
        assert "ev-103" not in ids
        assert "ev-106" not in ids
        assert "ev-112" not in ids
        assert "ev-116" not in ids
        assert "ev-120" not in ids
        by_id = {row["event_id"]: row for row in rows}
        assert by_id["ev-109"]["adjusted_kwh"] == round_kwh_product(2.4, 1.015)
        assert by_id["ev-122"]["adjusted_kwh"] == round_kwh_product(2.1, 0.956)
