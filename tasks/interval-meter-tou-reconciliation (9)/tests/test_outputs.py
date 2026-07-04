"""Verifier for interval-meter TOU reconciliation report."""

from __future__ import annotations

import csv
import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

APP = Path("/app")
ENV = APP / "environment"
BIN = APP / "bin" / "tou_reconcile"
REPORT = APP / "output" / "reconciliation_report.json"
RUN_CONFIG = ENV / "config" / "run.json"
TIMEZONE = "America/Chicago"


@dataclass(frozen=True)
class TierWindows:
    off_peak: list[tuple[int, int]]
    mid_peak: list[tuple[int, int]]
    on_peak: list[tuple[int, int]]


@dataclass(frozen=True)
class TariffRules:
    timezone: str
    register_max_kwh: float
    interval_minutes: int
    summer_start: int
    summer_end: int
    summer: TierWindows
    winter: TierWindows


def _parse_clock(clock: str) -> int:
    hour, minute = clock.split(":")
    return int(hour) * 60 + int(minute)


def _parse_mmdd(mmdd: str) -> int:
    month, day = mmdd.split("-")
    return int(month) * 100 + int(day)


def _windows(raw: dict[str, list[list[str]]]) -> TierWindows:
    return TierWindows(
        off_peak=[(_parse_clock(a), _parse_clock(b)) for a, b in raw["off_peak"]],
        mid_peak=[(_parse_clock(a), _parse_clock(b)) for a, b in raw["mid_peak"]],
        on_peak=[(_parse_clock(a), _parse_clock(b)) for a, b in raw["on_peak"]],
    )


def load_tariff(run_config: Path) -> TariffRules:
    run = json.loads(run_config.read_text(encoding="utf-8"))
    tariff_path = Path(run["tariff_path"])
    data = json.loads(tariff_path.read_text(encoding="utf-8"))
    summer = data["seasons"]["summer"]
    return TariffRules(
        timezone=data["timezone"],
        register_max_kwh=float(data["register_max_kwh"]),
        interval_minutes=int(data["interval_minutes"]),
        summer_start=_parse_mmdd(summer["start_mmdd"]),
        summer_end=_parse_mmdd(summer["end_mmdd"]),
        summer=_windows(data["windows"]["summer"]),
        winter=_windows(data["windows"]["winter"]),
    )


def _clock_minutes(dt: datetime) -> int:
    return dt.hour * 60 + dt.minute


def _is_summer(dt: datetime, tariff: TariffRules) -> bool:
    mmdd = dt.month * 100 + dt.day
    if tariff.summer_start <= tariff.summer_end:
        return tariff.summer_start <= mmdd <= tariff.summer_end
    return mmdd >= tariff.summer_start or mmdd <= tariff.summer_end


def _in_window(minute: int, start: int, end: int) -> bool:
    if start < end:
        return start <= minute < end
    return minute >= start or minute < end


def _tier_for(dt: datetime, tariff: TariffRules) -> str:
    windows = tariff.summer if _is_summer(dt, tariff) else tariff.winter
    minute = _clock_minutes(dt)
    for start, end in windows.off_peak:
        if _in_window(minute, start, end):
            return "off_peak"
    for start, end in windows.mid_peak:
        if _in_window(minute, start, end):
            return "mid_peak"
    for start, end in windows.on_peak:
        if _in_window(minute, start, end):
            return "on_peak"
    return "off_peak"


def _load_rows(csv_path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with csv_path.open(newline="", encoding="utf-8") as fp:
        for row in csv.DictReader(fp):
            quality = (row.get("quality") or row.get("quality_code") or "actual").strip().lower()
            if quality == "":
                quality = "actual"
            if quality == "estimated":
                quality = "estimate"
            if quality == "void":
                continue
            rows.append(
                {
                    "meter_id": row["meter_id"],
                    "timestamp": datetime.fromisoformat(row["timestamp"]),
                    "register_kwh": float(row["register_kwh"]),
                    "quality": quality,
                }
            )
    return rows


def _slot_count(prev: datetime, curr: datetime, tariff: TariffRules) -> int:
    elapsed = (curr - prev).total_seconds() / 60.0
    return max(1, int(elapsed // tariff.interval_minutes))


def compute_meter_stats(rows: list[dict[str, Any]], tariff: TariffRules) -> dict[str, Any]:
    stats = {
        "interval_count": 0,
        "total_kwh": 0.0,
        "tier_kwh": {"off_peak": 0.0, "mid_peak": 0.0, "on_peak": 0.0},
        "demand_peak_kw": 0.0,
        "rollover_events": 0,
        "gap_intervals": 0,
        "register_delta_kwh": 0.0,
    }
    if not rows:
        stats["reconciled"] = True
        return stats

    demand_peak = 0.0
    have_baseline = False
    prev: dict[str, Any] | None = None
    used_estimate = False

    for row in rows:
        quality = row.get("quality", "actual")
        if quality == "reset":
            have_baseline = True
            prev = row
            continue
        if not have_baseline:
            have_baseline = True
            prev = row
            if quality == "estimate":
                used_estimate = True
            continue
        assert prev is not None
        delta = row["register_kwh"] - prev["register_kwh"]
        if delta < 0:
            stats["rollover_events"] += 1
            delta = (tariff.register_max_kwh - prev["register_kwh"]) + row["register_kwh"]

        slots = _slot_count(prev["timestamp"], row["timestamp"], tariff)
        stats["gap_intervals"] += max(0, slots - 1)

        stats["interval_count"] += 1
        stats["total_kwh"] += delta
        stats["register_delta_kwh"] += delta
        per_slot = delta / slots
        for slot_idx in range(slots):
            slot_start = prev["timestamp"] + timedelta(minutes=tariff.interval_minutes * slot_idx)
            tier = _tier_for(slot_start, tariff)
            stats["tier_kwh"][tier] += per_slot
            demand_peak = max(demand_peak, per_slot * 60.0 / tariff.interval_minutes)

        if quality == "estimate" or prev.get("quality") == "estimate":
            used_estimate = True
        prev = row

    stats["demand_peak_kw"] = demand_peak
    stats["reconciled"] = (not used_estimate) and abs(stats["total_kwh"] - stats["register_delta_kwh"]) < 0.001
    return stats


def expected_report(config_path: Path = RUN_CONFIG) -> dict[str, Any]:
    run = json.loads(config_path.read_text(encoding="utf-8"))
    tariff = load_tariff(config_path)
    fixture_sets: list[dict[str, Any]] = []
    all_reconciled = True
    for fx in run["fixture_sets"]:
        csv_path = Path(fx["csv"])
        rows = _load_rows(csv_path)
        by_meter: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            by_meter.setdefault(row["meter_id"], []).append(row)
        meters: dict[str, Any] = {}
        for meter_id, meter_rows in sorted(by_meter.items()):
            meter_rows.sort(key=lambda r: r["timestamp"])
            meters[meter_id] = compute_meter_stats(meter_rows, tariff)
            if not meters[meter_id]["reconciled"]:
                all_reconciled = False
        fixture_sets.append({"name": fx["name"], "meters": meters})
    return {
        "timezone": tariff.timezone,
        "all_reconciled": all_reconciled,
        "fixture_sets": fixture_sets,
    }


def run_checked(cmd: list[str], *, timeout: int = 180) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout, check=False)
    if result.returncode != 0:
        raise AssertionError(
            f"command failed: {' '.join(cmd)}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result


@pytest.fixture(scope="module")
def built_binary() -> Path:
    run_checked(["make", "-C", str(ENV)])
    assert BIN.is_file(), "tou_reconcile binary missing"
    return BIN


def run_report(config_path: Path, out_path: Path) -> dict[str, Any]:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    run_checked(
        [
            str(BIN),
            "--config",
            str(config_path),
            "--out",
            str(out_path),
        ]
    )
    return json.loads(out_path.read_text(encoding="utf-8"))


def rebuild_and_run() -> dict[str, Any]:
    return run_report(RUN_CONFIG, REPORT)


def _fixture_map(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {fx["name"]: fx["meters"] for fx in report["fixture_sets"]}


@pytest.fixture(scope="module")
def report(built_binary: Path) -> dict[str, Any]:
    return rebuild_and_run()


@pytest.fixture(scope="module")
def expected() -> dict[str, Any]:
    return expected_report()


FIXTURE_NAMES = [
    "uniform_summer",
    "tier_boundaries",
    "winter_weekday",
    "season_boundary",
    "overnight_span",
    "rollover",
    "gap",
    "month_boundary_gap",
    "year_boundary_gap",
    "summer_edges",
    "multi_meter",
    "offset_ordering",
    "json_key_escape",
    "long_meter_ids",
    "mixed_offsets",
]


@pytest.mark.parametrize("fixture_name", FIXTURE_NAMES)
def test_fixture_present(report: dict[str, Any], fixture_name: str) -> None:
    """Each configured fixture set appears in the report output."""
    names = {fx["name"] for fx in report["fixture_sets"]}
    assert fixture_name in names


@pytest.mark.parametrize("fixture_name", FIXTURE_NAMES)
def test_fixture_meter_keys(report: dict[str, Any], expected: dict[str, Any], fixture_name: str) -> None:
    """Meter ids in a fixture match the reference grouping."""
    got = _fixture_map(report)[fixture_name]
    want = _fixture_map(expected)[fixture_name]
    assert set(got) == set(want)


@pytest.mark.parametrize(
    ("fixture_name", "meter_id"),
    [
        ("uniform_summer", "MTR-1"),
        ("tier_boundaries", "EDGE-1"),
        ("winter_weekday", "WIN-1"),
        ("season_boundary", "SEA-1"),
        ("overnight_span", "NIGHT-1"),
        ("rollover", "ROLL-1"),
        ("gap", "GAP-1"),
        ("month_boundary_gap", "MON-G"),
        ("year_boundary_gap", "YR-G"),
        ("summer_edges", "SUM-1"),
        ("multi_meter", "M-A"),
        ("multi_meter", "M-B"),
        ("offset_ordering", "DST-FOLD"),
        ("json_key_escape", 'MTR "North"\\A'),
        ("long_meter_ids", "PLANT-ALPHA-FEEDER-0000000000001-A"),
        ("long_meter_ids", "PLANT-ALPHA-FEEDER-0000000000001-B"),
        ("mixed_offsets", "OFFSET-TIER"),
    ],
)
def test_interval_counts(
    report: dict[str, Any], expected: dict[str, Any], fixture_name: str, meter_id: str
) -> None:
    """Interval counts equal the number of register deltas computed for each meter."""
    got = _fixture_map(report)[fixture_name][meter_id]["interval_count"]
    want = _fixture_map(expected)[fixture_name][meter_id]["interval_count"]
    assert got == want


@pytest.mark.parametrize(
    ("fixture_name", "meter_id"),
    [
        ("uniform_summer", "MTR-1"),
        ("tier_boundaries", "EDGE-1"),
        ("winter_weekday", "WIN-1"),
        ("season_boundary", "SEA-1"),
        ("overnight_span", "NIGHT-1"),
        ("rollover", "ROLL-1"),
        ("gap", "GAP-1"),
        ("month_boundary_gap", "MON-G"),
        ("year_boundary_gap", "YR-G"),
        ("summer_edges", "SUM-1"),
        ("multi_meter", "M-A"),
        ("multi_meter", "M-B"),
        ("offset_ordering", "DST-FOLD"),
        ("json_key_escape", 'MTR "North"\\A'),
        ("long_meter_ids", "PLANT-ALPHA-FEEDER-0000000000001-A"),
        ("long_meter_ids", "PLANT-ALPHA-FEEDER-0000000000001-B"),
        ("mixed_offsets", "OFFSET-TIER"),
    ],
)
def test_total_kwh(
    report: dict[str, Any], expected: dict[str, Any], fixture_name: str, meter_id: str
) -> None:
    """Total kWh matches summed interval deltas including rollover handling."""
    got = _fixture_map(report)[fixture_name][meter_id]["total_kwh"]
    want = _fixture_map(expected)[fixture_name][meter_id]["total_kwh"]
    assert abs(got - want) < 0.001


@pytest.mark.parametrize(
    ("fixture_name", "meter_id", "tier"),
    [
        ("uniform_summer", "MTR-1", "off_peak"),
        ("uniform_summer", "MTR-1", "mid_peak"),
        ("uniform_summer", "MTR-1", "on_peak"),
        ("winter_weekday", "WIN-1", "on_peak"),
        ("winter_weekday", "WIN-1", "mid_peak"),
        ("tier_boundaries", "EDGE-1", "off_peak"),
        ("tier_boundaries", "EDGE-1", "on_peak"),
        ("multi_meter", "M-A", "on_peak"),
        ("multi_meter", "M-B", "on_peak"),
        ("offset_ordering", "DST-FOLD", "off_peak"),
        ("json_key_escape", 'MTR "North"\\A', "on_peak"),
        ("long_meter_ids", "PLANT-ALPHA-FEEDER-0000000000001-A", "mid_peak"),
        ("long_meter_ids", "PLANT-ALPHA-FEEDER-0000000000001-A", "on_peak"),
        ("mixed_offsets", "OFFSET-TIER", "on_peak"),
        ("mixed_offsets", "OFFSET-TIER", "mid_peak"),
    ],
)
def test_tier_kwh(
    report: dict[str, Any],
    expected: dict[str, Any],
    fixture_name: str,
    meter_id: str,
    tier: str,
) -> None:
    """TOU tier buckets match schedule assignment from local interval start times."""
    got = _fixture_map(report)[fixture_name][meter_id]["tier_kwh"][tier]
    want = _fixture_map(expected)[fixture_name][meter_id]["tier_kwh"][tier]
    assert abs(got - want) < 0.001


@pytest.mark.parametrize(
    ("fixture_name", "meter_id"),
    [
        ("uniform_summer", "MTR-1"),
        ("winter_weekday", "WIN-1"),
        ("rollover", "ROLL-1"),
        ("gap", "GAP-1"),
        ("month_boundary_gap", "MON-G"),
        ("year_boundary_gap", "YR-G"),
        ("summer_edges", "SUM-1"),
        ("multi_meter", "M-A"),
        ("offset_ordering", "DST-FOLD"),
        ("json_key_escape", 'MTR "North"\\A'),
        ("long_meter_ids", "PLANT-ALPHA-FEEDER-0000000000001-A"),
        ("mixed_offsets", "OFFSET-TIER"),
    ],
)
def test_demand_peak_kw(
    report: dict[str, Any], expected: dict[str, Any], fixture_name: str, meter_id: str
) -> None:
    """Demand peak uses the maximum interval kW extrapolation, not an average."""
    got = _fixture_map(report)[fixture_name][meter_id]["demand_peak_kw"]
    want = _fixture_map(expected)[fixture_name][meter_id]["demand_peak_kw"]
    assert abs(got - want) < 0.001


@pytest.mark.parametrize(
    ("fixture_name", "meter_id", "want_rollovers"),
    [
        ("rollover", "ROLL-1", 1),
        ("uniform_summer", "MTR-1", 0),
        ("gap", "GAP-1", 0),
        ("offset_ordering", "DST-FOLD", 0),
        ("long_meter_ids", "PLANT-ALPHA-FEEDER-0000000000001-B", 0),
    ],
)
def test_rollover_events(
    report: dict[str, Any],
    fixture_name: str,
    meter_id: str,
    want_rollovers: int,
) -> None:
    """Rollover counters increment when registers decrease."""
    got = _fixture_map(report)[fixture_name][meter_id]["rollover_events"]
    assert got == want_rollovers


@pytest.mark.parametrize(
    ("fixture_name", "meter_id", "want_gaps"),
    [
        ("gap", "GAP-1", 2),
        ("month_boundary_gap", "MON-G", 1),
        ("year_boundary_gap", "YR-G", 1),
        ("uniform_summer", "MTR-1", 0),
        ("rollover", "ROLL-1", 0),
        ("offset_ordering", "DST-FOLD", 58),
        ("mixed_offsets", "OFFSET-TIER", 22),
    ],
)
def test_gap_intervals(
    report: dict[str, Any], fixture_name: str, meter_id: str, want_gaps: int
) -> None:
    """Missing timestamp slots contribute gap_intervals based on elapsed minutes."""
    got = _fixture_map(report)[fixture_name][meter_id]["gap_intervals"]
    assert got == want_gaps


@pytest.mark.parametrize(
    ("fixture_name", "meter_id"),
    [
        ("uniform_summer", "MTR-1"),
        ("rollover", "ROLL-1"),
        ("gap", "GAP-1"),
        ("multi_meter", "M-B"),
        ("offset_ordering", "DST-FOLD"),
        ("json_key_escape", 'MTR "North"\\A'),
        ("long_meter_ids", "PLANT-ALPHA-FEEDER-0000000000001-A"),
        ("long_meter_ids", "PLANT-ALPHA-FEEDER-0000000000001-B"),
    ],
)
def test_register_delta_matches_total(
    report: dict[str, Any], fixture_name: str, meter_id: str
) -> None:
    """register_delta_kwh tracks the summed interval energy for each meter."""
    meter = _fixture_map(report)[fixture_name][meter_id]
    assert abs(meter["register_delta_kwh"] - meter["total_kwh"]) < 0.001


@pytest.mark.parametrize(
    ("fixture_name", "meter_id", "want_reconciled"),
    [
        ("uniform_summer", "MTR-1", True),
        ("rollover", "ROLL-1", True),
        ("gap", "GAP-1", True),
        ("multi_meter", "M-A", True),
        ("offset_ordering", "DST-FOLD", True),
        ("json_key_escape", 'MTR "North"\\A', True),
        ("long_meter_ids", "PLANT-ALPHA-FEEDER-0000000000001-A", True),
    ],
)
def test_meter_reconciled_flag(
    report: dict[str, Any], fixture_name: str, meter_id: str, want_reconciled: bool
) -> None:
    """Per-meter reconciled flag is true when totals agree within 0.001 kWh."""
    got = _fixture_map(report)[fixture_name][meter_id]["reconciled"]
    assert got is want_reconciled


def test_reconciled_flag_tracks_total_agreement(report: dict[str, Any]) -> None:
    """reconciled is false whenever total_kwh and register_delta_kwh diverge beyond 0.001 kWh."""
    for fx in report["fixture_sets"]:
        for meter in fx["meters"].values():
            want = abs(meter["total_kwh"] - meter["register_delta_kwh"]) < 0.001
            assert meter["reconciled"] is want


def test_top_level_timezone(report: dict[str, Any]) -> None:
    """Report timezone string mirrors the tariff config label."""
    assert report["timezone"] == TIMEZONE


def test_all_reconciled_true(report: dict[str, Any]) -> None:
    """All meters reconcile for the bundled fixture sets."""
    assert report["all_reconciled"] is True


def test_tier_keys_present(report: dict[str, Any]) -> None:
    """Each meter includes off_peak, mid_peak, and on_peak tier buckets."""
    for fx in report["fixture_sets"]:
        for meter in fx["meters"].values():
            tiers = meter["tier_kwh"]
            assert set(tiers) == {"off_peak", "mid_peak", "on_peak"}


def test_uniform_summer_tier_split(report: dict[str, Any], expected: dict[str, Any]) -> None:
    """Uniform summer day splits 24 kWh across tiers per Chicago summer windows."""
    got = _fixture_map(report)["uniform_summer"]["MTR-1"]["tier_kwh"]
    want = _fixture_map(expected)["uniform_summer"]["MTR-1"]["tier_kwh"]
    assert abs(sum(got.values()) - 24.0) < 0.01
    for tier in ("off_peak", "mid_peak", "on_peak"):
        assert abs(got[tier] - want[tier]) < 0.001


def test_tier_boundary_exclusive(report: dict[str, Any], expected: dict[str, Any]) -> None:
    """Intervals starting exactly on tier boundaries land in the end-exclusive window."""
    got = _fixture_map(report)["tier_boundaries"]["EDGE-1"]["tier_kwh"]
    want = _fixture_map(expected)["tier_boundaries"]["EDGE-1"]["tier_kwh"]
    assert got == pytest.approx(want, abs=0.001)


def test_season_boundary_winter_to_summer(report: dict[str, Any], expected: dict[str, Any]) -> None:
    """Season boundary fixture applies winter vs summer windows on May 31 and June 1 rows."""
    got = _fixture_map(report)["season_boundary"]["SEA-1"]["tier_kwh"]
    want = _fixture_map(expected)["season_boundary"]["SEA-1"]["tier_kwh"]
    assert abs(sum(got.values()) - sum(want.values())) < 0.001
    assert abs(got["on_peak"] - want["on_peak"]) < 0.001


def test_overnight_off_peak_span(report: dict[str, Any], expected: dict[str, Any]) -> None:
    """Overnight span assigns late evening and early morning intervals to off_peak."""
    got = _fixture_map(report)["overnight_span"]["NIGHT-1"]["tier_kwh"]["off_peak"]
    want = _fixture_map(expected)["overnight_span"]["NIGHT-1"]["tier_kwh"]["off_peak"]
    assert abs(got - want) < 0.001
    assert got > 0.0


def test_rollover_energy_conservation(report: dict[str, Any], expected: dict[str, Any]) -> None:
    """Rollover fixture totals match reference rollover-aware deltas."""
    got = _fixture_map(report)["rollover"]["ROLL-1"]["total_kwh"]
    want = _fixture_map(expected)["rollover"]["ROLL-1"]["total_kwh"]
    assert abs(got - want) < 0.001


def test_multi_meter_isolation(report: dict[str, Any], expected: dict[str, Any]) -> None:
    """Distinct meters in one CSV stay isolated with separate totals."""
    got = _fixture_map(report)["multi_meter"]
    want = _fixture_map(expected)["multi_meter"]
    assert set(got) == {"M-A", "M-B"}
    assert abs(got["M-A"]["total_kwh"] - want["M-A"]["total_kwh"]) < 0.001
    assert abs(got["M-B"]["total_kwh"] - want["M-B"]["total_kwh"]) < 0.001
    assert abs(got["M-A"]["total_kwh"] - got["M-B"]["total_kwh"]) > 0.001


def test_year_boundary_gap_count(report: dict[str, Any], expected: dict[str, Any]) -> None:
    """Gaps spanning a year boundary use full elapsed minutes."""
    got = _fixture_map(report)["year_boundary_gap"]["YR-G"]["gap_intervals"]
    want = _fixture_map(expected)["year_boundary_gap"]["YR-G"]["gap_intervals"]
    assert got == want
    assert got == 1


def test_summer_edge_inclusive_season(report: dict[str, Any], expected: dict[str, Any]) -> None:
    """June 1 and September 30 dates use summer windows when locally inclusive."""
    got = _fixture_map(report)["summer_edges"]["SUM-1"]["tier_kwh"]
    want = _fixture_map(expected)["summer_edges"]["SUM-1"]["tier_kwh"]
    assert abs(got["on_peak"] - want["on_peak"]) < 0.001
    assert abs(got["mid_peak"] - want["mid_peak"]) < 0.001


def test_month_boundary_gap_count(report: dict[str, Any], expected: dict[str, Any]) -> None:
    """Gaps spanning a month boundary use full elapsed minutes, not day-of-month arithmetic."""
    got = _fixture_map(report)["month_boundary_gap"]["MON-G"]["gap_intervals"]
    want = _fixture_map(expected)["month_boundary_gap"]["MON-G"]["gap_intervals"]
    assert got == want
    assert got == 1


def test_summer_edges_reconciled(report: dict[str, Any]) -> None:
    """Summer edge fixture stays reconciled when rollover and register deltas align."""
    meter = _fixture_map(report)["summer_edges"]["SUM-1"]
    assert meter["reconciled"] is True
    assert abs(meter["total_kwh"] - meter["register_delta_kwh"]) < 0.001


def test_offset_ordering_uses_absolute_time(report: dict[str, Any], expected: dict[str, Any]) -> None:
    """DST fold rows are ordered by absolute time, not lexicographic local timestamp text."""
    got = _fixture_map(report)["offset_ordering"]["DST-FOLD"]
    want = _fixture_map(expected)["offset_ordering"]["DST-FOLD"]
    assert got["rollover_events"] == 0
    assert got["gap_intervals"] == want["gap_intervals"] == 58
    assert abs(got["total_kwh"] - want["total_kwh"]) < 0.001
    assert abs(got["demand_peak_kw"] - want["demand_peak_kw"]) < 0.001


def test_json_special_meter_id_is_preserved(report: dict[str, Any], expected: dict[str, Any]) -> None:
    """Meter ids containing quotes and backslashes are preserved as JSON object keys."""
    meter_id = 'MTR "North"\\A'
    got = _fixture_map(report)["json_key_escape"]
    assert set(got) == {meter_id}
    assert abs(got[meter_id]["total_kwh"] - _fixture_map(expected)["json_key_escape"][meter_id]["total_kwh"]) < 0.001


def test_long_meter_ids_do_not_collide(report: dict[str, Any], expected: dict[str, Any]) -> None:
    """Long meter ids with a shared prefix remain distinct and untruncated."""
    got = _fixture_map(report)["long_meter_ids"]
    want = _fixture_map(expected)["long_meter_ids"]
    assert set(got) == set(want)
    assert len(got) == 2
    for meter_id in want:
        assert meter_id in got
        assert abs(got[meter_id]["total_kwh"] - want[meter_id]["total_kwh"]) < 0.001


def test_mixed_offset_tiers_use_written_local_clock(report: dict[str, Any], expected: dict[str, Any]) -> None:
    """TOU assignment uses the local clock in the timestamp while gaps use offset-aware elapsed minutes."""
    got = _fixture_map(report)["mixed_offsets"]["OFFSET-TIER"]
    want = _fixture_map(expected)["mixed_offsets"]["OFFSET-TIER"]
    assert abs(got["tier_kwh"]["on_peak"] - want["tier_kwh"]["on_peak"]) < 0.001
    assert abs(got["tier_kwh"]["mid_peak"] - want["tier_kwh"]["mid_peak"]) < 0.001
    assert got["gap_intervals"] == want["gap_intervals"] == 22


def _write_custom_tariff(path: Path, *, interval_minutes: int = 30) -> None:
    path.write_text(
        json.dumps(
            {
                "timezone": "Verifier/Alt-Tariff",
                "register_max_kwh": 999.9,
                "interval_minutes": interval_minutes,
                "demand_window_intervals": 2,
                "seasons": {
                    "summer": {"start_mmdd": "04-15", "end_mmdd": "10-15"},
                    "winter": {"start_mmdd": "10-16", "end_mmdd": "04-14"},
                },
                "windows": {
                    "summer": {
                        "off_peak": [["23:00", "03:00"]],
                        "mid_peak": [["03:00", "10:00"], ["18:00", "23:00"]],
                        "on_peak": [["10:00", "18:00"]],
                    },
                    "winter": {
                        "off_peak": [["21:30", "05:30"]],
                        "mid_peak": [["05:30", "09:30"], ["17:30", "21:30"]],
                        "on_peak": [["09:30", "17:30"]],
                    },
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def _write_run_config(path: Path, tariff: Path, fixtures: list[tuple[str, Path]]) -> None:
    path.write_text(
        json.dumps(
            {
                "tariff_path": str(tariff),
                "fixture_sets": [{"name": name, "csv": str(csv_path)} for name, csv_path in fixtures],
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def _run_dynamic_case(config_path: Path, out_path: Path, built_binary: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    assert built_binary.is_file()
    got = run_report(config_path, out_path)
    want = expected_report(config_path)
    return got, want


def test_dynamic_tariff_windows_and_interval_minutes(tmp_path: Path, built_binary: Path) -> None:
    """A non-bundled tariff file controls seasons, tier windows, interval size, and rollover math."""
    tariff = tmp_path / "alt_tariff.json"
    csv_path = tmp_path / "alt_fixture.csv"
    config = tmp_path / "run_alt.json"
    out = tmp_path / "report_alt.json"
    _write_custom_tariff(tariff, interval_minutes=30)
    csv_path.write_text(
        "meter_id,timestamp,register_kwh\n"
        "ALT-1,2024-04-20T09:30:00-05:00,990.000\n"
        "ALT-1,2024-04-20T10:00:00-05:00,995.000\n"
        "ALT-1,2024-04-20T10:30:00-05:00,2.500\n"
        "ALT-1,2024-04-20T18:00:00-05:00,8.500\n"
        "ALT-1,2024-04-20T23:00:00-05:00,12.500\n",
        encoding="utf-8",
    )
    _write_run_config(config, tariff, [("alt window set", csv_path)])

    got, want = _run_dynamic_case(config, out, built_binary)
    meter = _fixture_map(got)["alt window set"]["ALT-1"]
    expected_meter = _fixture_map(want)["alt window set"]["ALT-1"]
    assert got["timezone"] == "Verifier/Alt-Tariff"
    assert meter["rollover_events"] == 1
    assert abs(meter["demand_peak_kw"] - expected_meter["demand_peak_kw"]) < 0.001
    assert meter["tier_kwh"] == pytest.approx(expected_meter["tier_kwh"], abs=0.001)
    assert abs(meter["total_kwh"] - expected_meter["total_kwh"]) < 0.001


def test_dynamic_quoted_csv_fields_and_many_meters(tmp_path: Path, built_binary: Path) -> None:
    """Quoted CSV meter ids, commas, quotes, and more than sixty-four meters are parsed and emitted exactly."""
    tariff = tmp_path / "tariff_many.json"
    csv_path = tmp_path / "many_meters.csv"
    config = tmp_path / "run_many.json"
    out = tmp_path / "report_many.json"
    _write_custom_tariff(tariff, interval_minutes=15)
    lines = ["meter_id,timestamp,register_kwh"]
    special = 'MTR, "South" feeder'
    for i in range(72):
        meter_id = special if i == 5 else f"DYN-MTR-{i:02d}"
        meter_csv = '"' + meter_id.replace('"', '""') + '"'
        lines.append(f"{meter_csv},2024-05-01T08:00:00-05:00,{100 + i:.3f}")
        lines.append(f"{meter_csv},2024-05-01T08:15:00-05:00,{100 + i + 1.25:.3f}")
    csv_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    _write_run_config(config, tariff, [("many meters", csv_path)])

    got, want = _run_dynamic_case(config, out, built_binary)
    meters = _fixture_map(got)["many meters"]
    assert set(meters) == set(_fixture_map(want)["many meters"])
    assert special in meters
    assert len(meters) == 72
    for meter_id, meter in meters.items():
        expected_meter = _fixture_map(want)["many meters"][meter_id]
        assert meter["interval_count"] == 1
        assert abs(meter["total_kwh"] - expected_meter["total_kwh"]) < 0.001
        assert meter["tier_kwh"] == pytest.approx(expected_meter["tier_kwh"], abs=0.001)


def test_dynamic_absolute_sorting_with_fractional_seconds(tmp_path: Path, built_binary: Path) -> None:
    """Absolute timestamp ordering includes numeric offsets and fractional seconds, not timestamp text order."""
    tariff = tmp_path / "tariff_fractional.json"
    csv_path = tmp_path / "fractional.csv"
    config = tmp_path / "run_fractional.json"
    out = tmp_path / "report_fractional.json"
    _write_custom_tariff(tariff, interval_minutes=15)
    csv_path.write_text(
        "meter_id,timestamp,register_kwh\n"
        "FRAC,2024-05-01T02:00:00.900-05:00,50.000\n"
        "FRAC,2024-05-01T02:15:00.100-05:00,51.000\n"
        "FRAC,2024-05-01T01:30:00.500-05:00,48.000\n"
        "FRAC,2024-05-01T01:45:00.500-05:00,49.000\n",
        encoding="utf-8",
    )
    _write_run_config(config, tariff, [("fractional order", csv_path)])

    got, want = _run_dynamic_case(config, out, built_binary)
    meter = _fixture_map(got)["fractional order"]["FRAC"]
    expected_meter = _fixture_map(want)["fractional order"]["FRAC"]
    assert meter["interval_count"] == 3
    assert meter["gap_intervals"] == expected_meter["gap_intervals"]
    assert abs(meter["total_kwh"] - expected_meter["total_kwh"]) < 0.001
    assert meter["tier_kwh"] == pytest.approx(expected_meter["tier_kwh"], abs=0.001)


def test_dynamic_more_than_sixteen_fixture_sets(tmp_path: Path, built_binary: Path) -> None:
    """All configured fixture sets are processed, not just a small fixed-size prefix or sixty-four-entry cap."""
    tariff = tmp_path / "tariff_many_fixtures.json"
    config = tmp_path / "run_many_fixtures.json"
    out = tmp_path / "report_many_fixtures.json"
    _write_custom_tariff(tariff, interval_minutes=15)
    fixtures: list[tuple[str, Path]] = []
    for i in range(72):
        csv_path = tmp_path / f"fx_{i:02d}.csv"
        csv_path.write_text(
            "meter_id,timestamp,register_kwh\n"
            f"FX-{i:02d},2024-05-02T11:00:00-05:00,{10 + i:.3f}\n"
            f"FX-{i:02d},2024-05-02T11:15:00-05:00,{11 + i:.3f}\n",
            encoding="utf-8",
        )
        fixtures.append((f"fixture {i:02d}", csv_path))
    _write_run_config(config, tariff, fixtures)

    got, want = _run_dynamic_case(config, out, built_binary)
    assert [fx["name"] for fx in got["fixture_sets"]] == [fx["name"] for fx in want["fixture_sets"]]
    assert len(got["fixture_sets"]) == 72
    for name, meters in _fixture_map(got).items():
        meter_id = name.replace("fixture ", "FX-")
        assert meter_id in meters
        assert meters[meter_id]["interval_count"] == 1


def test_dynamic_prorates_gap_delta_across_tier_slots(tmp_path: Path, built_binary: Path) -> None:
    """A long register span is split across configured interval slots before tiering and demand."""
    tariff = tmp_path / "tariff_prorate.json"
    csv_path = tmp_path / "prorate.csv"
    config = tmp_path / "run_prorate.json"
    out = tmp_path / "report_prorate.json"
    _write_custom_tariff(tariff, interval_minutes=30)
    csv_path.write_text(
        "meter_id,timestamp,register_kwh\n"
        "PRORATE,2024-05-01T17:30:00-05:00,100.000\n"
        "PRORATE,2024-05-01T19:00:00-05:00,109.000\n",
        encoding="utf-8",
    )
    _write_run_config(config, tariff, [("prorated gap", csv_path)])

    got, want = _run_dynamic_case(config, out, built_binary)
    meter = _fixture_map(got)["prorated gap"]["PRORATE"]
    expected_meter = _fixture_map(want)["prorated gap"]["PRORATE"]
    assert meter["gap_intervals"] == 2
    assert meter["tier_kwh"] == pytest.approx(expected_meter["tier_kwh"], abs=0.001)
    assert meter["tier_kwh"]["on_peak"] > 0.0
    assert meter["tier_kwh"]["mid_peak"] > 0.0
    assert abs(meter["demand_peak_kw"] - expected_meter["demand_peak_kw"]) < 0.001
    assert meter["demand_peak_kw"] < 20.0


def test_dynamic_quality_reset_void_and_estimate_rows(tmp_path: Path, built_binary: Path) -> None:
    """Optional quality codes control void rows, reset baselines, and estimated reconciliation."""
    tariff = tmp_path / "tariff_quality.json"
    csv_path = tmp_path / "quality.csv"
    config = tmp_path / "run_quality.json"
    out = tmp_path / "report_quality.json"
    _write_custom_tariff(tariff, interval_minutes=15)
    csv_path.write_text(
        "meter_id,timestamp,register_kwh,quality\n"
        "QUAL,2024-05-01T08:00:00-05:00,100.000,actual\n"
        "QUAL,2024-05-01T08:15:00-05:00,101.000,actual\n"
        "QUAL,2024-05-01T08:30:00-05:00,999.000,void\n"
        "QUAL,2024-05-01T08:30:00-05:00,102.500,estimate\n"
        "QUAL,2024-05-01T08:45:00-05:00,0.000,reset\n"
        "QUAL,2024-05-01T09:00:00-05:00,2.000,actual\n",
        encoding="utf-8",
    )
    _write_run_config(config, tariff, [("quality rows", csv_path)])

    got, want = _run_dynamic_case(config, out, built_binary)
    meter = _fixture_map(got)["quality rows"]["QUAL"]
    expected_meter = _fixture_map(want)["quality rows"]["QUAL"]
    assert meter["interval_count"] == 3
    assert meter["rollover_events"] == 0
    assert abs(meter["total_kwh"] - 4.5) < 0.001
    assert meter["tier_kwh"] == pytest.approx(expected_meter["tier_kwh"], abs=0.001)
    assert meter["reconciled"] is False
    assert got["all_reconciled"] is False


def test_dynamic_wrapped_summer_range_and_prorated_slots(tmp_path: Path, built_binary: Path) -> None:
    """Wrapped summer ranges still use prorated slot starts across the new-year boundary."""
    tariff = tmp_path / "tariff_wrap.json"
    csv_path = tmp_path / "wrap.csv"
    config = tmp_path / "run_wrap.json"
    out = tmp_path / "report_wrap.json"
    tariff.write_text(
        json.dumps(
            {
                "timezone": "Verifier/Wrapped-Season",
                "register_max_kwh": 5000.0,
                "interval_minutes": 20,
                "demand_window_intervals": 3,
                "seasons": {
                    "summer": {"start_mmdd": "11-15", "end_mmdd": "02-15"},
                    "winter": {"start_mmdd": "02-16", "end_mmdd": "11-14"},
                },
                "windows": {
                    "summer": {
                        "off_peak": [["00:00", "06:00"]],
                        "mid_peak": [["06:00", "18:00"]],
                        "on_peak": [["18:00", "00:00"]],
                    },
                    "winter": {
                        "off_peak": [["22:00", "06:00"]],
                        "mid_peak": [["06:00", "12:00"], ["20:00", "22:00"]],
                        "on_peak": [["12:00", "20:00"]],
                    },
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    csv_path.write_text(
        "meter_id,timestamp,register_kwh\n"
        "WRAP,2024-12-31T23:40:00+02:00,200.000\n"
        "WRAP,2025-01-01T00:40:00+02:00,206.000\n",
        encoding="utf-8",
    )
    _write_run_config(config, tariff, [("wrapped season", csv_path)])

    got, want = _run_dynamic_case(config, out, built_binary)
    meter = _fixture_map(got)["wrapped season"]["WRAP"]
    expected_meter = _fixture_map(want)["wrapped season"]["WRAP"]
    assert got["timezone"] == "Verifier/Wrapped-Season"
    assert meter["gap_intervals"] == 2
    assert meter["tier_kwh"] == pytest.approx(expected_meter["tier_kwh"], abs=0.001)
    assert meter["tier_kwh"]["on_peak"] > 0.0
    assert meter["tier_kwh"]["off_peak"] > 0.0


def test_dynamic_slot_crossing_tou_boundary_uses_overlap_seconds(tmp_path: Path, built_binary: Path) -> None:
    """A generated slot crossing a TOU boundary is prorated by seconds, not assigned only by start time."""
    tariff = tmp_path / "tariff_overlap.json"
    csv_path = tmp_path / "overlap.csv"
    config = tmp_path / "run_overlap.json"
    out = tmp_path / "report_overlap.json"
    _write_custom_tariff(tariff, interval_minutes=15)
    csv_path.write_text(
        "meter_id,timestamp,register_kwh\n"
        "OVERLAP,2024-05-01T17:50:00-05:00,100.000\n"
        "OVERLAP,2024-05-01T18:20:00-05:00,106.000\n",
        encoding="utf-8",
    )
    _write_run_config(config, tariff, [("overlap boundary", csv_path)])

    got = run_report(config, out)
    meter = _fixture_map(got)["overlap boundary"]["OVERLAP"]
    assert meter["interval_count"] == 1
    assert meter["gap_intervals"] == 1
    assert abs(meter["total_kwh"] - 6.0) < 0.001
    # The alternate summer tariff has on_peak 10:00-18:00 and mid_peak 18:00-23:00.
    assert abs(meter["tier_kwh"]["on_peak"] - 2.0) < 0.001
    assert abs(meter["tier_kwh"]["mid_peak"] - 4.0) < 0.001
    assert abs(meter["tier_kwh"]["off_peak"] - 0.0) < 0.001
    assert abs(meter["demand_peak_kw"] - 12.0) < 0.001


def test_dynamic_duplicate_timestamp_corrections_replace_prior_row(tmp_path: Path, built_binary: Path) -> None:
    """Duplicate absolute timestamps for a meter use the last CSV reading without creating a zero-time interval."""
    tariff = tmp_path / "tariff_duplicate.json"
    csv_path = tmp_path / "duplicate.csv"
    config = tmp_path / "run_duplicate.json"
    out = tmp_path / "report_duplicate.json"
    _write_custom_tariff(tariff, interval_minutes=15)
    csv_path.write_text(
        "meter_id,timestamp,register_kwh\n"
        "DUP,2024-05-01T08:00:00-05:00,100.000\n"
        "DUP,2024-05-01T08:00:00-05:00,103.000\n"
        "DUP,2024-05-01T08:15:00-05:00,105.000\n",
        encoding="utf-8",
    )
    _write_run_config(config, tariff, [("duplicate correction", csv_path)])

    got = run_report(config, out)
    meter = _fixture_map(got)["duplicate correction"]["DUP"]
    assert meter["interval_count"] == 1
    assert meter["gap_intervals"] == 0
    assert meter["rollover_events"] == 0
    assert abs(meter["total_kwh"] - 2.0) < 0.001
    assert abs(meter["register_delta_kwh"] - 2.0) < 0.001
    assert meter["reconciled"] is True


def test_dynamic_duplicate_timestamp_reset_correction_is_not_rollover(tmp_path: Path, built_binary: Path) -> None:
    """A same-timestamp reset after an actual reading closes the prior interval, then becomes the next baseline."""
    tariff = tmp_path / "tariff_duplicate_reset.json"
    csv_path = tmp_path / "duplicate_reset.csv"
    config = tmp_path / "run_duplicate_reset.json"
    out = tmp_path / "report_duplicate_reset.json"
    _write_custom_tariff(tariff, interval_minutes=15)
    csv_path.write_text(
        "meter_id,timestamp,register_kwh,quality\n"
        "DUPRESET,2024-05-01T12:00:00-05:00,450.000,actual\n"
        "DUPRESET,2024-05-01T12:15:00-05:00,452.000,actual\n"
        "DUPRESET,2024-05-01T12:15:00-05:00,10.000,reset\n"
        "DUPRESET,2024-05-01T12:30:00-05:00,13.500,actual\n",
        encoding="utf-8",
    )
    _write_run_config(config, tariff, [("duplicate reset", csv_path)])

    got = run_report(config, out)
    meter = _fixture_map(got)["duplicate reset"]["DUPRESET"]
    assert meter["interval_count"] == 2
    assert meter["rollover_events"] == 0
    assert abs(meter["total_kwh"] - 5.5) < 0.001
    assert abs(meter["register_delta_kwh"] - 5.5) < 0.001
    assert meter["reconciled"] is True
