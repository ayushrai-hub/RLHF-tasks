"""
Verifier for the PSON seafloor change-point detection CLI.

Expectations are derived at runtime by a reference pipeline that parses the dossier,
calibrates database readings, and runs the detrend / robust-Z / Bayesian scoring
methodology described in the operations dossier. Hidden mutation tests rebuild the
database with verifier-only perturbations so lookup-table catalogs cannot pass.
"""

from __future__ import annotations

import json
import math
import os
import re
import shutil
import sqlite3
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pytest

OUTPUT_PATH = "/app/output/events.json"
CLI_ENTRY = "/app/dist/src/index.js"
DB_PATH = "/app/data/sensors.db"
DOSSIER_PATH = "/app/docs/seismology_ops_dossier.md"
DB_BACKUP_PATH = "/tmp/sensors_backup.db"

PRESSURE_TO_DISPLACEMENT_M_PER_KPA = 0.1
MAD_CONSISTENCY_CONSTANT = 1.4826
STATIONS = ("AXID01", "AXID02", "NEMO01", "JUAN01", "COAX01")

# Verifier-only mutation key — not present in the agent environment.
_MUTATION_KEY = 0x5EAF0102


@dataclass(frozen=True)
class CalibrationParams:
    station_id: str
    pressure_gain: float
    pressure_offset: float
    z_score_threshold: float
    min_duration_hours: float
    maintenance_windows: list[tuple[datetime, datetime, str]]


def parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def load_catalog(path: str = OUTPUT_PATH) -> dict:
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def run_cli(db_path: str, dossier_path: str, output_path: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "node",
            "dist/src/index.js",
            "--db",
            db_path,
            "--dossier",
            dossier_path,
            "--output",
            output_path,
        ],
        cwd="/app",
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


# ---------------------------------------------------------------------------
# Reference pipeline (mirrors the oracle methodology)
# ---------------------------------------------------------------------------


def _extract_gain(text: str) -> float | None:
    patterns = [
        r"pressure\s+gain\s*[:=]\s*([\d]+\.[\d]+)",
        r"\bgain\s+of\s+([\d]+\.[\d]+)",
        r"gain\s+correction\s+(?:factor\s+)?(?:is\s+)?([\d]+\.[\d]+)",
        r"\bgain\s+([\d]+\.[\d]+)",
        r"multiplicative\s+gain\s+correction[^0-9]*([\d]+\.[\d]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            value = float(match.group(1))
            if 0.5 < value < 2.5:
                return value
    return None


def _extract_offset(text: str) -> float | None:
    patterns = [
        r"pressure\s+offset\s*[:=]\s*([^\s,\n]{1,12})\s*(?:kPa)?",
        r"\boffset\s+(?:of\s+)?([+−\-][\s\d.]+|\d+\.\d+)\s*(?:kPa)?",
        r"raw_value\s*[×x*]\s*[\d.]+\s*\+\s*\(\s*([−+\-][\d.]+)\s*\)",
        r"additive\s+(?:pressure\s+)?offset(?:\s+is)?\s+([^\s,kK]{1,12})\s*(?:kPa|kilo)?",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            raw = match.group(1).replace("−", "-").replace(" ", "")
            value = float(raw)
            if not math.isnan(value) and abs(value) < 10:
                return value
    return None


def _extract_z_threshold(text: str) -> float | None:
    patterns = [
        r"z.score\s+threshold\s*[:=]\s*([\d]+\.[\d]*)\s*(?:standard\s+deviations?|sigma)?",
        r"z.score\s+threshold\s+of\s+([\d]+\.[\d]*)\s*(?:sigma|standard)?",
        r"threshold\s+(?:of\s+)?([\d]+\.[\d]*)\s+(?:sigma|standard\s+deviation)",
        r"\b([\d]+\.[\d]*)\s+sigma\b",
        r"detection\s+threshold[^0-9]*([\d]+\.[\d]*)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            value = float(match.group(1))
            if 0.5 < value < 15:
                return value
    return None


def _extract_min_duration(text: str) -> float | None:
    patterns = [
        r"minimum\s+event\s+duration\s*[:=]\s*([\d]+\.[\d]*)\s+hours?",
        r"minimum\s+duration\s+criterion\s+(?:of\s+)?([\d]+\.[\d]*)\s+hours?",
        r"minimum\s+(?:sustained\s+)?duration(?:\s+(?:is|of|required))?\s+(?:is\s+)?([\d]+\.[\d]*)\s+hours?",
        r"duration\s+criterion[^0-9]*([\d]+\.[\d]*)\s+hours?",
        r"lasting\s+(?:fewer|less)\s+than\s+([\d]+\.[\d]*)\s+hours?",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            value = float(match.group(1))
            if 0 < value < 48:
                return value
    return None


def _extract_maintenance_windows(text: str) -> list[tuple[datetime, datetime, str]]:
    windows: list[tuple[datetime, datetime, str]] = []
    prose = re.finditer(r"january\s+(\d{1,2})[^0-9]+(\d{1,2})[^0-9]*2024", text, flags=re.IGNORECASE)
    iso = re.finditer(r"2024-01-(\d{2})T[^Z]*Z[^0-9]+2024-01-(\d{2})", text, flags=re.IGNORECASE)
    for match in list(prose) + list(iso):
        day1 = int(match.group(1))
        day2 = int(match.group(2))
        if 1 <= day1 <= 31 and day1 <= day2 <= 31:
            windows.append(
                (
                    datetime(2024, 1, day1, tzinfo=timezone.utc),
                    datetime(2024, 1, day2, 23, 59, 59, 999000, tzinfo=timezone.utc),
                    "Maintenance window per operations dossier",
                )
            )
            break
    return windows


def _parse_block(text: str, station_id: str) -> CalibrationParams | None:
    gain = _extract_gain(text)
    offset = _extract_offset(text)
    z_threshold = _extract_z_threshold(text)
    min_duration = _extract_min_duration(text)
    if None in (gain, offset, z_threshold, min_duration):
        return None
    return CalibrationParams(
        station_id=station_id,
        pressure_gain=gain,
        pressure_offset=offset,
        z_score_threshold=z_threshold,
        min_duration_hours=min_duration,
        maintenance_windows=_extract_maintenance_windows(text),
    )


def parse_dossier(text: str) -> dict[str, CalibrationParams]:
    result: dict[str, CalibrationParams] = {}

    sec29_idx = text.find("Quality Control Event Log: January 2024")
    sec30_idx = text.find("\n## 30.")
    if sec29_idx >= 0:
        section = text[sec29_idx:sec30_idx] if sec30_idx > sec29_idx else text[sec29_idx : sec29_idx + 20000]
        for chunk in re.split(r"\n###\s+29\.\d+\s+", section):
            for station_id in STATIONS:
                if station_id not in result and station_id in chunk:
                    params = _parse_block(chunk, station_id)
                    if params:
                        result[station_id] = params

    appendix_f_idx = text.find("Appendix F")
    appendix_g_idx = text.find("Appendix G")
    if appendix_f_idx >= 0:
        appendix = text[appendix_f_idx:appendix_g_idx] if appendix_g_idx > appendix_f_idx else text[appendix_f_idx:]
        for block in re.split(r"\n\n(?=\*\*Station )", appendix):
            match = re.search(r"\*\*Station ([A-Z0-9]+)", block)
            if not match:
                continue
            station_id = match.group(1)
            if station_id in result:
                continue
            params = _parse_block(block, station_id)
            if params:
                result[station_id] = params

    for station_id in STATIONS:
        if station_id in result:
            continue
        match = re.search(
            rf"## \d+\.\s+Station {station_id}[\s\S]{{0,12000}}?(?=\n## \d+\.)",
            text,
            flags=re.IGNORECASE,
        )
        if match:
            params = _parse_block(match.group(0), station_id)
            if params:
                result[station_id] = params

    for station_id in STATIONS:
        if station_id in result:
            continue
        idx = text.find(station_id)
        if idx >= 0:
            params = _parse_block(text[max(0, idx - 200) : idx + 10000], station_id)
            if params:
                result[station_id] = params

    return result


def _detrend(values: list[float]) -> list[float]:
    n = len(values)
    if n < 2:
        return values[:]
    sx = sy = sxx = sxy = 0.0
    for i, value in enumerate(values):
        sx += i
        sy += value
        sxx += i * i
        sxy += i * value
    denom = n * sxx - sx * sx
    if abs(denom) < 1e-12:
        mean = sy / n
        return [value - mean for value in values]
    slope = (n * sxy - sx * sy) / denom
    intercept = (sy - slope * sx) / n
    return [value - (slope * i + intercept) for i, value in enumerate(values)]


def _median(sorted_values: list[float]) -> float:
    n = len(sorted_values)
    if n == 0:
        return 0.0
    mid = n // 2
    return sorted_values[mid] if n % 2 else (sorted_values[mid - 1] + sorted_values[mid]) / 2


def _compute_mad(values: list[float]) -> tuple[float, float]:
    sorted_values = sorted(values)
    med = _median(sorted_values)
    abs_devs = sorted(abs(value - med) for value in values)
    return med, _median(abs_devs)


def _robust_z_scores(values: list[float]) -> list[float]:
    _, mad = _compute_mad(values)
    sigma = MAD_CONSISTENCY_CONSTANT * (mad if mad > 1e-12 else 1e-12)
    med, _ = _compute_mad(values)
    return [(value - med) / sigma for value in values]


def _bayesian_confidence(window: list[float], bg_sigma: float) -> float:
    n = len(window)
    if n == 0:
        return 0.0
    delta = sum(window) / n
    sig2 = bg_sigma * bg_sigma
    if sig2 < 1e-20:
        return 0.0
    log_bf = (n * delta * delta) / (2 * sig2) - 0.5 * math.log(n)
    return 1 / (1 + math.exp(-log_bf / 2.0))


def _detect_events(
    station_id: str,
    timestamps: list[datetime],
    calibrated: list[float],
    params: CalibrationParams,
) -> list[dict]:
    detrended = _detrend(calibrated)
    z_scores = _robust_z_scores(detrended)
    _, mad = _compute_mad(detrended)
    bg_sigma = MAD_CONSISTENCY_CONSTANT * (mad if mad > 1e-12 else 1e-12)
    min_samples = math.ceil(params.min_duration_hours * 6)

    events: list[dict] = []
    index = 0
    while index < len(z_scores):
        if abs(z_scores[index]) >= params.z_score_threshold:
            end = index + 1
            while end < len(z_scores) and abs(z_scores[end]) >= params.z_score_threshold:
                end += 1
            if end - index >= min_samples:
                window = detrended[index:end]
                mean_anomaly = sum(window) / len(window)
                displacement = mean_anomaly * PRESSURE_TO_DISPLACEMENT_M_PER_KPA
                confidence = _bayesian_confidence(window, bg_sigma)
                start_time = timestamps[index]
                finish_time = timestamps[end - 1]
                duration_hours = (finish_time - start_time).total_seconds() / 3600

                excluded = False
                exclusion_reason: str | None = None
                for start, finish, reason in params.maintenance_windows:
                    if start <= start_time <= finish:
                        excluded = True
                        exclusion_reason = (
                            f"{reason} ({start.date().isoformat()} to {finish.date().isoformat()})"
                        )
                        break

                events.append(
                    {
                        "station_id": station_id,
                        "sensor_type": "pressure",
                        "start_time": start_time.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                        "duration_hours": round(duration_hours, 2),
                        "displacement_estimate": round(displacement, 4),
                        "confidence_score": round(confidence, 4),
                        "excluded": excluded,
                        "exclusion_reason": exclusion_reason,
                    }
                )
                index = end
                continue
        index += 1
    return events


def _select_primary_event(events: list[dict]) -> dict | None:
    if not events:
        return None
    return max(events, key=lambda event: (event["confidence_score"], event["duration_hours"]))


def reference_catalog(db_path: str, dossier_path: str) -> dict:
    dossier_text = Path(dossier_path).read_text(encoding="utf-8")
    calibrations = parse_dossier(dossier_text)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    station_ids = [
        row["station_id"]
        for row in conn.execute(
            "SELECT DISTINCT station_id FROM readings ORDER BY station_id"
        ).fetchall()
    ]

    all_events: list[dict] = []
    for station_id in station_ids:
        params = calibrations.get(station_id)
        if params is None:
            continue
        rows = conn.execute(
            """
            SELECT timestamp, raw_value
            FROM readings
            WHERE station_id = ? AND sensor_type = 'pressure'
            ORDER BY timestamp ASC
            """,
            (station_id,),
        ).fetchall()
        if not rows:
            continue

        timestamps = [parse_iso(row["timestamp"]) for row in rows]
        calibrated = [
            row["raw_value"] * params.pressure_gain + params.pressure_offset for row in rows
        ]
        detected = _detect_events(station_id, timestamps, calibrated, params)
        primary = _select_primary_event(detected)
        if primary is not None:
            all_events.append(primary)

    conn.close()
    excluded = sum(1 for event in all_events if event["excluded"])
    return {
        "total_events": len(all_events),
        "excluded_events": excluded,
        "events": all_events,
    }


def event_by_station(catalog: dict, station_id: str) -> dict | None:
    matches = [event for event in catalog["events"] if event["station_id"] == station_id]
    if not matches:
        return None
    return max(matches, key=lambda event: (event["confidence_score"], event["duration_hours"]))


def references_juan01_maintenance_window(reason: str) -> bool:
    lower = reason.lower()
    maintenance_terms = (
        "maintenance",
        "servicing",
        "service",
        "battery",
        "tiltmeter",
        "reorientation",
        "rov",
        "shutdown",
        "replacement",
        "offline",
        "intervention",
    )
    if any(term in lower for term in maintenance_terms):
        return True
    if "january" in lower or " jan " in f" {lower} ":
        if any(day in lower for day in ("8", "08", "9", "09", "10", "11", "12")):
            return True
    return False


def assert_event_near(expected: dict, actual: dict, station_id: str) -> None:
    exp_start = parse_iso(expected["start_time"])
    act_start = parse_iso(actual["start_time"])
    start_delta_min = abs((act_start - exp_start).total_seconds()) / 60
    assert start_delta_min <= 40, (
        f"{station_id} start_time {actual['start_time']} is {start_delta_min:.0f} min "
        f"from reference {expected['start_time']}"
    )

    exp_disp = expected["displacement_estimate"]
    act_disp = actual["displacement_estimate"]
    if abs(exp_disp) > 1e-6:
        rel_err = abs(act_disp - exp_disp) / abs(exp_disp)
        assert rel_err <= 0.15, (
            f"{station_id} displacement {act_disp:.4f} m is {rel_err * 100:.1f}% "
            f"from reference {exp_disp:.4f} m"
        )
    else:
        assert abs(act_disp) <= 0.005, f"{station_id} displacement should be near zero"

    assert actual["excluded"] == expected["excluded"], (
        f"{station_id} excluded flag {actual['excluded']} != reference {expected['excluded']}"
    )

    if expected["excluded"]:
        assert actual.get("exclusion_reason"), f"{station_id} missing exclusion_reason"
        assert references_juan01_maintenance_window(actual["exclusion_reason"]), (
            f"Exclusion reason '{actual['exclusion_reason']}' does not cite JUAN01 maintenance"
        )


@pytest.fixture(scope="module")
def expected_catalog() -> dict:
    return reference_catalog(DB_PATH, DOSSIER_PATH)


@pytest.fixture(scope="module")
def agent_catalog() -> dict:
    return load_catalog()


# ---------------------------------------------------------------------------
# Schema and structure
# ---------------------------------------------------------------------------


class TestCatalogStructure:
    """Verify the top-level catalog JSON schema."""

    def test_file_exists(self):
        """Output file must exist at the expected path."""
        assert os.path.isfile(OUTPUT_PATH), f"Expected output at {OUTPUT_PATH}"

    def test_valid_json(self):
        """Output must be valid JSON."""
        with open(OUTPUT_PATH, encoding="utf-8") as handle:
            data = json.load(handle)
        assert isinstance(data, dict)

    def test_top_level_fields(self, agent_catalog):
        """Catalog must have generated_at, total_events, excluded_events, events."""
        for field in ("generated_at", "total_events", "excluded_events", "events"):
            assert field in agent_catalog, f"Missing top-level field: {field}"

    def test_events_is_list(self, agent_catalog):
        """events field must be a JSON array."""
        assert isinstance(agent_catalog["events"], list)

    def test_total_events_matches_list(self, agent_catalog):
        """total_events must equal the length of the events array."""
        assert agent_catalog["total_events"] == len(agent_catalog["events"])

    def test_excluded_count_consistent(self, agent_catalog):
        """excluded_events must equal the number of events with excluded=true."""
        actual_excluded = sum(1 for event in agent_catalog["events"] if event.get("excluded") is True)
        assert agent_catalog["excluded_events"] == actual_excluded

    def test_event_schema(self, agent_catalog):
        """Each event must contain the required fields with correct types."""
        required = {
            "station_id": str,
            "sensor_type": str,
            "start_time": str,
            "duration_hours": (int, float),
            "displacement_estimate": (int, float),
            "confidence_score": (int, float),
            "excluded": bool,
        }
        for event in agent_catalog["events"]:
            for field, expected_type in required.items():
                assert field in event, f"Event missing field: {field}"
                assert isinstance(event[field], expected_type), (
                    f"Field {field} has wrong type: {type(event[field])}"
                )
            assert "exclusion_reason" in event


# ---------------------------------------------------------------------------
# Reference pipeline alignment
# ---------------------------------------------------------------------------


class TestReferenceAlignment:
    """Compare agent output against the verifier reference pipeline."""

    def test_cli_entry_exists(self):
        """Compiled CLI entry point must exist."""
        assert os.path.isfile(CLI_ENTRY), (
            "CLI entry point dist/src/index.js must exist (run npm run build)"
        )

    def test_event_count_matches_reference(self, agent_catalog, expected_catalog):
        """Agent catalog size must match the reference pipeline."""
        assert agent_catalog["total_events"] == expected_catalog["total_events"], (
            f"total_events {agent_catalog['total_events']} != reference "
            f"{expected_catalog['total_events']}"
        )

    def test_excluded_count_matches_reference(self, agent_catalog, expected_catalog):
        """Excluded event count must match the reference pipeline."""
        assert agent_catalog["excluded_events"] == expected_catalog["excluded_events"]

    def test_one_event_per_station(self, agent_catalog):
        """Exactly one event candidate per active station must be reported."""
        station_ids = {event["station_id"] for event in agent_catalog["events"]}
        assert station_ids == set(STATIONS), f"Expected stations {STATIONS}, got {sorted(station_ids)}"

    @pytest.mark.parametrize("station_id", STATIONS)
    def test_station_event_matches_reference(self, agent_catalog, expected_catalog, station_id):
        """Each station event must align with the reference pipeline within tolerance."""
        expected = event_by_station(expected_catalog, station_id)
        actual = event_by_station(agent_catalog, station_id)
        assert expected is not None, f"Reference pipeline found no event for {station_id}"
        assert actual is not None, f"Agent catalog missing event for {station_id}"
        assert_event_near(expected, actual, station_id)

    def test_juan01_event_in_maintenance_window(self, agent_catalog):
        """The excluded JUAN01 event must fall inside the January 8–12 maintenance window."""
        juan01 = event_by_station(agent_catalog, "JUAN01")
        assert juan01 is not None
        assert juan01["excluded"] is True
        start = parse_iso(juan01["start_time"])
        maint_start = datetime(2024, 1, 8, tzinfo=timezone.utc)
        maint_end = datetime(2024, 1, 12, 23, 59, 59, tzinfo=timezone.utc)
        assert maint_start <= start <= maint_end, (
            f"JUAN01 start {juan01['start_time']} outside maintenance window"
        )


class TestScoresAndTiming:
    """Validate confidence scores and ISO timestamp formatting."""

    def test_confidence_scores_in_range(self, agent_catalog):
        """All confidence_score values must be in [0, 1]."""
        for event in agent_catalog["events"]:
            score = event["confidence_score"]
            assert 0 <= score <= 1, f"confidence_score {score} out of [0,1] for {event['station_id']}"

    def test_duration_positive(self, agent_catalog):
        """All duration_hours values must be positive."""
        for event in agent_catalog["events"]:
            assert event["duration_hours"] > 0

    def test_start_time_parseable(self, agent_catalog):
        """All start_time strings must be parseable as ISO 8601 UTC timestamps."""
        for event in agent_catalog["events"]:
            parse_iso(event["start_time"])

    def test_start_times_within_january(self, agent_catalog):
        """All event start times should fall within January 2024."""
        jan_start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        jan_end = datetime(2024, 1, 31, 23, 59, 59, tzinfo=timezone.utc)
        for event in agent_catalog["events"]:
            start = parse_iso(event["start_time"])
            assert jan_start <= start <= jan_end

    def test_detected_events_have_positive_confidence(self, agent_catalog):
        """Non-excluded events should have confidence > 0."""
        for event in agent_catalog["events"]:
            if not event["excluded"]:
                assert event["confidence_score"] > 0


# ---------------------------------------------------------------------------
# Hidden mutation / anti-cheating
# ---------------------------------------------------------------------------


def _mutation_station(index: int) -> str:
    """Pick a station for deletion tests using verifier-only entropy."""
    return STATIONS[(_MUTATION_KEY + index) % len(STATIONS)]


def _copy_db(source: str, destination: str) -> None:
    shutil.copy2(source, destination)


def _delete_station_pressure(db_path: str, station_id: str) -> None:
    conn = sqlite3.connect(db_path)
    conn.execute(
        "DELETE FROM readings WHERE station_id = ? AND sensor_type = 'pressure'",
        (station_id,),
    )
    conn.commit()
    conn.close()


def _amplify_station_anomaly(db_path: str, station_id: str, scale: float) -> None:
    """Scale the strongest contiguous pressure excursion for a station."""
    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        """
        SELECT id, raw_value
        FROM readings
        WHERE station_id = ? AND sensor_type = 'pressure'
        ORDER BY timestamp ASC
        """,
        (station_id,),
    ).fetchall()
    if not rows:
        conn.close()
        return

    values = [row[1] for row in rows]
    baseline = sum(values) / len(values)
    deviations = [value - baseline for value in values]

    best_start = 0
    best_score = 0.0
    window = 18
    for start in range(0, len(deviations) - window):
        score = sum(abs(deviations[start + offset]) for offset in range(window))
        if score > best_score:
            best_score = score
            best_start = start

    updates = []
    for offset in range(window):
        row_id, raw_value = rows[best_start + offset]
        centered = raw_value - baseline
        updates.append((baseline + centered * scale, row_id))

    conn.executemany("UPDATE readings SET raw_value = ? WHERE id = ?", updates)
    conn.commit()
    conn.close()


class TestHiddenMutations:
    """Verifier-only database perturbations block static lookup-table catalogs."""

    def test_deleted_station_absent_from_mutated_run(self):
        """Removing a station's pressure channel must drop that station from a fresh CLI run."""
        station_id = _mutation_station(1)
        mutated_db = f"/tmp/sensors_mut_del_{station_id}.db"
        output_path = f"/tmp/events_mut_del_{station_id}.json"

        _copy_db(DB_PATH, mutated_db)
        _delete_station_pressure(mutated_db, station_id)

        try:
            result = run_cli(mutated_db, DOSSIER_PATH, output_path)
            assert result.returncode == 0, result.stderr
            catalog = load_catalog(output_path)
            assert station_id not in {event["station_id"] for event in catalog["events"]}, (
                f"{station_id} should disappear after its pressure readings are deleted"
            )
            assert catalog["total_events"] == len(STATIONS) - 1
        finally:
            for path in (mutated_db, output_path):
                if os.path.isfile(path):
                    os.remove(path)

    def test_mutated_amplitude_matches_reference_pipeline(self):
        """A verifier-only amplitude perturbation must shift displacement per the reference pipeline."""
        station_id = _mutation_station(2)
        scale = 1.0 + ((_MUTATION_KEY >> 8) % 25) / 100.0
        mutated_db = f"/tmp/sensors_mut_amp_{station_id}.db"
        output_path = f"/tmp/events_mut_amp_{station_id}.json"

        _copy_db(DB_PATH, mutated_db)
        _amplify_station_anomaly(mutated_db, station_id, scale)

        try:
            expected = reference_catalog(mutated_db, DOSSIER_PATH)
            result = run_cli(mutated_db, DOSSIER_PATH, output_path)
            assert result.returncode == 0, result.stderr
            actual = load_catalog(output_path)

            assert actual["total_events"] == expected["total_events"]
            assert_event_near(
                event_by_station(expected, station_id),
                event_by_station(actual, station_id),
                station_id,
            )
            baseline = reference_catalog(DB_PATH, DOSSIER_PATH)
            base_disp = event_by_station(baseline, station_id)["displacement_estimate"]
            mut_disp = event_by_station(actual, station_id)["displacement_estimate"]
            assert abs(mut_disp) > abs(base_disp) * 1.05, (
                "Mutated displacement should differ materially from the default catalog"
            )
        finally:
            for path in (mutated_db, output_path):
                if os.path.isfile(path):
                    os.remove(path)

    def test_uncalibrated_lookup_table_fails_hidden_mutation(self):
        """Hard-coded displacement tables cannot track verifier-only amplitude mutations."""
        station_id = _mutation_station(3)
        scale = 1.35
        mutated_db = f"/tmp/sensors_mut_guard_{station_id}.db"
        output_path = f"/tmp/events_mut_guard_{station_id}.json"

        _copy_db(DB_PATH, mutated_db)
        _amplify_station_anomaly(mutated_db, station_id, scale)

        try:
            expected_event = event_by_station(reference_catalog(mutated_db, DOSSIER_PATH), station_id)
            result = run_cli(mutated_db, DOSSIER_PATH, output_path)
            assert result.returncode == 0, result.stderr
            actual_event = event_by_station(load_catalog(output_path), station_id)

            assert expected_event is not None and actual_event is not None
            exp_disp = expected_event["displacement_estimate"]
            act_disp = actual_event["displacement_estimate"]
            rel_err = abs(act_disp - exp_disp) / max(abs(exp_disp), 1e-6)
            assert rel_err <= 0.15, (
                f"Agent displacement {act_disp} did not track mutated reference {exp_disp}"
            )

            default_event = event_by_station(reference_catalog(DB_PATH, DOSSIER_PATH), station_id)
            default_err = abs(act_disp - default_event["displacement_estimate"]) / max(
                abs(default_event["displacement_estimate"]), 1e-6
            )
            assert default_err > 0.15, (
                "Output still matches the unmutated lookup-table displacement"
            )
        finally:
            for path in (mutated_db, output_path):
                if os.path.isfile(path):
                    os.remove(path)

    def test_default_db_restored_after_mutation(self):
        """Ensure live DB is unchanged after mutation tests copy from the fixture."""
        shutil.copy2(DB_PATH, DB_BACKUP_PATH)
        try:
            mutated = "/tmp/sensors_restore_check.db"
            _copy_db(DB_PATH, mutated)
            _delete_station_pressure(mutated, _mutation_station(0))
            assert os.path.getsize(DB_PATH) == os.path.getsize(DB_BACKUP_PATH)
        finally:
            if os.path.isfile(DB_BACKUP_PATH):
                os.remove(DB_BACKUP_PATH)