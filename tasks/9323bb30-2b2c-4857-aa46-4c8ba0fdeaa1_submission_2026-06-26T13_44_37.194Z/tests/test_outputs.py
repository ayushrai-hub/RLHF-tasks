"""Verifier tests for scala-ansible-vault-shard-hotreload-evaluator."""

from __future__ import annotations

import json
import sqlite3
import subprocess
from pathlib import Path

from gen_vault_fixtures import (
    TENANT_ALPHA,
    TENANT_BETA,
    EPOCH_BASE,
    bad_crc_frames,
    conflict_cross_bundle_frames,
    conflict_second_frames,
    beta_duplicate_frames,
    duplicate_shard_frames,
    hidden_ooo_frames,
    hidden_precedence_shadow_frames,
    mixed_tenant_frames,
    precedence_trap_frames,
    precedence_trap_shards,
    public_bundle_frames,
    reload_gate_frames,
    reload_gate_shards,
    ten_alpha_public_shards,
    tenant_beta_frames,
    tenant_beta_shards,
    write_bundle,
)
from vault_expect import (
    audit_hash_from_body,
    build_report,
    compact_report_body,
    expected_report,
    replay_shard_rows,
)

INGEST = Path("/app/bin/vaultshard-ingest")
EXPORT = Path("/app/bin/vaultshard-export")
PUBLIC = Path("/app/fixtures/public/sample_bundle.vshard")


def run_ingest(db: Path, bundle: Path) -> subprocess.CompletedProcess[str]:
    db.parent.mkdir(parents=True, exist_ok=True)
    return subprocess.run(
        [str(INGEST), "--db", str(db), "--bundle", str(bundle)],
        capture_output=True,
        text=True,
        timeout=120,
    )


def run_export(db: Path, tenant_id: str, out: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(EXPORT), "--db", str(db), "--tenant-id", tenant_id, "--out", str(out)],
        capture_output=True,
        text=True,
        timeout=120,
    )


def connect(db: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    return conn


def load_report(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_db_rows(db: Path, tenant_id: str) -> list[dict]:
    conn = connect(db)
    rows = conn.execute(
        "SELECT shard_id, tenant_id, shard_seq, workload_id, material_source, "
        "reload_applied, log_redacted, secret_version, preview "
        "FROM vault_shards WHERE tenant_id = ? ORDER BY shard_seq, shard_id",
        (tenant_id,),
    ).fetchall()
    conn.close()
    out: list[dict] = []
    for r in rows:
        out.append(
            {
                "shard_id": r["shard_id"],
                "tenant_id": r["tenant_id"],
                "shard_seq": r["shard_seq"],
                "workload_id": r["workload_id"],
                "material_source": r["material_source"],
                "reload_applied": bool(r["reload_applied"]),
                "log_redacted": bool(r["log_redacted"]),
                "secret_version": r["secret_version"],
                "preview": r["preview"],
            }
        )
    return out


def dup_skipped(db: Path, tenant_id: str) -> int:
    conn = connect(db)
    row = conn.execute(
        "SELECT COALESCE(SUM(duplicate_skipped), 0) s FROM ingest_files WHERE tenant_id = ?",
        (tenant_id,),
    ).fetchone()
    conn.close()
    return int(row["s"])


def assert_report_matches(doc: dict, expected: dict) -> None:
    assert doc["tenant_id"] == expected["tenant_id"]
    assert doc["shards"] == expected["shards"]
    assert doc["workloads"] == expected["workloads"]
    assert doc["leak_rows"] == expected["leak_rows"]
    assert doc["stats"] == expected["stats"]
    assert doc["audit_hash"] == expected["audit_hash"]


def ingest_frames(db: Path, tmp_path: Path, name: str, frames, *, noise: bytes = b"") -> subprocess.CompletedProcess[str]:
    path = tmp_path / name
    write_bundle(path, frames, noise=noise)
    return run_ingest(db, path)


def test_public_tenant_alpha(tmp_path: Path) -> None:
    """Public bundle exports the tenant hot-reload audit JSON."""
    db = tmp_path / "pub.db"
    out = tmp_path / "pub.json"
    assert run_ingest(db, PUBLIC).returncode == 0
    proc = run_export(db, TENANT_ALPHA, out)
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert_report_matches(
        load_report(out),
        build_report(TENANT_ALPHA, ten_alpha_public_shards()),
    )


def test_sqlite_shard_rows(tmp_path: Path) -> None:
    """Public ingest stores three shard rows for TENANT-ALPHA."""
    db = tmp_path / "rows.db"
    assert run_ingest(db, PUBLIC).returncode == 0
    n = connect(db).execute(
        "SELECT COUNT(*) c FROM vault_shards WHERE tenant_id = ?",
        (TENANT_ALPHA,),
    ).fetchone()["c"]
    assert n == 3


def test_migrations_applied(tmp_path: Path) -> None:
    """Ingest applies migrations before inserting shard rows."""
    db = tmp_path / "mig.db"
    assert run_ingest(db, PUBLIC).returncode == 0
    conn = connect(db)
    assert conn.execute(
        "SELECT COUNT(*) c FROM schema_migrations WHERE version >= 1"
    ).fetchone()["c"] >= 1
    assert conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='vault_shards'"
    ).fetchone() is not None


def test_idempotent_file_replay(tmp_path: Path) -> None:
    """Re-ingesting identical bundle bytes does not add shard rows."""
    db = tmp_path / "idem.db"
    assert run_ingest(db, PUBLIC).returncode == 0
    n1 = connect(db).execute("SELECT COUNT(*) c FROM vault_shards").fetchone()["c"]
    assert run_ingest(db, PUBLIC).returncode == 0
    n2 = connect(db).execute("SELECT COUNT(*) c FROM vault_shards").fetchone()["c"]
    assert n1 == n2 == 3


def test_shard_id_duplicate_skipped(tmp_path: Path) -> None:
    """Duplicate shard_id in one bundle increments duplicate_shards_skipped."""
    db = tmp_path / "dup.db"
    out = tmp_path / "dup.json"
    assert run_ingest(db, PUBLIC).returncode == 0
    assert ingest_frames(db, tmp_path, "dup.vshard", duplicate_shard_frames()).returncode == 0
    assert run_export(db, TENANT_ALPHA, out).returncode == 0
    doc = load_report(out)
    assert doc["stats"]["shard_count"] == 3
    assert doc["stats"]["duplicate_shards_skipped"] == 2


def test_malformed_crc_rollback(tmp_path: Path) -> None:
    """Bad frame CRC rolls back the ingest transaction."""
    db = tmp_path / "crc.db"
    assert ingest_frames(db, tmp_path, "bad.vshard", bad_crc_frames()).returncode != 0
    conn = connect(db)
    assert conn.execute("SELECT COUNT(*) c FROM vault_shards").fetchone()["c"] == 0
    assert conn.execute("SELECT COUNT(*) c FROM ingest_files").fetchone()["c"] == 0


def test_noise_resync_prefix(tmp_path: Path) -> None:
    """Leading noise bytes before VS magic are skipped via resync."""
    db = tmp_path / "noise.db"
    out = tmp_path / "noise.json"
    assert (
        ingest_frames(
            db,
            tmp_path,
            "noise.vshard",
            public_bundle_frames(),
            noise=b"\x00\xff\xfe",
        ).returncode
        == 0
    )
    assert run_export(db, TENANT_ALPHA, out).returncode == 0
    assert_report_matches(
        load_report(out),
        build_report(TENANT_ALPHA, ten_alpha_public_shards()),
    )


def test_mixed_tenant_rejected(tmp_path: Path) -> None:
    """Bundles mixing tenant_id values are rejected."""
    db = tmp_path / "mix.db"
    assert ingest_frames(db, tmp_path, "mix.vshard", mixed_tenant_frames()).returncode != 0
    assert connect(db).execute("SELECT COUNT(*) c FROM vault_shards").fetchone()["c"] == 0


def test_cross_bundle_conflict_rollback(tmp_path: Path) -> None:
    """Second bundle conflicting on shard_seq+workload rolls back."""
    db = tmp_path / "conf.db"
    assert ingest_frames(db, tmp_path, "c1.vshard", conflict_cross_bundle_frames()).returncode == 0
    assert ingest_frames(db, tmp_path, "c2.vshard", conflict_second_frames()).returncode != 0
    assert connect(db).execute("SELECT COUNT(*) c FROM vault_shards").fetchone()["c"] == 1


def test_precedence_env_beats_vault_file(tmp_path: Path) -> None:
    """env material wins over vault_file for the same shard_seq and workload."""
    db = tmp_path / "prec.db"
    out = tmp_path / "prec.json"
    assert ingest_frames(db, tmp_path, "prec.vshard", precedence_trap_frames()).returncode == 0
    assert run_export(db, TENANT_ALPHA, out).returncode == 0
    shard = next(s for s in load_report(out)["shards"] if s["workload_id"] == "pay")
    assert shard["effective_source"] == "env"
    assert shard["secret_version"] == "env-wins"


def test_reload_gate_active_version_empty(tmp_path: Path) -> None:
    """active_version stays empty until reload_applied is true."""
    db = tmp_path / "gate.db"
    out = tmp_path / "gate.json"
    assert ingest_frames(db, tmp_path, "gate.vshard", reload_gate_frames()).returncode == 0
    assert run_export(db, TENANT_ALPHA, out).returncode == 0
    gate = next(w for w in load_report(out)["workloads"] if w["workload_id"] == "gate")
    assert gate["active_version"] == ""
    assert gate["reload_pending"] == "true"


def test_leak_row_unredacted_preview(tmp_path: Path) -> None:
    """Unredacted preview lines appear in leak_rows with detail unredacted_preview."""
    db = tmp_path / "leak.db"
    out = tmp_path / "leak.json"
    assert run_ingest(db, PUBLIC).returncode == 0
    assert run_export(db, TENANT_ALPHA, out).returncode == 0
    leaks = load_report(out)["leak_rows"]
    assert any(
        r["workload_id"] == "worker" and r["shard_seq"] == 3 and r["detail"] == "unredacted_preview"
        for r in leaks
    )


def test_reported_at_epoch_plus_max_seq(tmp_path: Path) -> None:
    """stats.reported_at_unix equals vault_epoch_base plus max shard_seq."""
    db = tmp_path / "epoch.db"
    out = tmp_path / "epoch.json"
    assert run_ingest(db, PUBLIC).returncode == 0
    assert run_export(db, TENANT_ALPHA, out).returncode == 0
    assert load_report(out)["stats"]["reported_at_unix"] == EPOCH_BASE + 3


def test_audit_hash_trailing_newline(tmp_path: Path) -> None:
    """audit_hash covers compact JSON plus trailing newline."""
    db = tmp_path / "hash.db"
    out = tmp_path / "hash.json"
    assert run_ingest(db, PUBLIC).returncode == 0
    assert run_export(db, TENANT_ALPHA, out).returncode == 0
    doc = load_report(out)
    rows = load_db_rows(db, TENANT_ALPHA)
    replay = replay_shard_rows(rows)
    compact = compact_report_body(
        TENANT_ALPHA,
        replay,
        len(rows),
        dup_skipped(db, TENANT_ALPHA),
        EPOCH_BASE + replay["max_shard_seq"],
    )
    assert doc["audit_hash"] == audit_hash_from_body(compact)


def test_top_level_key_order(tmp_path: Path) -> None:
    """Export JSON top-level keys follow audit-report-schema order."""
    db = tmp_path / "order.db"
    out = tmp_path / "order.json"
    assert run_ingest(db, PUBLIC).returncode == 0
    assert run_export(db, TENANT_ALPHA, out).returncode == 0
    keys = list(load_report(out).keys())
    assert keys == [
        "tenant_id",
        "shards",
        "workloads",
        "leak_rows",
        "stats",
        "audit_hash",
    ]


def test_workload_count_stats(tmp_path: Path) -> None:
    """stats.workload_count matches workloads array length."""
    db = tmp_path / "wc.db"
    out = tmp_path / "wc.json"
    assert run_ingest(db, PUBLIC).returncode == 0
    assert run_export(db, TENANT_ALPHA, out).returncode == 0
    doc = load_report(out)
    assert doc["stats"]["workload_count"] == len(doc["workloads"]) == 2


def test_shard_count_stats(tmp_path: Path) -> None:
    """stats.shard_count reflects stored shard rows for the tenant."""
    db = tmp_path / "sc.db"
    out = tmp_path / "sc.json"
    assert run_ingest(db, PUBLIC).returncode == 0
    assert run_export(db, TENANT_ALPHA, out).returncode == 0
    assert load_report(out)["stats"]["shard_count"] == 3


def test_duplicate_skipped_tenant_scoped(tmp_path: Path) -> None:
    """duplicate_shards_skipped sums ingest_files for the exported tenant only."""
    db = tmp_path / "scope.db"
    out = tmp_path / "scope.json"
    assert run_ingest(db, PUBLIC).returncode == 0
    assert ingest_frames(db, tmp_path, "dup-a.vshard", duplicate_shard_frames()).returncode == 0
    assert ingest_frames(db, tmp_path, "beta.vshard", tenant_beta_frames()).returncode == 0
    assert ingest_frames(db, tmp_path, "dup-beta.vshard", beta_duplicate_frames()).returncode == 0
    assert run_export(db, TENANT_ALPHA, out).returncode == 0
    assert load_report(out)["stats"]["duplicate_shards_skipped"] == 2


def test_export_other_tenant(tmp_path: Path) -> None:
    """Export scopes workloads and shards to the requested tenant_id."""
    db = tmp_path / "beta.db"
    out = tmp_path / "beta.json"
    assert ingest_frames(db, tmp_path, "b.vshard", tenant_beta_frames()).returncode == 0
    assert run_export(db, TENANT_BETA, out).returncode == 0
    assert_report_matches(load_report(out), build_report(TENANT_BETA, tenant_beta_shards()))


def test_out_of_order_file_stores_three_shards(tmp_path: Path) -> None:
    """Out-of-order frames still yield ascending shard_seq in export."""
    db = tmp_path / "ooo.db"
    out = tmp_path / "ooo.json"
    assert run_ingest(db, PUBLIC).returncode == 0
    assert run_export(db, TENANT_ALPHA, out).returncode == 0
    seqs = [s["shard_seq"] for s in load_report(out)["shards"]]
    assert seqs == sorted(seqs) == [1, 2, 3]


def test_api_active_version_after_reload(tmp_path: Path) -> None:
    """api workload active_version reflects the latest reload_applied shard."""
    db = tmp_path / "api.db"
    out = tmp_path / "api.json"
    assert run_ingest(db, PUBLIC).returncode == 0
    assert run_export(db, TENANT_ALPHA, out).returncode == 0
    api = next(w for w in load_report(out)["workloads"] if w["workload_id"] == "api")
    assert api["active_version"] == "v2-env"
    assert api["reload_pending"] == "false"


def test_worker_reload_pending(tmp_path: Path) -> None:
    """worker workload stays reload_pending when latest shard has reload_applied false."""
    db = tmp_path / "wrk.db"
    out = tmp_path / "wrk.json"
    assert run_ingest(db, PUBLIC).returncode == 0
    assert run_export(db, TENANT_ALPHA, out).returncode == 0
    worker = next(w for w in load_report(out)["workloads"] if w["workload_id"] == "worker")
    assert worker["active_version"] == ""
    assert worker["reload_pending"] == "true"


def test_expected_from_rows_helper() -> None:
    """vault_expect recomputes the public fixture without SQLite."""
    exp = build_report(TENANT_ALPHA, ten_alpha_public_shards())
    assert exp["stats"]["reported_at_unix"] == EPOCH_BASE + 3
    assert len(exp["leak_rows"]) == 1


def test_partial_fix_ingest_only_fails_mixed_tenant(tmp_path: Path) -> None:
    """Mixed tenant_id in one bundle must be rejected without persisting rows."""
    db = tmp_path / "pf1.db"
    assert ingest_frames(db, tmp_path, "pf-mix.vshard", mixed_tenant_frames()).returncode != 0
    assert connect(db).execute("SELECT COUNT(*) c FROM vault_shards").fetchone()["c"] == 0


def test_partial_fix_ingest_only_fails_rollback(tmp_path: Path) -> None:
    """Malformed CRC ingest must roll back vault_shards and ingest_files."""
    db = tmp_path / "pf2.db"
    assert ingest_frames(db, tmp_path, "pf-crc.vshard", bad_crc_frames()).returncode != 0
    conn = connect(db)
    assert conn.execute("SELECT COUNT(*) c FROM vault_shards").fetchone()["c"] == 0
    assert conn.execute("SELECT COUNT(*) c FROM ingest_files").fetchone()["c"] == 0


def test_partial_fix_store_only_fails_duplicate_scope(tmp_path: Path) -> None:
    """duplicate_shards_skipped must be scoped to the exported tenant."""
    db = tmp_path / "pf3.db"
    out = tmp_path / "pf3.json"
    assert run_ingest(db, PUBLIC).returncode == 0
    assert ingest_frames(db, tmp_path, "pf-dup.vshard", duplicate_shard_frames()).returncode == 0
    assert ingest_frames(db, tmp_path, "pf-beta-dup.vshard", beta_duplicate_frames()).returncode == 0
    assert run_export(db, TENANT_ALPHA, out).returncode == 0
    assert load_report(out)["stats"]["duplicate_shards_skipped"] == 2


def test_partial_fix_replay_only_fails_precedence(tmp_path: Path) -> None:
    """env beats vault_file at the same shard_seq for one workload."""
    db = tmp_path / "pf4.db"
    out = tmp_path / "pf4.json"
    assert ingest_frames(db, tmp_path, "pf4.vshard", precedence_trap_frames()).returncode == 0
    assert run_export(db, TENANT_ALPHA, out).returncode == 0
    assert_report_matches(
        load_report(out),
        build_report(TENANT_ALPHA, precedence_trap_shards()),
    )


def test_partial_fix_replay_only_fails_reload_gate(tmp_path: Path) -> None:
    """reload_applied false leaves active_version empty and reload_pending true."""
    db = tmp_path / "pf5.db"
    out = tmp_path / "pf5.json"
    assert ingest_frames(db, tmp_path, "pf5.vshard", reload_gate_frames()).returncode == 0
    assert run_export(db, TENANT_ALPHA, out).returncode == 0
    assert_report_matches(
        load_report(out),
        build_report(TENANT_ALPHA, reload_gate_shards()),
    )


def test_partial_fix_export_only_fails_audit_hash(tmp_path: Path) -> None:
    """Export audit_hash must match vault_expect compact payload."""
    db = tmp_path / "pf6.db"
    out = tmp_path / "pf6.json"
    assert run_ingest(db, PUBLIC).returncode == 0
    assert run_export(db, TENANT_ALPHA, out).returncode == 0
    doc = load_report(out)
    rows = load_db_rows(db, TENANT_ALPHA)
    exp = expected_report(
        TENANT_ALPHA,
        rows,
        shard_count=len(rows),
        duplicate_skipped=dup_skipped(db, TENANT_ALPHA),
    )
    assert doc["audit_hash"] == exp["audit_hash"]


def test_partial_fix_replay_only_fails_leak_detail(tmp_path: Path) -> None:
    """leak_rows detail must be unredacted_preview not raw preview text."""
    db = tmp_path / "pf7.db"
    out = tmp_path / "pf7.json"
    assert run_ingest(db, PUBLIC).returncode == 0
    assert run_export(db, TENANT_ALPHA, out).returncode == 0
    for row in load_report(out)["leak_rows"]:
        assert row["detail"] == "unredacted_preview"
        assert row["detail"] != "sekret"


def test_partial_fix_ingest_only_fails_noise_without_resync(tmp_path: Path) -> None:
    """Resync parser accepts bundles with leading noise bytes."""
    db = tmp_path / "pf8.db"
    proc = ingest_frames(
        db,
        tmp_path,
        "pf-noise.vshard",
        public_bundle_frames(),
        noise=b"\xde\xad",
    )
    assert proc.returncode == 0


def test_hidden_fixture_ooo_shard_seq(tmp_path: Path) -> None:
    """Verifier-only tests/fixtures/hidden_ooo.vshard applies ascending shard_seq not file order."""
    bundle = tmp_path / "hidden_ooo.vshard"
    write_bundle(bundle, hidden_ooo_frames())
    db = tmp_path / "hidden-ooo.db"
    out = tmp_path / "hidden-ooo.json"
    assert run_ingest(db, bundle).returncode == 0
    assert run_export(db, TENANT_ALPHA, out).returncode == 0
    doc = load_report(out)
    hidden_w = next(w for w in doc["workloads"] if w["workload_id"] == "hidden")
    assert hidden_w["active_version"] == "h30"
    seqs = [s["shard_seq"] for s in doc["shards"] if s["workload_id"] == "hidden"]
    assert seqs == [10, 20, 30]


def test_hidden_fixture_precedence_shadow(tmp_path: Path) -> None:
    """Verifier-only tests/fixtures/hidden_precedence.vshard keeps env over vault_file at shard_seq 40."""
    bundle = tmp_path / "hidden_precedence.vshard"
    write_bundle(bundle, hidden_precedence_shadow_frames())
    db = tmp_path / "hidden-prec.db"
    out = tmp_path / "hidden-prec.json"
    assert run_ingest(db, bundle).returncode == 0
    assert run_export(db, TENANT_ALPHA, out).returncode == 0
    shadow = next(s for s in load_report(out)["shards"] if s["workload_id"] == "shadow")
    assert shadow["effective_source"] == "env"
    assert shadow["secret_version"] == "env-shadow"
