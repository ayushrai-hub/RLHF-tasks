"""Verifier tests for the monthly settlement outputs."""

import hashlib
import json
import sqlite3
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path


APP = Path("/app")
RAW_DIR = APP / "raw-events"
NORMALIZED = APP / "output" / "normalized-events.jsonl"
SETTLEMENT_DB = APP / "output" / "settlement.db"
SUMMARY = APP / "output" / "settlement-summary.json"
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
RATES = {
    "ACC-110": 18,
    "ACC-220": 22,
    "ACC-330": 16,
    "ACC-440": 24,
    "ACC-550": 19,
}
CREDITS = {
    "central": 3,
    "east": 2,
    "north": 2,
    "south": 1,
    "west": 4,
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


def expected_normalized_rows() -> list[dict]:
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


def expected_account_months() -> list[dict]:
    grouped = defaultdict(lambda: {"event_count": 0, "adjusted_kwh": 0.0})
    for row in expected_normalized_rows():
        key = (row["account_id"], row["service_month"], row["district"])
        grouped[key]["event_count"] += 1
        grouped[key]["adjusted_kwh"] += row["adjusted_kwh"]

    rows = []
    for (account_id, service_month, district), values in grouped.items():
        adjusted_kwh = round_kwh(values["adjusted_kwh"])
        energy = round(adjusted_kwh * RATES[account_id])
        credit = round(adjusted_kwh * CREDITS[district])
        rows.append(
            {
                "account_id": account_id,
                "service_month": service_month,
                "district": district,
                "event_count": values["event_count"],
                "adjusted_kwh": adjusted_kwh,
                "energy_charge_cents": energy,
                "district_credit_cents": credit,
                "total_cents": energy - credit,
            }
        )
    return sorted(rows, key=lambda row: (row["service_month"], row["account_id"], row["district"]))


def expected_summary() -> dict:
    account_months = expected_account_months()
    districts = []
    for district in sorted({row["district"] for row in account_months}):
        rows = [row for row in account_months if row["district"] == district]
        districts.append(
            {
                "district": district,
                "account_month_count": len(rows),
                "total_kwh": round_kwh(sum(row["adjusted_kwh"] for row in rows)),
                "total_cents": sum(row["total_cents"] for row in rows),
            }
        )
    return {
        "generated_from": "/app/output/normalized-events.jsonl",
        "account_month_count": len(account_months),
        "total_kwh": round_kwh(sum(row["adjusted_kwh"] for row in account_months)),
        "total_cents": sum(row["total_cents"] for row in account_months),
        "districts": districts,
    }


class TestMilestone2:
    def test_source_event_files_are_unchanged(self):
        """The raw event fixtures should remain unchanged before settlement totals are computed."""
        assert combined_raw_hash() == EXPECTED_RAW_HASH

    def test_normalized_feed_still_matches_first_milestone(self):
        """The settlement step should preserve the normalized feed contract from the first milestone."""
        assert NORMALIZED.exists(), "normalized feed is missing"
        actual = [json.loads(line) for line in NORMALIZED.read_text().splitlines() if line.strip()]
        assert actual == expected_normalized_rows()

    def test_settlement_database_rows_are_correct(self):
        """The account_months table should contain exact account, month, district, kWh, and cent totals."""
        assert SETTLEMENT_DB.exists(), "settlement database is missing"
        with sqlite3.connect(SETTLEMENT_DB) as conn:
            conn.row_factory = sqlite3.Row
            rows = [
                dict(row)
                for row in conn.execute(
                    """
                    SELECT account_id, service_month, district, event_count, adjusted_kwh,
                           energy_charge_cents, district_credit_cents, total_cents
                    FROM account_months
                    ORDER BY service_month, account_id, district
                    """
                )
            ]
        for row in rows:
            row["adjusted_kwh"] = round(row["adjusted_kwh"], 3)
        assert rows == expected_account_months()

    def test_settlement_database_schema_is_usable(self):
        """The settlement table should expose the required columns with one account-month per key."""
        with sqlite3.connect(SETTLEMENT_DB) as conn:
            columns = [row[1] for row in conn.execute("PRAGMA table_info(account_months)").fetchall()]
            duplicate_count = conn.execute(
                """
                SELECT COUNT(*) FROM (
                  SELECT account_id, service_month, district, COUNT(*) AS n
                  FROM account_months
                  GROUP BY account_id, service_month, district
                  HAVING n > 1
                )
                """
            ).fetchone()[0]
        assert columns == [
            "account_id",
            "service_month",
            "district",
            "event_count",
            "adjusted_kwh",
            "energy_charge_cents",
            "district_credit_cents",
            "total_cents",
        ]
        assert duplicate_count == 0

    def test_summary_json_matches_database_totals(self):
        """The JSON summary should match the same account-month totals and sorted district breakdowns."""
        assert SUMMARY.exists(), "settlement summary is missing"
        actual = json.loads(SUMMARY.read_text())
        assert actual == expected_summary()
