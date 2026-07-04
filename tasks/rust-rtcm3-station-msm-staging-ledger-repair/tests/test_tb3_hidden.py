"""Hidden verifier traps for rtcmctl partial-fix detection."""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, "/tests")
from fixture_codec import (
    corrupt_crc,
    encode_frame,
    reference_gap_delta,
    reference_observable_sum,
    reference_staging_keys_digest,
    reference_staging_keys_digest_insertion_order,
    reference_station_chain_digest,
)

APP = Path("/app")
BIN = APP / "bin" / "rtcmctl"
SNAPSHOT = APP / "state" / "rtcmctl-snapshot.json"
STAGING_MANIFEST = APP / "state" / "rtcmctl-staging-manifest.json"
FIXTURES = Path("/opt/verifier-fixtures/rtcm3")
U32_MAX = 4_294_967_295


def run_cmd(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess:
    proc = subprocess.run(
        [str(BIN), *args],
        cwd=APP,
        text=True,
        capture_output=True,
        timeout=90,
    )
    if check and proc.returncode != 0:
        raise AssertionError(
            f"command failed: {proc.args}\nSTDOUT={proc.stdout}\nSTDERR={proc.stderr}"
        )
    return proc


def init_db(tmp_path: Path) -> Path:
    db = tmp_path / "hidden.db"
    run_cmd(["init", "--db", str(db)])
    return db


def ingest(db: Path, capture: Path, ingest_at: str) -> None:
    run_cmd(
        [
            "ingest",
            "--db",
            str(db),
            "--capture",
            str(capture),
            "--ingest-at",
            ingest_at,
        ]
    )


@pytest.fixture(scope="module", autouse=True)
def ensure_hidden_fixtures():
    FIXTURES.mkdir(parents=True, exist_ok=True)
    seed = int(os.environ.get("RTCMCTL_SEED", "17"))
    obs_a = [(1, 2, 80_000 + seed, 0)]
    obs_b = [(2, 1, 12_000 + seed, 0)]
    cap = FIXTURES / f"hidden_{seed}.rtcm3"
    if not cap.exists():
        frames = [
            encode_frame(500 + seed, "HID_A", 1, 1_700_100_000_000, obs_a),
            encode_frame(500 + seed, "HID_B", 1, 1_700_100_000_100, obs_b),
        ]
        cap.write_bytes(b"".join(frames))
    yield


def test_hidden_dual_mountpoint_counts(tmp_path):
    """TB3_TRAP dual mountpoint — hidden ingest via /opt/verifier-fixtures must persist two rows."""
    seed = int(os.environ.get("RTCMCTL_SEED", "17"))
    cap = FIXTURES / f"hidden_{seed}.rtcm3"
    db = init_db(tmp_path)
    as_of = "2024-10-01T12:00:00Z"
    ingest(db, cap, as_of)
    with sqlite3.connect(db) as conn:
        count = conn.execute("SELECT COUNT(*) FROM stations").fetchone()[0]
    assert count == 2
    proc = run_cmd(["export", "--db", str(db), "--as-of", as_of, "json"])
    report = json.loads(proc.stdout)
    assert report["station_count"] == 2


def test_hidden_scaled_observable_sum(tmp_path):
    """TB3_TRAP scaled MSM sum — /opt/verifier-fixtures hidden ingest observable totals."""
    seed = int(os.environ.get("RTCMCTL_SEED", "17"))
    obs = [(1, 2, 80_000 + seed, 0)]
    frame = encode_frame(900, "SCALE", 4, 1_700_200_000_000, obs)
    cap = tmp_path / "hidden_scale.rtcm3"
    cap.write_bytes(frame)
    db = init_db(tmp_path)
    as_of = "2024-10-02T12:00:00Z"
    ingest(db, cap, as_of)
    expected = reference_observable_sum(obs)
    with sqlite3.connect(db) as conn:
        total = conn.execute("SELECT SUM(observable_sum) FROM stations").fetchone()[0]
    assert abs(total - expected) < 1e-5


def test_hidden_mid_batch_crc_aborts(tmp_path):
    """Hidden ingest must abort before persisting when a mid-batch CRC fails."""
    good = encode_frame(1, "A", 1, 1000, [(1, 0, 1, 0)])
    bad = corrupt_crc(encode_frame(1, "A", 2, 1001, [(1, 0, 2, 0)]))
    tail = encode_frame(1, "A", 3, 1002, [(1, 0, 3, 0)])
    cap = tmp_path / "midbad.rtcm3"
    cap.write_bytes(good + bad + tail)
    db = init_db(tmp_path)
    proc = run_cmd(
        [
            "ingest",
            "--db",
            str(db),
            "--capture",
            str(cap),
            "--ingest-at",
            "2024-10-03T12:00:00Z",
        ],
        check=False,
    )
    assert proc.returncode != 0
    with sqlite3.connect(db) as conn:
        n = conn.execute("SELECT COUNT(*) FROM stations").fetchone()[0]
        a = conn.execute("SELECT COUNT(*) FROM station_audit").fetchone()[0]
    assert n == 0
    assert a == 0


def test_hidden_audit_digest_chronological_order(tmp_path):
    """Hidden ledger digest must sort by created_at when event_id order disagrees."""
    db = init_db(tmp_path)
    with sqlite3.connect(db) as conn:
        conn.execute(
            """
            INSERT INTO station_audit (event_id, station_key, action, created_at)
            VALUES ('audit-zzz', '1:Z', 'ingested', '2024-10-04T12:00:00Z')
            """
        )
        conn.execute(
            """
            INSERT INTO station_audit (event_id, station_key, action, created_at)
            VALUES ('audit-aaa', '2:A', 'ingested', '2024-10-04T12:00:01Z')
            """
        )
        conn.commit()
    run_cmd(["publish-ledger", "--db", str(db)])
    expected = reference_station_chain_digest(db)
    ledger = json.loads((APP / "state" / "rtcmctl-station-ledger.json").read_text())
    assert ledger["chain_digest"] == expected


def test_hidden_gap_wrap_u32(tmp_path):
    """Hidden persist must count gaps when sequence wraps from u32::MAX to 2."""
    db = init_db(tmp_path)
    obs = [(1, 0, 1, 0)]
    cap = tmp_path / "hidden_wrap.rtcm3"
    cap.write_bytes(
        b"".join(
            [
                encode_frame(77, "HW", U32_MAX, 1000, obs),
                encode_frame(77, "HW", 2, 1001, obs),
            ]
        )
    )
    ingest(db, cap, "2024-10-04T12:30:00Z")
    with sqlite3.connect(db) as conn:
        gap_count = conn.execute("SELECT gap_count FROM stations").fetchone()[0]
    assert gap_count == reference_gap_delta(U32_MAX, 2)


def test_hidden_export_snapshot_gate_after_db_tamper(tmp_path):
    """Hidden export must ignore live SQLite tampering after snapshot publish."""
    db = init_db(tmp_path)
    frame = encode_frame(6, "TAMPER", 1, 1000, [(1, 0, 4, 0)])
    cap = tmp_path / "tamper.rtcm3"
    cap.write_bytes(frame)
    as_of = "2024-10-05T12:00:00Z"
    ingest(db, cap, as_of)
    with sqlite3.connect(db) as conn:
        conn.execute("UPDATE stations SET observable_sum = observable_sum + 1000")
        conn.commit()
    proc = run_cmd(["export", "--db", str(db), "--as-of", as_of, "json"])
    snap = json.loads(SNAPSHOT.read_text())
    report = json.loads(proc.stdout)
    assert abs(report["observable_sum_total"] - snap["observable_sum_total"]) < 1e-6
    assert report["observable_sum_total"] < 1000


class TestTB3RtcmTraps:
    """TB3 traps for partial-fix profiles (scale decoy, export path, batch atomicity)."""

    def test_tb3_scale_decoy_multiply_fails_hidden_sum(self, tmp_path):
        """Fixing only internal/scale.rs multiply formula must still fail scaled ingest."""
        seed = int(os.environ.get("RTCMCTL_SEED", "17"))
        obs = [(1, 2, 80_000 + seed, 0)]
        frame = encode_frame(900, "SCALE", 4, 1_700_200_000_000, obs)
        cap = tmp_path / "tb3_scale.rtcm3"
        cap.write_bytes(frame)
        db = init_db(tmp_path)
        as_of = "2024-10-02T12:00:00Z"
        ingest(db, cap, as_of)
        expected = reference_observable_sum(obs)
        with sqlite3.connect(db) as conn:
            total = conn.execute("SELECT SUM(observable_sum) FROM stations").fetchone()[0]
        assert abs(total - expected) < 1e-5

    def test_tb3_report_metrics_export_reads_live_sqlite(self, tmp_path):
        """export must not use report_metrics live SQLite aggregation."""
        db = init_db(tmp_path)
        frame = encode_frame(6, "METRICS", 1, 1000, [(1, 0, 4, 0)])
        cap = tmp_path / "metrics.rtcm3"
        cap.write_bytes(frame)
        as_of = "2024-10-06T12:00:00Z"
        ingest(db, cap, as_of)
        with sqlite3.connect(db) as conn:
            conn.execute("UPDATE stations SET gap_count = gap_count + 50")
            conn.commit()
        proc = run_cmd(["export", "--db", str(db), "--as-of", as_of, "json"])
        snap = json.loads(SNAPSHOT.read_text())
        report = json.loads(proc.stdout)
        assert report["total_gaps"] == snap["total_gaps"]

    def test_tb3_batch_persist_partial_commit_trap(self, tmp_path):
        """Second-row audit failure must not leave first-row station rows behind."""
        db = init_db(tmp_path)
        trap_key = "12:TB3"
        with sqlite3.connect(db) as conn:
            conn.execute(
                f"""
                CREATE TRIGGER block_tb3_audit
                BEFORE INSERT ON station_audit
                WHEN NEW.station_key = '{trap_key.replace("'", "''")}'
                BEGIN
                    SELECT RAISE(ABORT, 'blocked');
                END;
                """
            )
            conn.commit()
        staged = tmp_path / "tb3_batch.ndjson"
        rows = [
            {
                "station_key": "11:SAFE",
                "station_id": 11,
                "mountpoint": "SAFE",
                "sequence": 1,
                "epoch_ms": 2000,
                "observable_sum": 1.0,
            },
            {
                "station_key": trap_key,
                "station_id": 12,
                "mountpoint": "TB3",
                "sequence": 1,
                "epoch_ms": 2001,
                "observable_sum": 2.0,
            },
        ]
        staged.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
        STAGING_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
        STAGING_MANIFEST.write_text(
            json.dumps(
                {
                    "staged_path": str(staged),
                    "row_count": 2,
                    "station_keys": sorted([r["station_key"] for r in rows]),
                    "keys_digest": reference_staging_keys_digest([r["station_key"] for r in rows]),
                }
            )
        )
        proc = run_cmd(
            [
                "persist",
                "--db",
                str(db),
                "--staged",
                str(staged),
                "--ingest-at",
                "2024-10-07T12:00:00Z",
            ],
            check=False,
        )
        assert proc.returncode != 0
        with sqlite3.connect(db) as conn:
            assert conn.execute("SELECT COUNT(*) FROM stations").fetchone()[0] == 0
            assert conn.execute("SELECT COUNT(*) FROM station_audit").fetchone()[0] == 0

    def test_tb3_manifest_digest_requires_sorted_keys(self, tmp_path):
        """Manifest keys_digest must use lexicographically sorted keys, not insertion order."""
        db = init_db(tmp_path)
        staged = tmp_path / "tb3_manifest.ndjson"
        rows = [
            {
                "station_key": "9:ZULU",
                "station_id": 9,
                "mountpoint": "ZULU",
                "sequence": 1,
                "epoch_ms": 1000,
                "observable_sum": 1.0,
            },
            {
                "station_key": "1:ALPHA",
                "station_id": 1,
                "mountpoint": "ALPHA",
                "sequence": 1,
                "epoch_ms": 1001,
                "observable_sum": 2.0,
            },
        ]
        staged.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
        STAGING_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
        insertion_keys = [r["station_key"] for r in rows]
        STAGING_MANIFEST.write_text(
            json.dumps(
                {
                    "staged_path": str(staged),
                    "row_count": 2,
                    "station_keys": sorted(insertion_keys),
                    "keys_digest": reference_staging_keys_digest_insertion_order(insertion_keys),
                }
            )
        )
        proc = run_cmd(
            [
                "persist",
                "--db",
                str(db),
                "--staged",
                str(staged),
                "--ingest-at",
                "2024-10-08T12:00:00Z",
            ],
            check=False,
        )
        assert proc.returncode != 0
        with sqlite3.connect(db) as conn:
            assert conn.execute("SELECT COUNT(*) FROM stations").fetchone()[0] == 0

    def test_tb3_persist_requires_manifest(self, tmp_path):
        """persist must fail when staging manifest is absent."""
        db = init_db(tmp_path)
        staged = tmp_path / "no_manifest.ndjson"
        staged.write_text(
            json.dumps(
                {
                    "station_key": "3:C",
                    "station_id": 3,
                    "mountpoint": "C",
                    "sequence": 1,
                    "epoch_ms": 1000,
                    "observable_sum": 1.0,
                }
            )
            + "\n"
        )
        if STAGING_MANIFEST.exists():
            STAGING_MANIFEST.unlink()
        proc = run_cmd(
            [
                "persist",
                "--db",
                str(db),
                "--staged",
                str(staged),
                "--ingest-at",
                "2024-10-09T12:00:00Z",
            ],
            check=False,
        )
        assert proc.returncode != 0
