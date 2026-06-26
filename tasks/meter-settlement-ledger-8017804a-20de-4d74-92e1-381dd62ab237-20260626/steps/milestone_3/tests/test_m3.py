"""Verifier tests for the settlement reconciliation report."""

import csv
import json
import sqlite3
from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path


APP = Path("/app")
RAW_DIR = APP / "raw-events"
PRIOR_LEDGER = APP / "prior-ledger" / "prior-account-months.csv"
SETTLEMENT_DB = APP / "output" / "settlement.db"
SUMMARY = APP / "output" / "settlement-summary.json"
REPORT = APP / "output" / "reconciliation-report.json"
KWH_QUANT = Decimal("0.001")
CENT_QUANT = Decimal("1")

METERS = {
    "MTR-1001": ("ACC-110", "north", 1.015, "2025-12-01T00:00:00Z", None),
    "MTR-1002": ("ACC-110", "north", 0.982, "2025-12-01T00:00:00Z", None),
    "MTR-2001": ("ACC-220", "central", 1.044, "2026-01-01T00:00:00Z", "2026-03-10T00:00:00Z"),
    "MTR-3001": ("ACC-330", "south", 0.956, "2025-11-15T00:00:00Z", None),
    "MTR-4001": ("ACC-440", "west", 1.128, "2026-02-15T00:00:00Z", None),
    "MTR-5001": ("ACC-550", "east", 1.0, "2026-01-20T00:00:00Z", None),
}
RATE_SCHEDULE = {
    "ACC-110": [("2026-01", 18), ("2026-03", 21)],
    "ACC-220": [("2026-01", 22)],
    "ACC-330": [("2026-01", 16), ("2026-03", 17)],
    "ACC-440": [("2026-01", 24)],
    "ACC-550": [("2026-01", 19), ("2026-03", 20)],
}
CREDITS = {
    "central": 3,
    "east": 2,
    "north": 2,
    "south": 1,
    "west": 4,
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
RATE_ADJUSTMENTS = {
    ("central", "standard"): 0,
    ("central", "peak"): 5,
    ("east", "standard"): 0,
    ("east", "peak"): 4,
    ("north", "standard"): 0,
    ("north", "peak"): 6,
    ("south", "standard"): 0,
    ("south", "peak"): 3,
    ("west", "standard"): 0,
    ("west", "peak"): 7,
}
REGISTER_BASELINES = {
    "MTR-1001": (Decimal("8100.000"), Decimal("10000.000")),
    "MTR-4001": (Decimal("9998.400"), Decimal("10000.000")),
}
ADJUSTMENTS = {
    ("ACC-220", "2026-02", "central"): (-5, "late-meter-dispute"),
    ("ACC-440", "2026-03", "west"): (12, "distribution-true-up"),
    ("ACC-550", "2026-03", "east"): (-4, "manual-credit-review"),
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


def round_cent(adjusted_kwh: float, cents_per_kwh: int) -> int:
    value = Decimal(str(adjusted_kwh)) * Decimal(str(cents_per_kwh))
    return int(value.quantize(CENT_QUANT, rounding=ROUND_HALF_UP))


def round_cent_amount(value: Decimal) -> int:
    return int(value.quantize(CENT_QUANT, rounding=ROUND_HALF_UP))


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


def rate_for(account_id: str, service_month: str) -> int:
    matches = [rate for effective_month, rate in RATE_SCHEDULE[account_id] if effective_month <= service_month]
    assert matches, f"missing rate for {account_id} {service_month}"
    return matches[-1]


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


def expected_account_months() -> list[dict]:
    grouped = defaultdict(lambda: {"event_count": 0, "adjusted_kwh": Decimal("0"), "energy_charge": Decimal("0")})
    for row in expected_normalized_rows():
        key = (row["account_id"], row["service_month"], row["district"])
        adjusted_kwh = Decimal(str(row["adjusted_kwh"]))
        effective_rate = Decimal(str(rate_for(row["account_id"], row["service_month"])))
        effective_rate += Decimal(str(RATE_ADJUSTMENTS[(row["district"], row["billing_band"])]))
        grouped[key]["event_count"] += 1
        grouped[key]["adjusted_kwh"] += adjusted_kwh
        grouped[key]["energy_charge"] += adjusted_kwh * effective_rate

    rows = []
    for (account_id, service_month, district), values in grouped.items():
        adjusted_kwh = round_kwh(values["adjusted_kwh"])
        energy = round_cent_amount(values["energy_charge"])
        credit = round_cent(adjusted_kwh, CREDITS[district])
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


def load_prior_rows() -> dict[tuple[str, str, str], dict]:
    with PRIOR_LEDGER.open(newline="") as handle:
        return {
            (row["account_id"], row["service_month"], row["district"]): {
                "prior_total_cents": int(row["prior_total_cents"]),
                "prior_kwh": round_kwh(row["prior_adjusted_kwh"]),
            }
            for row in csv.DictReader(handle)
        }


def expected_report() -> dict:
    settlement = {
        (row["account_id"], row["service_month"], row["district"]): row
        for row in expected_account_months()
    }
    prior = load_prior_rows()
    rows = []
    for key in sorted(set(settlement) | set(prior), key=lambda item: (item[1], item[0], item[2])):
        account_id, service_month, district = key
        current = settlement.get(key)
        previous = prior.get(key)
        adjustment_cents, adjustment_reason = ADJUSTMENTS.get(key, (0, None))
        current_total = None if current is None else current["total_cents"]
        previous_total = None if previous is None else previous["prior_total_cents"]
        current_kwh = None if current is None else round_kwh(current["adjusted_kwh"])
        previous_kwh = None if previous is None else previous["prior_kwh"]
        if previous is None:
            status = "new"
        elif current is None:
            status = "missing_from_settlement"
        elif current_total == previous_total and current_kwh == previous_kwh:
            status = "unchanged"
        else:
            status = "changed"

        rows.append(
            {
                "account_id": account_id,
                "service_month": service_month,
                "district": district,
                "status": status,
                "settlement_total_cents": current_total,
                "prior_total_cents": previous_total,
                "delta_cents": (current_total or 0) - (previous_total or 0),
                "settlement_kwh": current_kwh,
                "prior_kwh": previous_kwh,
                "delta_kwh": round_kwh((current_kwh or 0) - (previous_kwh or 0)),
                "adjustment_cents": adjustment_cents,
                "adjustment_reason": adjustment_reason,
                "final_total_cents": None if current_total is None else current_total + adjustment_cents,
            }
        )

    status_counts = {"changed": 0, "missing_from_settlement": 0, "new": 0, "unchanged": 0}
    for row in rows:
        status_counts[row["status"]] += 1

    return {
        "generated_from": ["/app/output/settlement.db", "/app/prior-ledger/prior-account-months.csv"],
        "row_count": len(rows),
        "status_counts": status_counts,
        "net_delta_cents": sum(row["delta_cents"] for row in rows),
        "net_adjustment_cents": sum(row["adjustment_cents"] for row in rows),
        "final_total_cents": sum(row["final_total_cents"] or 0 for row in rows),
        "rows": rows,
    }


class TestMilestone3:
    def test_settlement_outputs_are_preserved(self):
        """The reconciliation step should keep the milestone 2 database and summary contract intact."""
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
        assert json.loads(SUMMARY.read_text()) == expected_summary()

    def test_reconciliation_report_matches_prior_ledger_union(self):
        """The report should classify all current and prior account-month keys and apply adjustments."""
        assert REPORT.exists(), "reconciliation report is missing"
        assert json.loads(REPORT.read_text()) == expected_report()

    def test_reconciliation_report_exercises_all_statuses(self):
        """The fixture should force changed, unchanged, new, and missing statuses."""
        rows = json.loads(REPORT.read_text())["rows"]
        statuses = {row["status"] for row in rows}
        assert statuses == {"changed", "missing_from_settlement", "new", "unchanged"}
        by_key = {(row["account_id"], row["service_month"], row["district"]): row for row in rows}
        assert by_key[("ACC-550", "2026-03", "east")]["status"] == "new"
        assert by_key[("ACC-660", "2026-03", "north")]["status"] == "missing_from_settlement"
        assert by_key[("ACC-220", "2026-02", "central")]["adjustment_cents"] == -5
