"""
Verifier tests for mavlink-mission-upload-sequence-auditor.

Runs mission-ingest and mission-export, validates X.25 CRC framing (with and without
mavlink-v2 CRC extra), SQLite waypoints, upload idempotency, rollback on corrupt logs,
seq-ordered distance, and relative altitude.
"""

from __future__ import annotations

import json
import math
import os
import sqlite3
import subprocess
from pathlib import Path

import pytest

from gen_mseq_fixtures import hidden_fixture_root, main as gen_fixtures
from mission_expect import expected_export

FIXTURES = gen_fixtures()
FIXTURES_HIDDEN = hidden_fixture_root()

INGEST = Path("/app/bin/mission-ingest")
EXPORT = Path("/app/bin/mission-export")
EPOCH_BASE = 1_704_067_200
HOME_V1 = 120.5
HOME_V2 = 85.0


def alt_relative(alt_mm: int, home_alt_m: float) -> float:
    return round(alt_mm / 1000.0 - home_alt_m, 3)


def alt_global(alt_mm: int) -> float:
    return round(alt_mm / 1000.0, 3)


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6_371_000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def run_ingest(db: Path, log: Path, upload_id: str, vehicle: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            str(INGEST),
            "--db",
            str(db),
            "--log",
            str(log),
            "--upload-id",
            upload_id,
            "--vehicle",
            vehicle,
        ],
        capture_output=True,
        text=True,
        check=False,
        env={
            "PATH": "/app/bin:/usr/local/cargo/bin:" + os.environ.get("PATH", ""),
            "MISSION_EPOCH_BASE": str(EPOCH_BASE),
        },
    )


def run_export(db: Path, vehicle: str, upload_id: str, out: Path) -> subprocess.CompletedProcess[str]:
    return run_export_with_epoch(db, vehicle, upload_id, out, EPOCH_BASE)


def run_export_with_epoch(
    db: Path, vehicle: str, upload_id: str, out: Path, epoch_base: int
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            str(EXPORT),
            "--db",
            str(db),
            "--vehicle",
            vehicle,
            "--upload-id",
            upload_id,
            "--out",
            str(out),
        ],
        capture_output=True,
        text=True,
        check=False,
        env={
            "PATH": "/app/bin:/usr/local/cargo/bin:" + os.environ.get("PATH", ""),
            "MISSION_EPOCH_BASE": str(epoch_base),
        },
    )


def connect(db: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    return conn


@pytest.fixture
def tmp_paths(tmp_path: Path) -> dict[str, Path]:
    return {"db": tmp_path / "missions.db", "report": tmp_path / "report.json"}


def test_alpha_sample_ingest_and_export(tmp_paths: dict[str, Path]) -> None:
    """Public sample log ingests three waypoints and exports seq-ordered summary."""
    proc = run_ingest(tmp_paths["db"], Path("/app/data/sample-alpha.mseq"), "alpha-01", "V1")
    assert proc.returncode == 0, proc.stderr
    conn = connect(tmp_paths["db"])
    assert conn.execute("SELECT COUNT(*) c FROM waypoints WHERE vehicle_id='V1'").fetchone()["c"] == 3
    conn.close()

    out = run_export(tmp_paths["db"], "V1", "alpha-01", tmp_paths["report"])
    assert out.returncode == 0, out.stderr
    rep = json.loads(tmp_paths["report"].read_text(encoding="utf-8"))
    assert rep["exported_at_unix"] == EPOCH_BASE + 2
    wps = rep["waypoints"]
    assert [w["seq"] for w in wps] == [0, 1, 2]
    assert wps[0]["alt_meters"] == alt_relative(170500, HOME_V1)
    assert wps[2]["alt_meters"] == alt_global(180000)


def test_beta_idempotent_replay(tmp_paths: dict[str, Path]) -> None:
    """Replaying a committed upload must not change row counts."""
    batch = FIXTURES / "beta_clean.mseq"
    assert run_ingest(tmp_paths["db"], batch, "beta-02", "V2").returncode == 0
    conn = connect(tmp_paths["db"])
    before = conn.execute("SELECT COUNT(*) c FROM waypoints").fetchone()["c"]
    rows_before = conn.execute(
        "SELECT seq, lat_e7, alt_mm FROM waypoints ORDER BY seq"
    ).fetchall()
    conn.close()
    assert run_ingest(tmp_paths["db"], FIXTURES / "beta_replay.mseq", "beta-02", "V2").returncode == 0
    conn = connect(tmp_paths["db"])
    assert conn.execute("SELECT COUNT(*) c FROM waypoints").fetchone()["c"] == before
    rows_after = conn.execute(
        "SELECT seq, lat_e7, alt_mm FROM waypoints ORDER BY seq"
    ).fetchall()
    conn.close()
    assert rows_before == rows_after


def test_gamma_corrupt_upload_rolls_back(tmp_paths: dict[str, Path]) -> None:
    """Invalid CRC mid-log leaves no rows for that upload_id but schema tables still exist."""
    proc = run_ingest(tmp_paths["db"], FIXTURES / "gamma_corrupt.mseq", "gamma-bad", "V1")
    assert proc.returncode != 0
    conn = connect(tmp_paths["db"])
    tables = {
        row["name"]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    assert "waypoints" in tables
    assert "upload_commits" in tables
    assert conn.execute("SELECT COUNT(*) c FROM waypoints").fetchone()["c"] == 0
    assert (
        conn.execute("SELECT COUNT(*) c FROM upload_commits WHERE upload_id='gamma-bad'").fetchone()["c"]
        == 0
    )
    conn.close()


def test_delta_distance_uses_seq_order(tmp_paths: dict[str, Path]) -> None:
    """total_distance_m follows ascending seq, not file order."""
    assert run_ingest(tmp_paths["db"], FIXTURES / "delta_out_of_order.mseq", "delta-03", "V1").returncode == 0
    out = run_export(tmp_paths["db"], "V1", "delta-03", tmp_paths["report"])
    assert out.returncode == 0, out.stderr
    rep = json.loads(tmp_paths["report"].read_text(encoding="utf-8"))
    wps = rep["waypoints"]
    assert [w["seq"] for w in wps] == [0, 1, 2]
    expected = 0.0
    for a, b in zip(wps, wps[1:]):
        expected += haversine_m(a["lat_deg"], a["lon_deg"], b["lat_deg"], b["lon_deg"])
    assert rep["total_distance_m"] == round(expected, 3)


def test_partial_fix_canary_export_matches_mission_expect(tmp_paths: dict[str, Path]) -> None:
    """Export must match independent recompute including three-decimal rounding."""
    assert run_ingest(tmp_paths["db"], FIXTURES / "delta_out_of_order.mseq", "delta-03", "V1").returncode == 0
    out = run_export(tmp_paths["db"], "V1", "delta-03", tmp_paths["report"])
    assert out.returncode == 0, out.stderr
    rep = json.loads(tmp_paths["report"].read_text(encoding="utf-8"))
    assert rep == expected_export(tmp_paths["db"], "V1", "delta-03", epoch_base=EPOCH_BASE)


def test_echo_same_seq_different_uploads(tmp_paths: dict[str, Path]) -> None:
    """Same seq index in two uploads must not collide."""
    assert run_ingest(tmp_paths["db"], FIXTURES / "echo_upload_a.mseq", "echo-a", "V1").returncode == 0
    assert run_ingest(tmp_paths["db"], FIXTURES / "echo_upload_b.mseq", "echo-b", "V1").returncode == 0
    conn = connect(tmp_paths["db"])
    assert conn.execute("SELECT COUNT(*) c FROM waypoints WHERE vehicle_id='V1'").fetchone()["c"] == 2
    lat_a = conn.execute(
        "SELECT lat_e7 FROM waypoints WHERE upload_id='echo-a'"
    ).fetchone()["lat_e7"]
    lat_b = conn.execute(
        "SELECT lat_e7 FROM waypoints WHERE upload_id='echo-b'"
    ).fetchone()["lat_e7"]
    conn.close()
    assert lat_a != lat_b


def test_relative_altitude_export_v2(tmp_paths: dict[str, Path]) -> None:
    """Frame 3 altitudes subtract home_alt_m for V2."""
    assert run_ingest(tmp_paths["db"], FIXTURES / "beta_clean.mseq", "beta-02", "V2").returncode == 0
    out = run_export(tmp_paths["db"], "V2", "beta-02", tmp_paths["report"])
    assert out.returncode == 0, out.stderr
    rep = json.loads(tmp_paths["report"].read_text(encoding="utf-8"))
    assert rep["waypoints"][0]["alt_meters"] == alt_relative(95000, HOME_V2)


def test_noise_resync_ingests(tmp_paths: dict[str, Path]) -> None:
    """Long arbitrary leading noise with partial 'M' bytes must still resync to MQ."""
    assert run_ingest(tmp_paths["db"], FIXTURES / "zeta_long_noise.mseq", "zeta-noise", "V1").returncode == 0
    conn = connect(tmp_paths["db"])
    assert conn.execute("SELECT COUNT(*) c FROM waypoints WHERE upload_id='zeta-noise'").fetchone()["c"] == 3
    conn.close()


def test_hotel_footer_expected_count_mismatch(tmp_paths: dict[str, Path]) -> None:
    """Footer expected_count must match parsed waypoint count; schema still initialized."""
    proc = run_ingest(tmp_paths["db"], FIXTURES / "hotel_footer_count.mseq", "hotel-04", "V1")
    assert proc.returncode != 0
    conn = connect(tmp_paths["db"])
    assert "waypoints" in {
        r["name"] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    }
    assert conn.execute("SELECT COUNT(*) c FROM waypoints WHERE upload_id='hotel-04'").fetchone()["c"] == 0
    conn.close()


def test_footer_upload_id_mismatch(tmp_paths: dict[str, Path]) -> None:
    """Footer upload_id must match the CLI --upload-id passed to ingest."""
    proc = run_ingest(tmp_paths["db"], FIXTURES / "india_upload_id.mseq", "india-04", "V1")
    assert proc.returncode != 0
    conn = connect(tmp_paths["db"])
    assert conn.execute("SELECT COUNT(*) c FROM waypoints WHERE upload_id='india-04'").fetchone()["c"] == 0
    assert (
        conn.execute("SELECT COUNT(*) c FROM upload_commits WHERE upload_id='india-04'").fetchone()["c"]
        == 0
    )
    conn.close()


def test_foxtrot_crc_omits_extra_when_v2_flag_clear(tmp_paths: dict[str, Path]) -> None:
    """Waypoints with flags bit0 clear must ingest using CRC input without 0x4D extra byte."""
    proc = run_ingest(tmp_paths["db"], FIXTURES / "foxtrot_flags_zero.mseq", "foxtrot-00", "V1")
    assert proc.returncode == 0, proc.stderr
    conn = connect(tmp_paths["db"])
    rows = conn.execute(
        "SELECT seq, flags, frame, alt_mm FROM waypoints WHERE upload_id='foxtrot-00' ORDER BY seq"
    ).fetchall()
    conn.close()
    assert len(rows) == 2
    assert all(r["flags"] == 0 for r in rows)
    assert rows[0]["alt_mm"] == 165000
    out = run_export(tmp_paths["db"], "V1", "foxtrot-00", tmp_paths["report"])
    assert out.returncode == 0, out.stderr
    rep = json.loads(tmp_paths["report"].read_text(encoding="utf-8"))
    assert rep["waypoints"][0]["alt_meters"] == alt_relative(165000, HOME_V1)
    assert rep["waypoints"][1]["alt_meters"] == alt_global(168000)


def test_juliet_midstream_noise_resync(tmp_paths: dict[str, Path]) -> None:
    """Garbage bytes between waypoint records must resync and ingest all waypoints."""
    proc = run_ingest(tmp_paths["db"], FIXTURES / "juliet_midstream_noise.mseq", "juliet-05", "V1")
    assert proc.returncode == 0, proc.stderr
    conn = connect(tmp_paths["db"])
    assert conn.execute("SELECT COUNT(*) c FROM waypoints WHERE upload_id='juliet-05'").fetchone()["c"] == 3
    conn.close()


def test_kilo_cross_batch_export_isolated(tmp_paths: dict[str, Path]) -> None:
    """A second upload on the same database must export only its own distance rollup."""
    assert run_ingest(tmp_paths["db"], Path("/app/data/sample-alpha.mseq"), "alpha-01", "V1").returncode == 0
    assert run_ingest(tmp_paths["db"], FIXTURES / "kilo_cross_batch.mseq", "kilo-06", "V1").returncode == 0
    out = run_export(tmp_paths["db"], "V1", "kilo-06", tmp_paths["report"])
    assert out.returncode == 0, out.stderr
    rep = json.loads(tmp_paths["report"].read_text(encoding="utf-8"))
    assert rep == expected_export(tmp_paths["db"], "V1", "kilo-06", epoch_base=EPOCH_BASE)
    assert rep["total_distance_m"] > 0.0
    assert len(rep["waypoints"]) == 2


def test_lima_single_waypoint_zero_distance(tmp_paths: dict[str, Path]) -> None:
    """Single-waypoint uploads export zero total_distance_m and epoch from max seq."""
    assert run_ingest(tmp_paths["db"], FIXTURES / "lima_single_wp.mseq", "lima-07", "V1").returncode == 0
    out = run_export(tmp_paths["db"], "V1", "lima-07", tmp_paths["report"])
    assert out.returncode == 0, out.stderr
    rep = json.loads(tmp_paths["report"].read_text(encoding="utf-8"))
    assert rep["total_distance_m"] == 0.0
    assert rep["exported_at_unix"] == EPOCH_BASE + 7
    assert rep == expected_export(tmp_paths["db"], "V1", "lima-07", epoch_base=EPOCH_BASE)


def test_mike_idempotent_replay_preserves_first_payload(tmp_paths: dict[str, Path]) -> None:
    """Committed upload_id replay must ignore a later log with different waypoint fields."""
    assert run_ingest(tmp_paths["db"], FIXTURES / "beta_clean.mseq", "beta-02", "V2").returncode == 0
    conn = connect(tmp_paths["db"])
    before = conn.execute(
        "SELECT seq, alt_mm FROM waypoints WHERE upload_id='beta-02' ORDER BY seq"
    ).fetchall()
    conn.close()
    assert run_ingest(
        tmp_paths["db"], FIXTURES / "mike_replay_mutated.mseq", "beta-02", "V2"
    ).returncode == 0
    conn = connect(tmp_paths["db"])
    after = conn.execute(
        "SELECT seq, alt_mm FROM waypoints WHERE upload_id='beta-02' ORDER BY seq"
    ).fetchall()
    assert conn.execute("SELECT COUNT(*) c FROM waypoints").fetchone()["c"] == 2
    conn.close()
    assert before == after
    assert after[0]["alt_mm"] == 95000


def test_november_distance_round3_after_sum_not_per_leg(tmp_paths: dict[str, Path]) -> None:
    """total_distance_m rounds the summed haversine path, not each leg before summing."""
    assert run_ingest(
        tmp_paths["db"], FIXTURES / "november_rounding_trap.mseq", "november-08", "V1"
    ).returncode == 0
    out = run_export(tmp_paths["db"], "V1", "november-08", tmp_paths["report"])
    assert out.returncode == 0, out.stderr
    rep = json.loads(tmp_paths["report"].read_text(encoding="utf-8"))
    assert rep == expected_export(tmp_paths["db"], "V1", "november-08", epoch_base=EPOCH_BASE)


def test_oscar_mixed_frame_altitude_export(tmp_paths: dict[str, Path]) -> None:
    """Frame 3 subtracts home_alt_m while frame 0 keeps absolute altitude in one upload."""
    assert run_ingest(tmp_paths["db"], FIXTURES / "oscar_mixed_frames.mseq", "oscar-09", "V2").returncode == 0
    out = run_export(tmp_paths["db"], "V2", "oscar-09", tmp_paths["report"])
    assert out.returncode == 0, out.stderr
    rep = json.loads(tmp_paths["report"].read_text(encoding="utf-8"))
    assert rep["waypoints"][0]["alt_meters"] == alt_relative(95000, HOME_V2)
    assert rep["waypoints"][1]["alt_meters"] == alt_global(100000)
    assert rep == expected_export(tmp_paths["db"], "V2", "oscar-09", epoch_base=EPOCH_BASE)


def test_partial_fix_fails_per_leg_distance_rounding(tmp_paths: dict[str, Path]) -> None:
    """CRC/altitude/sort fixes alone still fail when distance rounds each leg before sum."""
    assert run_ingest(
        tmp_paths["db"], FIXTURES / "november_rounding_trap.mseq", "november-08", "V1"
    ).returncode == 0
    out = run_export(tmp_paths["db"], "V1", "november-08", tmp_paths["report"])
    assert out.returncode == 0, out.stderr
    rep = json.loads(tmp_paths["report"].read_text(encoding="utf-8"))
    expect = expected_export(tmp_paths["db"], "V1", "november-08", epoch_base=EPOCH_BASE)
    assert rep["waypoints"] == expect["waypoints"]
    assert rep["total_distance_m"] == expect["total_distance_m"]


def test_papa_duplicate_seq_aborts_ingest(tmp_paths: dict[str, Path]) -> None:
    """Duplicate seq within one upload must fail ingest with no persisted rows."""
    proc = run_ingest(tmp_paths["db"], FIXTURES / "papa_dup_seq.mseq", "papa-10", "V1")
    assert proc.returncode != 0
    conn = connect(tmp_paths["db"])
    assert conn.execute("SELECT COUNT(*) c FROM waypoints WHERE upload_id='papa-10'").fetchone()["c"] == 0
    assert (
        conn.execute("SELECT COUNT(*) c FROM upload_commits WHERE upload_id='papa-10'").fetchone()["c"]
        == 0
    )
    conn.close()


def test_quebec_bad_waypoint_crc_aborts_ingest(tmp_paths: dict[str, Path]) -> None:
    """Valid MQ waypoint with bad CRC must abort upload without persisting rows."""
    proc = run_ingest(tmp_paths["db"], FIXTURES / "quebec_bad_wp_crc.mseq", "quebec-11", "V1")
    assert proc.returncode != 0
    conn = connect(tmp_paths["db"])
    assert conn.execute("SELECT COUNT(*) c FROM waypoints WHERE upload_id='quebec-11'").fetchone()["c"] == 0
    assert (
        conn.execute("SELECT COUNT(*) c FROM upload_commits WHERE upload_id='quebec-11'").fetchone()["c"]
        == 0
    )
    conn.close()


def test_partial_fix_fails_duplicate_seq_collapses_rows(tmp_paths: dict[str, Path]) -> None:
    """CRC/store fixes that collapse duplicate seq to one row must not pass as success."""
    proc = run_ingest(tmp_paths["db"], FIXTURES / "papa_dup_seq.mseq", "papa-10", "V1")
    conn = connect(tmp_paths["db"])
    row_count = conn.execute(
        "SELECT COUNT(*) c FROM waypoints WHERE upload_id='papa-10'"
    ).fetchone()["c"]
    conn.close()
    if proc.returncode == 0:
        assert row_count == 2


def test_partial_fix_fails_v2_export_vehicle_home(tmp_paths: dict[str, Path]) -> None:
    """Export must use the requested vehicle home_alt_m, not another profile entry."""
    assert run_ingest(tmp_paths["db"], FIXTURES / "beta_clean.mseq", "beta-02", "V2").returncode == 0
    out = run_export(tmp_paths["db"], "V2", "beta-02", tmp_paths["report"])
    assert out.returncode == 0, out.stderr
    rep = json.loads(tmp_paths["report"].read_text(encoding="utf-8"))
    expect = expected_export(tmp_paths["db"], "V2", "beta-02", epoch_base=EPOCH_BASE)
    assert rep["waypoints"][0]["alt_meters"] == expect["waypoints"][0]["alt_meters"]
    assert rep == expect


def test_sierra_same_upload_id_on_different_vehicles(tmp_paths: dict[str, Path]) -> None:
    """upload_id idempotency is scoped per vehicle_id; same upload_id on V2 must ingest."""
    assert run_ingest(tmp_paths["db"], FIXTURES / "sierra_v1.mseq", "sierra-12", "V1").returncode == 0
    proc = run_ingest(tmp_paths["db"], FIXTURES / "sierra_v2.mseq", "sierra-12", "V2")
    assert proc.returncode == 0, proc.stderr
    conn = connect(tmp_paths["db"])
    v2 = conn.execute(
        "SELECT lat_e7, alt_mm FROM waypoints WHERE vehicle_id='V2' AND upload_id='sierra-12'"
    ).fetchone()
    conn.close()
    assert v2 is not None
    assert v2["lat_e7"] == 600_100_000
    assert v2["alt_mm"] == 110_000


def test_romeo_waypoint_body_upload_id_mismatch_aborts(tmp_paths: dict[str, Path]) -> None:
    """Waypoint record upload_id must match --upload-id; mismatch aborts with no rows."""
    proc = run_ingest(tmp_paths["db"], FIXTURES / "romeo_body_upload_id.mseq", "romeo-12", "V1")
    assert proc.returncode != 0
    conn = connect(tmp_paths["db"])
    assert conn.execute("SELECT COUNT(*) c FROM waypoints WHERE upload_id='romeo-12'").fetchone()["c"] == 0
    assert (
        conn.execute("SELECT COUNT(*) c FROM upload_commits WHERE upload_id='romeo-12'").fetchone()["c"]
        == 0
    )
    conn.close()


def test_kilo_nonadjacent_duplicate_seq_aborts_ingest(tmp_paths: dict[str, Path]) -> None:
    """Duplicate seq separated by another waypoint must abort ingest with rollback."""
    proc = run_ingest(
        tmp_paths["db"], FIXTURES_HIDDEN / "kilo_nonadjacent_dup.mseq", "kilo-31", "V1"
    )
    assert proc.returncode != 0
    conn = connect(tmp_paths["db"])
    assert conn.execute("SELECT COUNT(*) c FROM waypoints WHERE upload_id='kilo-31'").fetchone()["c"] == 0
    assert (
        conn.execute("SELECT COUNT(*) c FROM upload_commits WHERE upload_id='kilo-31'").fetchone()["c"]
        == 0
    )
    conn.close()


def test_partial_fix_fails_nonadjacent_dup_replace_succeeds(tmp_paths: dict[str, Path]) -> None:
    """Adjacent-only duplicate checks must not accept file-order seq 0,1,0 with silent REPLACE."""
    proc = run_ingest(
        tmp_paths["db"], FIXTURES_HIDDEN / "kilo_nonadjacent_dup.mseq", "kilo-31", "V1"
    )
    conn = connect(tmp_paths["db"])
    row_count = conn.execute(
        "SELECT COUNT(*) c FROM waypoints WHERE upload_id='kilo-31'"
    ).fetchone()["c"]
    row0 = conn.execute(
        "SELECT lat_e7, lon_e7, alt_mm FROM waypoints WHERE upload_id='kilo-31' AND seq=0"
    ).fetchone()
    conn.close()
    if proc.returncode == 0:
        assert row_count == 2
        assert row0 is not None
        assert row0["lat_e7"] == 377_751_000
        assert row0["lon_e7"] == -1_224_195_000
        assert row0["alt_mm"] == 185_000


def test_zulu_mid_body_upload_id_mismatch_aborts_clean(tmp_paths: dict[str, Path]) -> None:
    """Mid-upload waypoint body upload_id mismatch must abort with zero persisted rows."""
    proc = run_ingest(
        tmp_paths["db"], FIXTURES_HIDDEN / "zulu_mid_body_upload_id.mseq", "zulu-32", "V1"
    )
    assert proc.returncode != 0
    conn = connect(tmp_paths["db"])
    assert conn.execute("SELECT COUNT(*) c FROM waypoints WHERE upload_id='zulu-32'").fetchone()["c"] == 0
    assert (
        conn.execute("SELECT COUNT(*) c FROM upload_commits WHERE upload_id='zulu-32'").fetchone()["c"]
        == 0
    )
    conn.close()


def test_partial_fix_fails_mid_mismatch_leaves_stale_rows(tmp_paths: dict[str, Path]) -> None:
    """Ingest without transaction rollback must not leave rows after a later body upload_id mismatch."""
    proc = run_ingest(
        tmp_paths["db"], FIXTURES_HIDDEN / "zulu_mid_body_upload_id.mseq", "zulu-32", "V1"
    )
    conn = connect(tmp_paths["db"])
    row_count = conn.execute(
        "SELECT COUNT(*) c FROM waypoints WHERE upload_id='zulu-32'"
    ).fetchone()["c"]
    commit_count = conn.execute(
        "SELECT COUNT(*) c FROM upload_commits WHERE upload_id='zulu-32'"
    ).fetchone()["c"]
    conn.close()
    assert proc.returncode != 0
    if row_count >= 1:
        assert commit_count == 0


def test_tango_export_epoch_scoped_to_upload_not_vehicle(tmp_paths: dict[str, Path]) -> None:
    """exported_at_unix uses max seq within the exported upload, not vehicle-wide max seq."""
    assert run_ingest(tmp_paths["db"], Path("/app/data/sample-alpha.mseq"), "alpha-01", "V1").returncode == 0
    assert run_ingest(tmp_paths["db"], FIXTURES / "lima_single_wp.mseq", "lima-07", "V1").returncode == 0
    out = run_export(tmp_paths["db"], "V1", "alpha-01", tmp_paths["report"])
    assert out.returncode == 0, out.stderr
    rep = json.loads(tmp_paths["report"].read_text(encoding="utf-8"))
    expect = expected_export(tmp_paths["db"], "V1", "alpha-01", epoch_base=EPOCH_BASE)
    assert rep["exported_at_unix"] == EPOCH_BASE + 2
    assert rep["exported_at_unix"] != EPOCH_BASE + 7
    assert rep == expect


def test_uniform_negative_relative_altitude(tmp_paths: dict[str, Path]) -> None:
    """Frame 3 below home_alt_m exports negative alt_meters rounded to three decimals."""
    assert run_ingest(
        tmp_paths["db"], FIXTURES / "uniform_negative_alt.mseq", "uniform-13", "V1"
    ).returncode == 0
    out = run_export(tmp_paths["db"], "V1", "uniform-13", tmp_paths["report"])
    assert out.returncode == 0, out.stderr
    rep = json.loads(tmp_paths["report"].read_text(encoding="utf-8"))
    assert rep["waypoints"][0]["alt_meters"] == -70.5
    assert rep == expected_export(tmp_paths["db"], "V1", "uniform-13", epoch_base=EPOCH_BASE)
    assert rep["upload_qc_pass"] is False


def test_partial_fix_fails_vehicle_wide_export_epoch(tmp_paths: dict[str, Path]) -> None:
    """Idempotency/export fixes that leak vehicle-wide max seq fail alpha export after lima ingest."""
    assert run_ingest(tmp_paths["db"], Path("/app/data/sample-alpha.mseq"), "alpha-01", "V1").returncode == 0
    assert run_ingest(tmp_paths["db"], FIXTURES / "lima_single_wp.mseq", "lima-07", "V1").returncode == 0
    out = run_export(tmp_paths["db"], "V1", "alpha-01", tmp_paths["report"])
    assert out.returncode == 0, out.stderr
    rep = json.loads(tmp_paths["report"].read_text(encoding="utf-8"))
    expect = expected_export(tmp_paths["db"], "V1", "alpha-01", epoch_base=EPOCH_BASE)
    assert rep["exported_at_unix"] == expect["exported_at_unix"]


def test_partial_fix_fails_upload_id_only_idempotency(tmp_paths: dict[str, Path]) -> None:
    """Store fixes that key idempotency on upload_id alone must not block a second vehicle."""
    assert run_ingest(tmp_paths["db"], FIXTURES / "sierra_v1.mseq", "sierra-12", "V1").returncode == 0
    assert run_ingest(tmp_paths["db"], FIXTURES / "sierra_v2.mseq", "sierra-12", "V2").returncode == 0
    conn = connect(tmp_paths["db"])
    v2_count = conn.execute(
        "SELECT COUNT(*) c FROM waypoints WHERE vehicle_id='V2' AND upload_id='sierra-12'"
    ).fetchone()["c"]
    conn.close()
    assert v2_count == 1


def test_whiskey_out_of_order_file_order_ingests(tmp_paths: dict[str, Path]) -> None:
    """Physical file order may differ from ascending seq; export must sort by seq."""
    proc = run_ingest(tmp_paths["db"], FIXTURES / "whiskey.mseq", "whiskey-14", "V1")
    assert proc.returncode == 0, proc.stderr
    conn = connect(tmp_paths["db"])
    assert conn.execute("SELECT COUNT(*) c FROM waypoints WHERE upload_id='whiskey-14'").fetchone()["c"] == 4
    conn.close()
    out = run_export(tmp_paths["db"], "V1", "whiskey-14", tmp_paths["report"])
    assert out.returncode == 0, out.stderr
    rep = json.loads(tmp_paths["report"].read_text(encoding="utf-8"))
    expect = expected_export(tmp_paths["db"], "V1", "whiskey-14", epoch_base=EPOCH_BASE)
    assert rep == expect
    assert [wp["seq"] for wp in rep["waypoints"]] == [0, 1, 2, 3]


def test_victor_cross_vehicle_export_epoch(tmp_paths: dict[str, Path]) -> None:
    """exported_at_unix for one upload must ignore max seq rows on other vehicles."""
    assert run_ingest(tmp_paths["db"], Path("/app/data/sample-alpha.mseq"), "alpha-01", "V1").returncode == 0
    assert run_ingest(tmp_paths["db"], FIXTURES / "beta_clean.mseq", "beta-02", "V2").returncode == 0
    out = run_export(tmp_paths["db"], "V2", "beta-02", tmp_paths["report"])
    assert out.returncode == 0, out.stderr
    rep = json.loads(tmp_paths["report"].read_text(encoding="utf-8"))
    expect = expected_export(tmp_paths["db"], "V2", "beta-02", epoch_base=EPOCH_BASE)
    assert rep["exported_at_unix"] == EPOCH_BASE + 1
    assert rep["exported_at_unix"] != EPOCH_BASE + 2
    assert rep == expect


def test_partial_fix_fails_global_export_epoch(tmp_paths: dict[str, Path]) -> None:
    """Export epoch fixes scoped only to vehicle still fail when global max seq leaks across vehicles."""
    assert run_ingest(tmp_paths["db"], Path("/app/data/sample-alpha.mseq"), "alpha-01", "V1").returncode == 0
    assert run_ingest(tmp_paths["db"], FIXTURES / "beta_clean.mseq", "beta-02", "V2").returncode == 0
    out = run_export(tmp_paths["db"], "V2", "beta-02", tmp_paths["report"])
    assert out.returncode == 0, out.stderr
    rep = json.loads(tmp_paths["report"].read_text(encoding="utf-8"))
    expect = expected_export(tmp_paths["db"], "V2", "beta-02", epoch_base=EPOCH_BASE)
    assert rep["exported_at_unix"] == expect["exported_at_unix"]


def test_partial_fix_fails_rejects_non_monotonic_file_order(tmp_paths: dict[str, Path]) -> None:
    """Ingest must accept distinct seq values in non-monotonic file order; only duplicates abort."""
    proc = run_ingest(tmp_paths["db"], FIXTURES / "whiskey.mseq", "whiskey-14", "V1")
    assert proc.returncode == 0, proc.stderr
    out = run_export(tmp_paths["db"], "V1", "whiskey-14", tmp_paths["report"])
    assert out.returncode == 0, out.stderr
    rep = json.loads(tmp_paths["report"].read_text(encoding="utf-8"))
    assert rep == expected_export(tmp_paths["db"], "V1", "whiskey-14", epoch_base=EPOCH_BASE)


def test_partial_fix_fails_mike_replay_mutates_payload(tmp_paths: dict[str, Path]) -> None:
    """Idempotency fixes that still apply replayed waypoint bytes fail alt preservation."""
    assert run_ingest(tmp_paths["db"], FIXTURES / "beta_clean.mseq", "beta-02", "V2").returncode == 0
    assert run_ingest(
        tmp_paths["db"], FIXTURES / "mike_replay_mutated.mseq", "beta-02", "V2"
    ).returncode == 0
    conn = connect(tmp_paths["db"])
    alt = conn.execute(
        "SELECT alt_mm FROM waypoints WHERE vehicle_id='V2' AND upload_id='beta-02' ORDER BY seq"
    ).fetchone()["alt_mm"]
    conn.close()
    assert alt == 95000


def test_echo_export_isolated_after_dual_upload(tmp_paths: dict[str, Path]) -> None:
    """Export for echo-a must reflect echo-a coordinates, not a colliding upload on the same seq."""
    assert run_ingest(tmp_paths["db"], FIXTURES / "echo_upload_a.mseq", "echo-a", "V1").returncode == 0
    assert run_ingest(tmp_paths["db"], FIXTURES / "echo_upload_b.mseq", "echo-b", "V1").returncode == 0
    out = run_export(tmp_paths["db"], "V1", "echo-a", tmp_paths["report"])
    assert out.returncode == 0, out.stderr
    rep = json.loads(tmp_paths["report"].read_text(encoding="utf-8"))
    expect = expected_export(tmp_paths["db"], "V1", "echo-a", epoch_base=EPOCH_BASE)
    assert rep == expect
    assert rep["waypoints"][0]["lat_deg"] == pytest.approx(40.0)


def test_partial_fix_fails_echo_export_contamination(tmp_paths: dict[str, Path]) -> None:
    """Store PK fixes without export isolation still fail echo-a distance and lat after echo-b ingest."""
    assert run_ingest(tmp_paths["db"], FIXTURES / "echo_upload_a.mseq", "echo-a", "V1").returncode == 0
    assert run_ingest(tmp_paths["db"], FIXTURES / "echo_upload_b.mseq", "echo-b", "V1").returncode == 0
    out = run_export(tmp_paths["db"], "V1", "echo-a", tmp_paths["report"])
    assert out.returncode == 0, out.stderr
    rep = json.loads(tmp_paths["report"].read_text(encoding="utf-8"))
    expect = expected_export(tmp_paths["db"], "V1", "echo-a", epoch_base=EPOCH_BASE)
    assert rep["total_distance_m"] == expect["total_distance_m"]
    assert rep["waypoints"] == expect["waypoints"]


def test_zulu_combined_db_export_canary(tmp_paths: dict[str, Path]) -> None:
    """One database with multiple uploads/vehicles exports each upload independently."""
    db = tmp_paths["db"]
    assert run_ingest(db, Path("/app/data/sample-alpha.mseq"), "alpha-01", "V1").returncode == 0
    assert run_ingest(db, FIXTURES / "whiskey.mseq", "whiskey-14", "V1").returncode == 0
    assert run_ingest(db, FIXTURES / "beta_clean.mseq", "beta-02", "V2").returncode == 0
    assert run_ingest(db, FIXTURES / "echo_upload_a.mseq", "echo-a", "V1").returncode == 0
    assert run_ingest(db, FIXTURES / "echo_upload_b.mseq", "echo-b", "V1").returncode == 0
    cases = [
        ("V1", "alpha-01", tmp_paths["report"].with_name("alpha.json")),
        ("V1", "whiskey-14", tmp_paths["report"].with_name("whiskey.json")),
        ("V2", "beta-02", tmp_paths["report"].with_name("beta.json")),
        ("V1", "echo-a", tmp_paths["report"].with_name("echo_a.json")),
        ("V1", "echo-b", tmp_paths["report"].with_name("echo_b.json")),
    ]
    for vehicle, upload_id, out_path in cases:
        proc = run_export(db, vehicle, upload_id, out_path)
        assert proc.returncode == 0, proc.stderr
        rep = json.loads(out_path.read_text(encoding="utf-8"))
        assert rep == expected_export(db, vehicle, upload_id, epoch_base=EPOCH_BASE)


def test_tango_hold_skips_inbound_leg_distance(tmp_paths: dict[str, Path]) -> None:
    """Hold flag 0x02 on a waypoint skips the haversine leg into that destination."""
    assert run_ingest(
        tmp_paths["db"], FIXTURES_HIDDEN / "tango_hold.mseq", "tango-15", "V1"
    ).returncode == 0
    out = run_export(tmp_paths["db"], "V1", "tango-15", tmp_paths["report"])
    assert out.returncode == 0, out.stderr
    rep = json.loads(tmp_paths["report"].read_text(encoding="utf-8"))
    assert rep == expected_export(tmp_paths["db"], "V1", "tango-15", epoch_base=EPOCH_BASE)
    assert len(rep["waypoints"]) == 3
    assert rep["total_distance_m"] > 0


def test_yankee_empty_upload_export(tmp_paths: dict[str, Path]) -> None:
    """Zero-waypoint committed upload exports empty waypoints and epoch base offset zero."""
    assert run_ingest(
        tmp_paths["db"], FIXTURES_HIDDEN / "yankee_empty.mseq", "yankee-16", "V1"
    ).returncode == 0
    out = run_export(tmp_paths["db"], "V1", "yankee-16", tmp_paths["report"])
    assert out.returncode == 0, out.stderr
    rep = json.loads(tmp_paths["report"].read_text(encoding="utf-8"))
    expect = expected_export(tmp_paths["db"], "V1", "yankee-16", epoch_base=EPOCH_BASE)
    assert rep == expect
    assert rep["waypoints"] == []
    assert rep["total_distance_m"] == 0.0
    assert rep["exported_at_unix"] == EPOCH_BASE


def test_xray_sparse_seq_distance_order(tmp_paths: dict[str, Path]) -> None:
    """Distance rollup follows ascending seq, not file order, for sparse seq values."""
    assert run_ingest(
        tmp_paths["db"], FIXTURES_HIDDEN / "xray_sparse_seq.mseq", "xray-17", "V1"
    ).returncode == 0
    out = run_export(tmp_paths["db"], "V1", "xray-17", tmp_paths["report"])
    assert out.returncode == 0, out.stderr
    rep = json.loads(tmp_paths["report"].read_text(encoding="utf-8"))
    assert rep == expected_export(tmp_paths["db"], "V1", "xray-17", epoch_base=EPOCH_BASE)
    assert [wp["seq"] for wp in rep["waypoints"]] == [2, 7, 15]


def test_partial_fix_fails_hold_flag_skips_leg(tmp_paths: dict[str, Path]) -> None:
    """Export distance fixes without hold-leg skip still fail tango hidden rollup."""
    assert run_ingest(
        tmp_paths["db"], FIXTURES_HIDDEN / "tango_hold.mseq", "tango-15", "V1"
    ).returncode == 0
    out = run_export(tmp_paths["db"], "V1", "tango-15", tmp_paths["report"])
    assert out.returncode == 0, out.stderr
    rep = json.loads(tmp_paths["report"].read_text(encoding="utf-8"))
    expect = expected_export(tmp_paths["db"], "V1", "tango-15", epoch_base=EPOCH_BASE)
    assert rep["total_distance_m"] == expect["total_distance_m"]


def test_partial_fix_fails_empty_upload_epoch_after_prior_ingest(tmp_paths: dict[str, Path]) -> None:
    """Upload-scoped epoch fixes that leak global max seq fail empty yankee export."""
    assert run_ingest(tmp_paths["db"], FIXTURES / "beta_clean.mseq", "beta-02", "V2").returncode == 0
    assert run_ingest(
        tmp_paths["db"], FIXTURES_HIDDEN / "yankee_empty.mseq", "yankee-16", "V1"
    ).returncode == 0
    out = run_export(tmp_paths["db"], "V1", "yankee-16", tmp_paths["report"])
    assert out.returncode == 0, out.stderr
    rep = json.loads(tmp_paths["report"].read_text(encoding="utf-8"))
    expect = expected_export(tmp_paths["db"], "V1", "yankee-16", epoch_base=EPOCH_BASE)
    assert rep["exported_at_unix"] == expect["exported_at_unix"]
    assert rep["exported_at_unix"] == EPOCH_BASE


def test_victor_suppress_omits_export_but_counts_distance(tmp_paths: dict[str, Path]) -> None:
    """Flag 0x04 drops waypoint from export array but distance still crosses suppressed leg."""
    assert run_ingest(
        tmp_paths["db"], FIXTURES_HIDDEN / "victor_suppress.mseq", "victor-18", "V1"
    ).returncode == 0
    out = run_export(tmp_paths["db"], "V1", "victor-18", tmp_paths["report"])
    assert out.returncode == 0, out.stderr
    rep = json.loads(tmp_paths["report"].read_text(encoding="utf-8"))
    expect = expected_export(tmp_paths["db"], "V1", "victor-18", epoch_base=EPOCH_BASE)
    assert rep == expect
    assert [wp["seq"] for wp in rep["waypoints"]] == [0, 2]
    assert rep["total_distance_m"] > 1_000_000.0


def test_lima_source_hold_still_counts_outbound_leg(tmp_paths: dict[str, Path]) -> None:
    """Hold on the source waypoint must not skip the leg into the next destination."""
    assert run_ingest(
        tmp_paths["db"], FIXTURES_HIDDEN / "lima_source_hold.mseq", "lima-19", "V1"
    ).returncode == 0
    out = run_export(tmp_paths["db"], "V1", "lima-19", tmp_paths["report"])
    assert out.returncode == 0, out.stderr
    rep = json.loads(tmp_paths["report"].read_text(encoding="utf-8"))
    expect = expected_export(tmp_paths["db"], "V1", "lima-19", epoch_base=EPOCH_BASE)
    assert rep == expect
    assert rep["total_distance_m"] > 200_000.0


def test_papa_frame10_absolute_altitude(tmp_paths: dict[str, Path]) -> None:
    """Frame 10 altitudes are absolute MSL meters, not relative to home."""
    assert run_ingest(
        tmp_paths["db"], FIXTURES_HIDDEN / "papa_frame10.mseq", "papa-20", "V1"
    ).returncode == 0
    out = run_export(tmp_paths["db"], "V1", "papa-20", tmp_paths["report"])
    assert out.returncode == 0, out.stderr
    rep = json.loads(tmp_paths["report"].read_text(encoding="utf-8"))
    expect = expected_export(tmp_paths["db"], "V1", "papa-20", epoch_base=EPOCH_BASE)
    assert rep == expect
    assert rep["waypoints"][0]["alt_meters"] == 150.5


def test_partial_fix_fails_suppress_filters_distance(tmp_paths: dict[str, Path]) -> None:
    """Export array fixes without suppressed rows in distance rollup fail victor hidden."""
    assert run_ingest(
        tmp_paths["db"], FIXTURES_HIDDEN / "victor_suppress.mseq", "victor-18", "V1"
    ).returncode == 0
    out = run_export(tmp_paths["db"], "V1", "victor-18", tmp_paths["report"])
    assert out.returncode == 0, out.stderr
    rep = json.loads(tmp_paths["report"].read_text(encoding="utf-8"))
    expect = expected_export(tmp_paths["db"], "V1", "victor-18", epoch_base=EPOCH_BASE)
    assert rep["total_distance_m"] == expect["total_distance_m"]
    assert len(rep["waypoints"]) == len(expect["waypoints"])


def test_partial_fix_fails_source_hold_skip(tmp_paths: dict[str, Path]) -> None:
    """Hold-leg fixes that skip when the source has 0x02 still fail lima hidden rollup."""
    assert run_ingest(
        tmp_paths["db"], FIXTURES_HIDDEN / "lima_source_hold.mseq", "lima-19", "V1"
    ).returncode == 0
    out = run_export(tmp_paths["db"], "V1", "lima-19", tmp_paths["report"])
    assert out.returncode == 0, out.stderr
    rep = json.loads(tmp_paths["report"].read_text(encoding="utf-8"))
    expect = expected_export(tmp_paths["db"], "V1", "lima-19", epoch_base=EPOCH_BASE)
    assert rep["total_distance_m"] == expect["total_distance_m"]


def test_partial_fix_fails_frame10_home_offset(tmp_paths: dict[str, Path]) -> None:
    """Relative-altitude fixes that add home to frame 10 still fail papa export alt."""
    assert run_ingest(
        tmp_paths["db"], FIXTURES_HIDDEN / "papa_frame10.mseq", "papa-20", "V1"
    ).returncode == 0
    out = run_export(tmp_paths["db"], "V1", "papa-20", tmp_paths["report"])
    assert out.returncode == 0, out.stderr
    rep = json.loads(tmp_paths["report"].read_text(encoding="utf-8"))
    expect = expected_export(tmp_paths["db"], "V1", "papa-20", epoch_base=EPOCH_BASE)
    assert rep["waypoints"][0]["alt_meters"] == expect["waypoints"][0]["alt_meters"]


def test_quebec_suppress_and_hold_export(tmp_paths: dict[str, Path]) -> None:
    """Suppress plus hold on one row omits export entry but still skips inbound leg distance."""
    assert run_ingest(
        tmp_paths["db"], FIXTURES_HIDDEN / "quebec_suppress_hold.mseq", "quebec-21", "V1"
    ).returncode == 0
    out = run_export(tmp_paths["db"], "V1", "quebec-21", tmp_paths["report"])
    assert out.returncode == 0, out.stderr
    rep = json.loads(tmp_paths["report"].read_text(encoding="utf-8"))
    expect = expected_export(tmp_paths["db"], "V1", "quebec-21", epoch_base=EPOCH_BASE)
    assert rep == expect
    assert [wp["seq"] for wp in rep["waypoints"]] == [0, 2]
    assert rep["total_distance_m"] > 1_000_000.0


def test_partial_fix_fails_suppress_hold_export_filtered_distance(tmp_paths: dict[str, Path]) -> None:
    """Suppress+hold fixes that walk export waypoints only fail quebec distance rollup."""
    assert run_ingest(
        tmp_paths["db"], FIXTURES_HIDDEN / "quebec_suppress_hold.mseq", "quebec-21", "V1"
    ).returncode == 0
    out = run_export(tmp_paths["db"], "V1", "quebec-21", tmp_paths["report"])
    assert out.returncode == 0, out.stderr
    rep = json.loads(tmp_paths["report"].read_text(encoding="utf-8"))
    expect = expected_export(tmp_paths["db"], "V1", "quebec-21", epoch_base=EPOCH_BASE)
    assert rep["total_distance_m"] == expect["total_distance_m"]
    assert rep["total_distance_m"] > 10_000.0


def test_bravo_suppress_middle_hold_dest_skips_last_leg(tmp_paths: dict[str, Path]) -> None:
    """Suppressed middle waypoint still participates in distance before hold on final dest."""
    assert run_ingest(
        tmp_paths["db"], FIXTURES_HIDDEN / "bravo_suppress_then_hold.mseq", "bravo-22", "V1"
    ).returncode == 0
    out = run_export(tmp_paths["db"], "V1", "bravo-22", tmp_paths["report"])
    assert out.returncode == 0, out.stderr
    rep = json.loads(tmp_paths["report"].read_text(encoding="utf-8"))
    expect = expected_export(tmp_paths["db"], "V1", "bravo-22", epoch_base=EPOCH_BASE)
    assert rep == expect
    assert [wp["seq"] for wp in rep["waypoints"]] == [0, 2]
    assert 100_000.0 < rep["total_distance_m"] < 200_000.0


def test_partial_fix_fails_bravo_export_only_distance(tmp_paths: dict[str, Path]) -> None:
    """Export-array distance that skips hold into suppressed middle fails bravo rollup."""
    assert run_ingest(
        tmp_paths["db"], FIXTURES_HIDDEN / "bravo_suppress_then_hold.mseq", "bravo-22", "V1"
    ).returncode == 0
    out = run_export(tmp_paths["db"], "V1", "bravo-22", tmp_paths["report"])
    assert out.returncode == 0, out.stderr
    rep = json.loads(tmp_paths["report"].read_text(encoding="utf-8"))
    expect = expected_export(tmp_paths["db"], "V1", "bravo-22", epoch_base=EPOCH_BASE)
    assert rep["total_distance_m"] == expect["total_distance_m"]


def test_sierra_v2_combined_flags_full_export(tmp_paths: dict[str, Path]) -> None:
    """V2 upload with frame-3 relative, suppress+hold middle, and frame-0 absolute tail."""
    assert run_ingest(
        tmp_paths["db"], FIXTURES_HIDDEN / "sierra_v2_suppress_hold.mseq", "sierra-23", "V2"
    ).returncode == 0
    out = run_export(tmp_paths["db"], "V2", "sierra-23", tmp_paths["report"])
    assert out.returncode == 0, out.stderr
    rep = json.loads(tmp_paths["report"].read_text(encoding="utf-8"))
    expect = expected_export(tmp_paths["db"], "V2", "sierra-23", epoch_base=EPOCH_BASE)
    assert rep == expect
    assert rep["waypoints"][0]["alt_meters"] == alt_relative(170_500, HOME_V2)
    assert rep["waypoints"][1]["alt_meters"] == alt_global(200_500)
    assert rep["total_distance_m"] > 1_000_000.0


def test_partial_fix_fails_sierra_v2_wrong_home(tmp_paths: dict[str, Path]) -> None:
    """V1 home hardcoding still fails sierra V2 suppress+hold export altitudes."""
    assert run_ingest(
        tmp_paths["db"], FIXTURES_HIDDEN / "sierra_v2_suppress_hold.mseq", "sierra-23", "V2"
    ).returncode == 0
    out = run_export(tmp_paths["db"], "V2", "sierra-23", tmp_paths["report"])
    assert out.returncode == 0, out.stderr
    rep = json.loads(tmp_paths["report"].read_text(encoding="utf-8"))
    expect = expected_export(tmp_paths["db"], "V2", "sierra-23", epoch_base=EPOCH_BASE)
    assert rep["waypoints"] == expect["waypoints"]


def test_uniform_rel_alt_qc_fail(tmp_paths: dict[str, Path]) -> None:
    """Frame-3 relative altitude above V1 max_rel_alt_m sets upload_qc_pass false."""
    assert run_ingest(
        tmp_paths["db"], FIXTURES_HIDDEN / "uniform_rel_alt_cap.mseq", "uniform-24", "V1"
    ).returncode == 0
    out = run_export(tmp_paths["db"], "V1", "uniform-24", tmp_paths["report"])
    assert out.returncode == 0, out.stderr
    rep = json.loads(tmp_paths["report"].read_text(encoding="utf-8"))
    expect = expected_export(tmp_paths["db"], "V1", "uniform-24", epoch_base=EPOCH_BASE)
    assert rep == expect
    assert rep["upload_qc_pass"] is False
    assert rep["waypoints"][0]["alt_meters"] == 65.0


def test_india_long_route_qc_fail(tmp_paths: dict[str, Path]) -> None:
    """Route length above V1 max_route_m sets upload_qc_pass false."""
    assert run_ingest(
        tmp_paths["db"], FIXTURES_HIDDEN / "india_long_route.mseq", "india-25", "V1"
    ).returncode == 0
    out = run_export(tmp_paths["db"], "V1", "india-25", tmp_paths["report"])
    assert out.returncode == 0, out.stderr
    rep = json.loads(tmp_paths["report"].read_text(encoding="utf-8"))
    expect = expected_export(tmp_paths["db"], "V1", "india-25", epoch_base=EPOCH_BASE)
    assert rep == expect
    assert rep["upload_qc_pass"] is False
    assert rep["total_distance_m"] > 8000.0


def test_partial_fix_fails_upload_qc_always_true(tmp_paths: dict[str, Path]) -> None:
    """Route distance rollup fixes alone still fail when upload_qc_pass ignores max_route_m."""
    assert run_ingest(
        tmp_paths["db"], FIXTURES_HIDDEN / "india_long_route.mseq", "india-25", "V1"
    ).returncode == 0
    out = run_export(tmp_paths["db"], "V1", "india-25", tmp_paths["report"])
    assert out.returncode == 0, out.stderr
    rep = json.loads(tmp_paths["report"].read_text(encoding="utf-8"))
    expect = expected_export(tmp_paths["db"], "V1", "india-25", epoch_base=EPOCH_BASE)
    assert rep["total_distance_m"] == expect["total_distance_m"]
    if rep["upload_qc_pass"] and not expect["upload_qc_pass"]:
        pytest.fail("partial fix: route distance matches but upload_qc_pass ignores max_route_m")


def test_partial_fix_fails_audit_hash_includes_epoch(tmp_paths: dict[str, Path]) -> None:
    """Rollup and QC fixes alone still fail when audit_hash includes exported_at_unix."""
    assert run_ingest(
        tmp_paths["db"], FIXTURES_HIDDEN / "romeo_hash_trap.mseq", "romeo-26", "V1"
    ).returncode == 0
    out = run_export(tmp_paths["db"], "V1", "romeo-26", tmp_paths["report"])
    assert out.returncode == 0, out.stderr
    rep = json.loads(tmp_paths["report"].read_text(encoding="utf-8"))
    expect = expected_export(tmp_paths["db"], "V1", "romeo-26", epoch_base=EPOCH_BASE)
    if rep["audit_hash"] != expect["audit_hash"]:
        assert rep["waypoints"] == expect["waypoints"]
        assert rep["total_distance_m"] == expect["total_distance_m"]
        assert rep["upload_qc_pass"] == expect["upload_qc_pass"]
        pytest.fail("partial fix: rollups and QC match but audit_hash still wrong")


def test_delta_hidden_negative_rel_qc_fail(tmp_paths: dict[str, Path]) -> None:
    """Hidden frame-3 relative altitude below -max_rel_alt_m fails upload_qc_pass."""
    assert run_ingest(
        tmp_paths["db"], FIXTURES_HIDDEN / "delta_negative_rel_band.mseq", "delta-27", "V1"
    ).returncode == 0
    out = run_export(tmp_paths["db"], "V1", "delta-27", tmp_paths["report"])
    assert out.returncode == 0, out.stderr
    rep = json.loads(tmp_paths["report"].read_text(encoding="utf-8"))
    expect = expected_export(tmp_paths["db"], "V1", "delta-27", epoch_base=EPOCH_BASE)
    assert rep == expect
    assert rep["upload_qc_pass"] is False
    assert rep["waypoints"][0]["alt_meters"] == -65.0


def test_hotel_v2_negative_rel_qc_fail(tmp_paths: dict[str, Path]) -> None:
    """V2 symmetric relative-altitude band rejects deep negative frame-3 exports."""
    assert run_ingest(
        tmp_paths["db"], FIXTURES_HIDDEN / "hotel_v2_negative_rel_band.mseq", "hotel-28", "V2"
    ).returncode == 0
    out = run_export(tmp_paths["db"], "V2", "hotel-28", tmp_paths["report"])
    assert out.returncode == 0, out.stderr
    rep = json.loads(tmp_paths["report"].read_text(encoding="utf-8"))
    expect = expected_export(tmp_paths["db"], "V2", "hotel-28", epoch_base=EPOCH_BASE)
    assert rep == expect
    assert rep["upload_qc_pass"] is False
    assert rep["waypoints"][0]["alt_meters"] == -100.05


def test_audit_hash_ignores_mission_epoch_base_override(tmp_paths: dict[str, Path]) -> None:
    """audit_hash payload excludes exported_at_unix even when MISSION_EPOCH_BASE changes."""
    assert run_ingest(
        tmp_paths["db"], FIXTURES_HIDDEN / "romeo_hash_trap.mseq", "romeo-26", "V1"
    ).returncode == 0
    custom_epoch = 9_001_234_567
    out = run_export_with_epoch(tmp_paths["db"], "V1", "romeo-26", tmp_paths["report"], custom_epoch)
    assert out.returncode == 0, out.stderr
    rep = json.loads(tmp_paths["report"].read_text(encoding="utf-8"))
    expect = expected_export(tmp_paths["db"], "V1", "romeo-26", epoch_base=custom_epoch)
    baseline = expected_export(tmp_paths["db"], "V1", "romeo-26", epoch_base=EPOCH_BASE)
    assert rep["exported_at_unix"] == custom_epoch
    assert rep["exported_at_unix"] != baseline["exported_at_unix"]
    assert rep["audit_hash"] == expect["audit_hash"]
    assert rep["audit_hash"] == baseline["audit_hash"]
    assert rep == expect


def test_partial_fix_fails_negative_rel_qc_lower_bound(tmp_paths: dict[str, Path]) -> None:
    """Upper-bound-only QC still passes frame-3 altitudes below -max_rel_alt_m."""
    assert run_ingest(
        tmp_paths["db"], FIXTURES_HIDDEN / "delta_negative_rel_band.mseq", "delta-27", "V1"
    ).returncode == 0
    out = run_export(tmp_paths["db"], "V1", "delta-27", tmp_paths["report"])
    assert out.returncode == 0, out.stderr
    rep = json.loads(tmp_paths["report"].read_text(encoding="utf-8"))
    expect = expected_export(tmp_paths["db"], "V1", "delta-27", epoch_base=EPOCH_BASE)
    assert rep["waypoints"] == expect["waypoints"]
    assert rep["total_distance_m"] == expect["total_distance_m"]
    assert expect["upload_qc_pass"] is False
    if rep["upload_qc_pass"] and not expect["upload_qc_pass"]:
        pytest.fail("partial fix: symmetric lower bound missing for negative relative altitudes")


def test_yankee_all_suppress_empty_export_positive_distance(tmp_paths: dict[str, Path]) -> None:
    """All-suppressed uploads export an empty waypoints array but still roll up route distance."""
    assert run_ingest(
        tmp_paths["db"], FIXTURES_HIDDEN / "yankee_all_suppress.mseq", "yankee-29", "V1"
    ).returncode == 0
    out = run_export(tmp_paths["db"], "V1", "yankee-29", tmp_paths["report"])
    assert out.returncode == 0, out.stderr
    rep = json.loads(tmp_paths["report"].read_text(encoding="utf-8"))
    expect = expected_export(tmp_paths["db"], "V1", "yankee-29", epoch_base=EPOCH_BASE)
    assert rep == expect
    assert rep["waypoints"] == []
    assert rep["total_distance_m"] > 0.0
    assert rep["upload_qc_pass"] is True


def test_partial_fix_fails_all_suppress_exports_rows(tmp_paths: dict[str, Path]) -> None:
    """Suppress export fixes without suppressed rows in distance rollup fail yankee-all hidden."""
    assert run_ingest(
        tmp_paths["db"], FIXTURES_HIDDEN / "yankee_all_suppress.mseq", "yankee-29", "V1"
    ).returncode == 0
    out = run_export(tmp_paths["db"], "V1", "yankee-29", tmp_paths["report"])
    assert out.returncode == 0, out.stderr
    rep = json.loads(tmp_paths["report"].read_text(encoding="utf-8"))
    expect = expected_export(tmp_paths["db"], "V1", "yankee-29", epoch_base=EPOCH_BASE)
    assert rep["total_distance_m"] == expect["total_distance_m"]
    assert rep["waypoints"] == expect["waypoints"]


class TestCrossRunExportClock:
    """Export epoch uses upload-scoped max seq, not rowid order or other uploads (G-056)."""

    def test_tau_cross_epoch_upload_scoped_after_later_run(self, tmp_paths: dict[str, Path]) -> None:
        """A later upload on the same vehicle must not shift exported_at_unix for an earlier upload."""
        a = FIXTURES_HIDDEN / "tau_cross_epoch_a.mseq"
        b = FIXTURES_HIDDEN / "tau_cross_epoch_b.mseq"
        assert a.is_file() and b.is_file()
        assert run_ingest(tmp_paths["db"], a, "tau-33", "V1").returncode == 0
        assert run_ingest(tmp_paths["db"], b, "tau-34", "V1").returncode == 0
        out = run_export(tmp_paths["db"], "V1", "tau-33", tmp_paths["report"])
        assert out.returncode == 0, out.stderr
        rep = json.loads(tmp_paths["report"].read_text(encoding="utf-8"))
        expect = expected_export(tmp_paths["db"], "V1", "tau-33", epoch_base=EPOCH_BASE)
        assert rep["exported_at_unix"] == EPOCH_BASE + 5
        assert rep["exported_at_unix"] != EPOCH_BASE + 9
        assert rep["exported_at_unix"] == expect["exported_at_unix"]

    def test_tau_cross_epoch_file_order_max_seq_not_last_row(self, tmp_paths: dict[str, Path]) -> None:
        """High seq before low seq in the file still uses max(seq) for export clock."""
        log = FIXTURES_HIDDEN / "tau_cross_epoch_a.mseq"
        assert log.is_file()
        assert run_ingest(tmp_paths["db"], log, "tau-33", "V1").returncode == 0
        out = run_export(tmp_paths["db"], "V1", "tau-33", tmp_paths["report"])
        assert out.returncode == 0, out.stderr
        rep = json.loads(tmp_paths["report"].read_text(encoding="utf-8"))
        expect = expected_export(tmp_paths["db"], "V1", "tau-33", epoch_base=EPOCH_BASE)
        wrong = expected_export(
            tmp_paths["db"], "V1", "tau-33", epoch_base=EPOCH_BASE, epoch_mode="id_desc"
        )
        assert rep["exported_at_unix"] == EPOCH_BASE + 5
        assert wrong["exported_at_unix"] == EPOCH_BASE + 0
        assert rep["exported_at_unix"] != wrong["exported_at_unix"]
        assert rep["exported_at_unix"] == expect["exported_at_unix"]

    def test_partial_fix_fails_id_desc_export_epoch(self, tmp_paths: dict[str, Path]) -> None:
        """ORDER BY rowid DESC picks wrong epoch when physical file order != ascending seq."""
        assert run_ingest(tmp_paths["db"], FIXTURES / "whiskey.mseq", "whiskey-14", "V1").returncode == 0
        out = run_export(tmp_paths["db"], "V1", "whiskey-14", tmp_paths["report"])
        assert out.returncode == 0, out.stderr
        rep = json.loads(tmp_paths["report"].read_text(encoding="utf-8"))
        correct = expected_export(tmp_paths["db"], "V1", "whiskey-14", epoch_base=EPOCH_BASE)
        wrong = expected_export(
            tmp_paths["db"], "V1", "whiskey-14", epoch_base=EPOCH_BASE, epoch_mode="id_desc"
        )
        assert correct["exported_at_unix"] == EPOCH_BASE + 3
        assert wrong["exported_at_unix"] == EPOCH_BASE + 2
        assert rep["exported_at_unix"] == correct["exported_at_unix"]
        assert rep["exported_at_unix"] != wrong["exported_at_unix"]
