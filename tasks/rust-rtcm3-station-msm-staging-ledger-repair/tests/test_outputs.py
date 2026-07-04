"""Behavioral verifier for rtcmctl RTCM3 ingest, ledger, and snapshot export."""

from __future__ import annotations

import json
import os
import random
import sqlite3
import string
import subprocess
from pathlib import Path

from fixture_codec import (
    corrupt_crc,
    db_fingerprint,
    encode_frame,
    reference_gap_delta,
    reference_observable_sum,
    reference_seal_digest,
    reference_staging_keys_digest,
    reference_station_chain_digest,
)

APP = Path("/app")
BIN = APP / "bin" / "rtcmctl"
SNAPSHOT = APP / "state" / "rtcmctl-snapshot.json"
LEDGER_ART = APP / "state" / "rtcmctl-station-ledger.json"
SEAL = APP / "state" / "rtcmctl-mutation-seal.json"
STAGING_MANIFEST = APP / "state" / "rtcmctl-staging-manifest.json"
STATE_SNAPSHOT_PATH = "/app/state/rtcmctl-snapshot.json"
STATE_SEAL_PATH = "/app/state/rtcmctl-mutation-seal.json"
STATE_MANIFEST_PATH = "/app/state/rtcmctl-staging-manifest.json"
U32_MAX = 4_294_967_295
RNG = random.SystemRandom()


def suffix() -> str:
    return "".join(RNG.choice(string.ascii_lowercase) for _ in range(8))


def run_cmd(args: list[str], *, check: bool = True, cwd: Path = APP) -> subprocess.CompletedProcess:
    proc = subprocess.run(
        [str(BIN), *args],
        cwd=cwd,
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
    db = tmp_path / f"rtcm-{suffix()}.db"
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


def export_health(db: Path, as_of: str) -> dict:
    proc = run_cmd(["export", "--db", str(db), "--as-of", as_of, "json"])
    return json.loads(proc.stdout)


def write_capture(path: Path, frames: list[bytes]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"".join(frames))


def station_rows(db: Path) -> list[tuple]:
    with sqlite3.connect(db) as conn:
        return conn.execute(
            """
            SELECT station_key, station_id, mountpoint, last_sequence, gap_count, observable_sum
            FROM stations ORDER BY station_key
            """
        ).fetchall()


def audit_count(db: Path) -> int:
    with sqlite3.connect(db) as conn:
        return conn.execute("SELECT COUNT(*) FROM station_audit").fetchone()[0]


def install_audit_block_trigger(db: Path, station_key: str) -> None:
    escaped = station_key.replace("'", "''")
    with sqlite3.connect(db) as conn:
        conn.execute(
            f"""
            CREATE TRIGGER block_audit_insert
            BEFORE INSERT ON station_audit
            WHEN NEW.station_key = '{escaped}'
            BEGIN
                SELECT RAISE(ABORT, 'audit insert blocked');
            END;
            """
        )
        conn.commit()


def write_staging_manifest(staged: Path, rows: list[dict]) -> None:
    keys = [r["station_key"] for r in rows]
    STAGING_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    STAGING_MANIFEST.write_text(
        json.dumps(
            {
                "staged_path": str(staged),
                "row_count": len(rows),
                "station_keys": sorted(set(keys)),
                "keys_digest": reference_staging_keys_digest(keys),
            }
        )
    )


def test_binary_exists():
    """The prebuilt rtcmctl binary must exist and be executable."""
    assert BIN.is_file() and os.access(BIN, os.X_OK)


def test_init_schema(tmp_path):
    """init must create stations, station_audit, and meta tables from schema.sql."""
    db = init_db(tmp_path)
    with sqlite3.connect(db) as conn:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
    assert {"stations", "station_audit", "meta"}.issubset(tables)


def test_decode_valid_capture(tmp_path):
    """decode must parse MSM7 frames with big-endian observables and valid CRC."""
    obs = [(3, 2, 12345, 0)]
    frame = encode_frame(1001, "ALPHA", 1, 1_700_000_000_000, obs)
    cap = tmp_path / "cap.rtcm3"
    write_capture(cap, [frame])
    ledger = tmp_path / "ledger.ndjson"
    run_cmd(["decode", "--capture", str(cap), "--ledger", str(ledger)])
    rows = [json.loads(line) for line in ledger.read_text().splitlines() if line.strip()]
    assert len(rows) == 1
    assert rows[0]["station_id"] == 1001
    assert rows[0]["mountpoint"] == "ALPHA"
    expected = reference_observable_sum(obs)
    assert abs(rows[0]["observable_sum"] - expected) < 1e-6


def test_decode_scale_exponent_nonzero(tmp_path):
    """decode must apply MSM scale exponents when computing observable_sum."""
    obs = [(5, 3, 250_000, 0)]
    frame = encode_frame(2002, "BETA", 7, 1_700_000_100_000, obs)
    cap = tmp_path / "scaled.rtcm3"
    write_capture(cap, [frame])
    ledger = tmp_path / "ledger.ndjson"
    run_cmd(["decode", "--capture", str(cap), "--ledger", str(ledger)])
    row = json.loads(ledger.read_text().strip())
    expected = reference_observable_sum(obs)
    assert abs(row["observable_sum"] - expected) < 1e-6


def test_decode_negative_scale_exp_uses_unit_divisor(tmp_path):
    """Negative scale_exp must use divisor 10^0 (not fractional powers)."""
    obs = [(6, -2, 7500, 0)]
    frame = encode_frame(3003, "GAMMA", 2, 1_700_000_200_000, obs)
    cap = tmp_path / "negexp.rtcm3"
    write_capture(cap, [frame])
    ledger = tmp_path / "ledger.ndjson"
    run_cmd(["decode", "--capture", str(cap), "--ledger", str(ledger)])
    row = json.loads(ledger.read_text().strip())
    expected = reference_observable_sum(obs)
    assert abs(row["observable_sum"] - expected) < 1e-6


def test_decode_crc_failure_leaves_no_partial(tmp_path):
    """decode must validate CRC before writing ledger or partial sidecar bytes."""
    obs = [(1, 0, 100, 0)]
    good = encode_frame(1, "X", 1, 1000, obs)
    bad = corrupt_crc(good)
    cap = tmp_path / "bad.rtcm3"
    write_capture(cap, [bad])
    ledger = tmp_path / "ledger.ndjson"
    partial = Path(f"{ledger}.partial")
    proc = run_cmd(
        ["decode", "--capture", str(cap), "--ledger", str(ledger)],
        check=False,
    )
    assert proc.returncode != 0
    assert not partial.exists() or partial.stat().st_size == 0
    if ledger.exists():
        assert ledger.read_text().strip() == ""


def test_stage_station_key_includes_mountpoint(tmp_path):
    """stage must emit station_key as station_id:mountpoint for every row."""
    obs = [(1, 0, 50, 0)]
    f1 = encode_frame(42, "MP1", 1, 1000, obs)
    f2 = encode_frame(42, "MP2", 1, 1001, obs)
    cap = tmp_path / "dual.rtcm3"
    write_capture(cap, [f1, f2])
    ledger = tmp_path / "ledger.ndjson"
    staged = tmp_path / "staged.ndjson"
    run_cmd(["decode", "--capture", str(cap), "--ledger", str(ledger)])
    run_cmd(["stage", "--ledger", str(ledger), "--staged", str(staged)])
    keys = {json.loads(line)["station_key"] for line in staged.read_text().splitlines()}
    assert keys == {"42:MP1", "42:MP2"}


def test_stage_writes_staging_manifest(tmp_path):
    """TB3_TRAP staging manifest — stage publishes /app/state/rtcmctl-staging-manifest.json with sorted keys digest."""
    obs = [(1, 0, 50, 0)]
    f1 = encode_frame(42, "MP1", 1, 1000, obs)
    f2 = encode_frame(42, "MP2", 1, 1001, obs)
    cap = tmp_path / "dual_manifest.rtcm3"
    write_capture(cap, [f1, f2])
    ledger = tmp_path / "ledger.ndjson"
    staged = tmp_path / "staged.ndjson"
    run_cmd(["decode", "--capture", str(cap), "--ledger", str(ledger)])
    run_cmd(["stage", "--ledger", str(ledger), "--staged", str(staged)])
    assert STAGING_MANIFEST.is_file()
    manifest = json.loads(STAGING_MANIFEST.read_text())
    assert manifest["staged_path"] == str(staged)
    assert manifest["row_count"] == 2
    assert manifest["station_keys"] == sorted(["42:MP1", "42:MP2"])
    expected_digest = reference_staging_keys_digest(["42:MP1", "42:MP2"])
    assert manifest["keys_digest"] == expected_digest


def test_persist_rejects_manifest_row_count_mismatch(tmp_path):
    """persist must reject when manifest row_count disagrees with staged lines."""
    db = init_db(tmp_path)
    staged = tmp_path / "staged.ndjson"
    staged.write_text(
        json.dumps(
            {
                "station_key": "1:A",
                "station_id": 1,
                "mountpoint": "A",
                "sequence": 1,
                "epoch_ms": 1000,
                "observable_sum": 1.0,
            }
        )
        + "\n"
    )
    STAGING_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    STAGING_MANIFEST.write_text(
        json.dumps(
            {
                "staged_path": str(staged),
                "row_count": 99,
                "station_keys": ["1:A"],
                "keys_digest": reference_staging_keys_digest(["1:A"]),
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
            "2024-06-01T12:05:00Z",
        ],
        check=False,
    )
    assert proc.returncode != 0


def test_persist_rejects_stale_manifest_staged_path(tmp_path):
    """persist must reject when manifest staged_path does not match --staged."""
    db = init_db(tmp_path)
    staged = tmp_path / "staged.ndjson"
    other = tmp_path / "other.ndjson"
    staged.write_text(
        json.dumps(
            {
                "station_key": "2:B",
                "station_id": 2,
                "mountpoint": "B",
                "sequence": 1,
                "epoch_ms": 1000,
                "observable_sum": 2.0,
            }
        )
        + "\n"
    )
    STAGING_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    STAGING_MANIFEST.write_text(
        json.dumps(
            {
                "staged_path": str(other),
                "row_count": 1,
                "station_keys": ["2:B"],
                "keys_digest": reference_staging_keys_digest(["2:B"]),
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
            "2024-06-01T12:06:00Z",
        ],
        check=False,
    )
    assert proc.returncode != 0


def test_persist_mountpoint_collision(tmp_path):
    """persist must keep distinct mountpoints on the same station_id separate."""
    db = init_db(tmp_path)
    obs = [(1, 0, 10, 0), (2, 0, 20, 0)]
    frames = [
        encode_frame(9, "NORTH", 1, 1000, [obs[0]]),
        encode_frame(9, "SOUTH", 2, 1001, [obs[1]]),
    ]
    cap = tmp_path / "mounts.rtcm3"
    write_capture(cap, frames)
    ingest(db, cap, "2024-06-01T12:00:00Z")
    rows = station_rows(db)
    assert len(rows) == 2
    keys = {r[0] for r in rows}
    assert keys == {"9:NORTH", "9:SOUTH"}
    sums = {r[0]: r[5] for r in rows}
    assert abs(sums["9:NORTH"] - 10.0) < 1e-6
    assert abs(sums["9:SOUTH"] - 20.0) < 1e-6


def test_gap_counts_missing_sequences(tmp_path):
    """persist must count skipped sequence numbers within a monotonic run."""
    db = init_db(tmp_path)
    obs = [(1, 0, 1, 0)]
    frames = [
        encode_frame(3, "G1", 1, 1000, obs),
        encode_frame(3, "G1", 5, 1001, obs),
    ]
    cap = tmp_path / "gaps.rtcm3"
    write_capture(cap, frames)
    ingest(db, cap, "2024-06-01T12:10:00Z")
    row = station_rows(db)[0]
    expected_gap = reference_gap_delta(1, 5)
    assert row[4] == expected_gap


def test_gap_single_step_wrap(tmp_path):
    """persist must treat u32 wrap MAX to 0 as a single-step advance with zero gap."""
    db = init_db(tmp_path)
    obs = [(1, 0, 1, 0)]
    frames = [
        encode_frame(6, "W0", U32_MAX, 1000, obs),
        encode_frame(6, "W0", 0, 1001, obs),
    ]
    cap = tmp_path / "wrap0.rtcm3"
    write_capture(cap, frames)
    ingest(db, cap, "2024-06-01T12:11:00Z")
    row = station_rows(db)[0]
    assert row[4] == reference_gap_delta(U32_MAX, 0)


def test_gap_wraparound_u32_boundary(tmp_path):
    """persist must count gaps across u32 sequence wrap using forward distance."""
    db = init_db(tmp_path)
    obs = [(1, 0, 1, 0)]
    frames = [
        encode_frame(4, "WRAP", U32_MAX, 1000, obs),
        encode_frame(4, "WRAP", 2, 1001, obs),
    ]
    cap = tmp_path / "wrap2.rtcm3"
    write_capture(cap, frames)
    ingest(db, cap, "2024-06-01T12:12:00Z")
    row = station_rows(db)[0]
    assert row[4] == reference_gap_delta(U32_MAX, 2)


def test_persist_keeps_audit_and_station_aligned(tmp_path):
    """Successful persist must write matching station and audit rows."""
    db = init_db(tmp_path)
    frame = encode_frame(1, "OK", 1, 1000, [(1, 0, 3, 0)])
    cap = tmp_path / "ok.rtcm3"
    write_capture(cap, [frame])
    ingest(db, cap, "2024-06-01T12:15:00Z")
    assert audit_count(db) == 1
    assert len(station_rows(db)) == 1


def test_persist_rollback_on_audit_failure(tmp_path):
    """persist must roll back station updates when audit insert fails."""
    db = init_db(tmp_path)
    trap_key = "7:TRAP"
    install_audit_block_trigger(db, trap_key)
    staged = tmp_path / "staged.ndjson"
    row = {
        "station_key": trap_key,
        "station_id": 7,
        "mountpoint": "TRAP",
        "sequence": 1,
        "epoch_ms": 1000,
        "observable_sum": 1.0,
    }
    staged.write_text(json.dumps(row) + "\n")
    write_staging_manifest(staged, [row])
    proc = run_cmd(
        [
            "persist",
            "--db",
            str(db),
            "--staged",
            str(staged),
            "--ingest-at",
            "2024-06-01T12:16:00Z",
        ],
        check=False,
    )
    assert proc.returncode != 0
    assert len(station_rows(db)) == 0
    assert audit_count(db) == 0


def test_persist_batch_atomic_on_audit_failure(tmp_path):
    """TB3_TRAP batch atomicity — failed audit insert on any row rolls back entire persist batch."""
    db = init_db(tmp_path)
    trap_key = "9:BATCH"
    install_audit_block_trigger(db, trap_key)
    staged = tmp_path / "batch.ndjson"
    rows = [
        {
            "station_key": "8:OK",
            "station_id": 8,
            "mountpoint": "OK",
            "sequence": 1,
            "epoch_ms": 1000,
            "observable_sum": 2.0,
        },
        {
            "station_key": trap_key,
            "station_id": 9,
            "mountpoint": "BATCH",
            "sequence": 1,
            "epoch_ms": 1001,
            "observable_sum": 3.0,
        },
    ]
    staged.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    write_staging_manifest(staged, rows)
    proc = run_cmd(
        [
            "persist",
            "--db",
            str(db),
            "--staged",
            str(staged),
            "--ingest-at",
            "2024-06-01T12:17:00Z",
        ],
        check=False,
    )
    assert proc.returncode != 0
    assert len(station_rows(db)) == 0
    assert audit_count(db) == 0


def test_station_chain_digest_order(tmp_path):
    """publish-ledger chain_digest must sort audit rows by created_at then event_id."""
    db = init_db(tmp_path)
    frames = [
        encode_frame(1, "A", 1, 1000, [(1, 0, 1, 0)]),
        encode_frame(2, "B", 1, 1001, [(1, 0, 2, 0)]),
    ]
    cap = tmp_path / "audit.rtcm3"
    write_capture(cap, frames)
    ingest(db, cap, "2024-06-01T12:00:00Z")
    ingest(db, cap, "2024-06-01T12:00:01Z")
    expected = reference_station_chain_digest(db)
    ledger = json.loads(LEDGER_ART.read_text())
    assert ledger["chain_digest"] == expected


def test_snapshot_and_seal_written(tmp_path):
    """ingest must publish snapshot and seal artifacts with contract digests."""
    db = init_db(tmp_path)
    frame = encode_frame(5, "S", 1, 1000, [(1, 1, 5000, 0)])
    cap = tmp_path / "snap.rtcm3"
    write_capture(cap, [frame])
    as_of = "2024-06-01T13:00:00Z"
    ingest(db, cap, as_of)
    assert SNAPSHOT.is_file()
    assert SEAL.is_file()
    snap = json.loads(SNAPSHOT.read_text())
    assert snap["db_path"] == str(db)
    assert snap["as_of"] == as_of
    assert snap["db_fingerprint"] == db_fingerprint(db)
    seal = json.loads(SEAL.read_text())
    assert reference_seal_digest(seal) == snap["mutation_seal_digest"]


def test_export_reads_snapshot_not_live_db(tmp_path):
    """export must return counters from the published snapshot, not live SQLite."""
    db = init_db(tmp_path)
    frame = encode_frame(8, "E", 1, 1000, [(1, 0, 7, 0)])
    cap = tmp_path / "export.rtcm3"
    write_capture(cap, [frame])
    as_of = "2024-06-01T14:00:00Z"
    ingest(db, cap, as_of)
    report = export_health(db, as_of)
    snap = json.loads(SNAPSHOT.read_text())
    assert report["station_count"] == snap["station_count"]
    assert report["total_gaps"] == snap["total_gaps"]
    assert abs(report["observable_sum_total"] - snap["observable_sum_total"]) < 1e-6

    with sqlite3.connect(db) as conn:
        conn.execute("UPDATE stations SET gap_count = gap_count + 99")
        conn.commit()
    report2 = export_health(db, as_of)
    assert report2 == report


def test_export_rejects_stale_seal_digest(tmp_path):
    """export must reject snapshots whose mutation_seal_digest no longer matches."""
    db = init_db(tmp_path)
    frame = encode_frame(1, "Z", 1, 1000, [(1, 0, 1, 0)])
    cap = tmp_path / "stale.rtcm3"
    write_capture(cap, [frame])
    as_of = "2024-06-01T15:00:00Z"
    ingest(db, cap, as_of)
    snap = json.loads(SNAPSHOT.read_text())
    snap["mutation_seal_digest"] = "0" * 64
    SNAPSHOT.write_text(json.dumps(snap))
    proc = run_cmd(["export", "--db", str(db), "--as-of", as_of, "json"], check=False)
    assert proc.returncode != 0


def test_ingest_pipeline_end_to_end(tmp_path):
    """ingest must run decode, stage, persist, and export coherently for seeded input."""
    seed = int(os.environ.get("RTCMCTL_SEED", "0"))
    station = 1000 + (seed % 50)
    mp = f"M{seed % 7}"
    seq = 10 + seed
    obs = [(4, 2, 50_000 + seed, 0)]
    frame = encode_frame(station, mp, seq, 1_700_000_000_000 + seed, obs)
    cap = tmp_path / "seed.rtcm3"
    write_capture(cap, [frame])
    db = init_db(tmp_path)
    as_of = "2024-07-01T08:00:00Z"
    ingest(db, cap, as_of)
    rows = station_rows(db)
    assert len(rows) == 1
    assert rows[0][0] == f"{station}:{mp}"
    expected_sum = reference_observable_sum(obs)
    assert abs(rows[0][5] - expected_sum) < 1e-5
    report = export_health(db, as_of)
    assert report["station_count"] == 1
    assert abs(report["observable_sum_total"] - expected_sum) < 1e-5


def test_ingest_writes_state_manifest_snapshot_seal(tmp_path):
    """ingest must write /app/state/rtcmctl-staging-manifest.json, /app/state/rtcmctl-snapshot.json, and /app/state/rtcmctl-mutation-seal.json."""
    seed = int(os.environ.get("RTCMCTL_SEED", "0"))
    station = 1100 + (seed % 50)
    mp = f"S{seed % 5}"
    frame = encode_frame(station, mp, 1, 1_700_000_000_000, [(1, 0, 100, 0)])
    cap = tmp_path / "state_paths.rtcm3"
    write_capture(cap, [frame])
    db = init_db(tmp_path)
    as_of = "2024-07-02T08:00:00Z"
    ingest(db, cap, as_of)
    assert STAGING_MANIFEST.is_file()
    assert Path(STATE_MANIFEST_PATH).is_file()
    assert Path(STATE_SNAPSHOT_PATH).is_file()
    assert Path(STATE_SEAL_PATH).is_file()
    assert SNAPSHOT.is_file()
    assert SEAL.is_file()
    manifest = json.loads(STAGING_MANIFEST.read_text())
    assert manifest["staged_path"]
    assert manifest["row_count"] >= 1


def test_decode_then_stage_then_persist_isolated(tmp_path):
    """persist must honor staged station_key and observable_sum from prior steps."""
    db = init_db(tmp_path)
    obs = [(2, 0, 99, 0)]
    frame = encode_frame(11, "ISO", 3, 5000, obs)
    cap = tmp_path / "iso.rtcm3"
    write_capture(cap, [frame])
    ledger = tmp_path / "led.ndjson"
    staged = tmp_path / "stg.ndjson"
    run_cmd(["decode", "--capture", str(cap), "--ledger", str(ledger)])
    run_cmd(["stage", "--ledger", str(ledger), "--staged", str(staged)])
    run_cmd(
        [
            "persist",
            "--db",
            str(db),
            "--staged",
            str(staged),
            "--ingest-at",
            "2024-08-01T09:00:00Z",
        ]
    )
    rows = station_rows(db)
    assert len(rows) == 1
    assert rows[0][0] == "11:ISO"
    assert abs(rows[0][5] - reference_observable_sum(obs)) < 1e-6


def test_refresh_snapshot_as_of_mismatch(tmp_path):
    """export must fail when the requested as_of does not match the snapshot."""
    db = init_db(tmp_path)
    frame = encode_frame(2, "R", 1, 1, [(1, 0, 1, 0)])
    cap = tmp_path / "ref.rtcm3"
    write_capture(cap, [frame])
    ingest(db, cap, "2024-09-01T10:00:00Z")
    proc = run_cmd(
        ["export", "--db", str(db), "--as-of", "2024-09-01T11:00:00Z", "json"],
        check=False,
    )
    assert proc.returncode != 0
