"""Verifier tests for the normalized meter event feed."""

import hashlib
import json
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path


APP = Path("/app")
RAW_DIR = APP / "raw-events"
OUTPUT = APP / "output" / "normalized-events.jsonl"
EXPECTED_RAW_HASH = "440b7fdb5bb2dd6e5546196a25cf577d2d7fb24fba53c9dd77366c8417ea1e41"
KWH_QUANT = Decimal("0.001")

METERS = {
    "MTR-1001": ("ACC-110", "north", 1.015, "2025-12-01T00:00:00Z", None),
    "MTR-1002": ("ACC-110", "north", 0.982, "2025-12-01T00:00:00Z", None),
    "MTR-2001": ("ACC-220", "central", 1.044, "2026-01-01T00:00:00Z", "2026-03-10T00:00:00Z"),
    "MTR-3001": ("ACC-330", "south", 0.956, "2025-11-15T00:00:00Z", None),
    "MTR-4001": ("ACC-440", "west", 1.128, "2026-02-15T00:00:00Z", None),
    "MTR-5001": ("ACC-550", "east", 1.0, "2026-01-20T00:00:00Z", None),
}
BILLING_WINDOWS = {
    "central": (-6, 1, 4),
    "east": (-5, 3, 5),
    "north": (-5, 2, 6),
    "south": (-6, 1, 7),
    "west": (-8, 1, 8),
}
PEAK_WINDOWS = {
    "central": (4, 6),
    "east": (3, 5),
    "north": (20, 23),
    "south": (22, 24),
    "west": (12, 15),
}
HOLIDAYS = {
    ("central", "2026-02-17"),
    ("north", "2026-02-20"),
    ("west", "2026-03-18"),
}
REGISTER_BASELINES = {
    "MTR-1001": (Decimal("8100.000"), Decimal("10000.000")),
    "MTR-4001": (Decimal("9998.400"), Decimal("10000.000")),
}


def round_kwh(value: float) -> float:
    return float(Decimal(str(value)).quantize(KWH_QUANT, rounding=ROUND_HALF_UP))


def round_kwh_product(kwh: float, multiplier: float) -> float:
    value = Decimal(str(kwh)) * Decimal(str(multiplier))
    return float(value.quantize(KWH_QUANT, rounding=ROUND_HALF_UP))


def register_delta(event: dict, previous_registers: dict[str, Decimal]) -> float:
    previous = previous_registers[event["meter_id"]]
    rollover = REGISTER_BASELINES[event["meter_id"]][1]
    current = Decimal(str(event["register_kwh"]))
    raw_delta = current - previous if current >= previous else current + rollover - previous
    previous_registers[event["meter_id"]] = current
    return float(raw_delta)


def service_month_for(observed_at: str, district: str) -> str:
    offset, cutover_day, cutover_hour = BILLING_WINDOWS[district]
    local = datetime.fromisoformat(observed_at.replace("Z", "+00:00")) + timedelta(hours=offset)
    year = local.year
    month = local.month
    if local.day < cutover_day or (local.day == cutover_day and local.hour < cutover_hour):
        month -= 1
        if month == 0:
            year -= 1
            month = 12
    return f"{year:04d}-{month:02d}"


def billing_band_for(observed_at: str, district: str) -> str:
    offset, _, _ = BILLING_WINDOWS[district]
    local = datetime.fromisoformat(observed_at.replace("Z", "+00:00")) + timedelta(hours=offset)
    local_date = local.date().isoformat()
    start_hour, end_hour = PEAK_WINDOWS[district]
    if local.weekday() >= 5 or (district, local_date) in HOLIDAYS:
        return "standard"
    if start_hour <= local.hour < end_hour:
        return "peak"
    return "standard"


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
        candidate_key = (event["revision"], event["source_priority"], event.get("received_at", ""))
        current_key = None if current is None else (
            current["revision"],
            current["source_priority"],
            current.get("received_at", ""),
        )
        if current is None or candidate_key > current_key:
            chosen[event["event_id"]] = event

    accepted = []
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
        accepted.append((event, meter))

    previous_registers = {meter_id: baseline for meter_id, (baseline, _) in REGISTER_BASELINES.items()}
    rows = []
    for event, meter in sorted(
        accepted,
        key=lambda item: (item[0]["meter_id"], item[0]["observed_at"], item[0]["event_id"]),
    ):
        account_id, district, multiplier, _, _ = meter
        observed_at = event["observed_at"]
        raw_kwh = (
            register_delta(event, previous_registers)
            if event.get("reading_type") == "register"
            else event["kwh"]
        )
        rows.append(
            {
                "event_id": event["event_id"],
                "observed_at": observed_at,
                "account_id": account_id,
                "meter_id": event["meter_id"],
                "service_month": service_month_for(observed_at, district),
                "district": district,
                "adjusted_kwh": round_kwh_product(raw_kwh, multiplier),
                "source_quality": event["quality"],
                "billing_band": billing_band_for(observed_at, district),
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
            "billing_band",
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
            assert isinstance(row["billing_band"], str)

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
        assert by_id["ev-114"]["service_month"] == "2026-02"
        assert by_id["ev-126"]["service_month"] == "2026-02"
        assert by_id["ev-109"]["adjusted_kwh"] == round_kwh_product(2.4, 1.015)
        assert by_id["ev-122"]["adjusted_kwh"] == round_kwh_product(2.1, 0.956)
        assert by_id["ev-125"]["adjusted_kwh"] == round_kwh_product(3.7, 0.982)
        assert by_id["ev-127"]["adjusted_kwh"] == round_kwh_product(12.345, 1.015)
        assert by_id["ev-128"]["adjusted_kwh"] == round_kwh_product(17.755, 1.015)
        assert by_id["ev-129"]["adjusted_kwh"] == round_kwh_product(4.2, 1.128)
        assert by_id["ev-102"]["billing_band"] == "peak"
        assert by_id["ev-108"]["billing_band"] == "standard"
        assert by_id["ev-111"]["billing_band"] == "peak"
        assert by_id["ev-125"]["billing_band"] == "peak"
        assert by_id["ev-127"]["billing_band"] == "standard"
