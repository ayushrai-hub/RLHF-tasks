"""Independent replay and audit_hash expectations for ABAC framed-wire auditor."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path

PROFILE_PATH = Path("/app/config/abac-policy-profile.json")


@dataclass(frozen=True)
class PolicyDecision:
    policy_id: str
    effective_decision: int
    last_eval_seq: int


@dataclass(frozen=True)
class ExportStats:
    evals_applied: int
    denies_overridden: int
    missing_attr_rejected: int
    duplicate_skipped: int


def load_profile() -> dict:
    return json.loads(PROFILE_PATH.read_text(encoding="utf-8"))


def combine_deny_overrides(prior: int | None, incoming: int) -> int:
    if prior is None:
        return incoming
    if prior == 0 or incoming == 0:
        return 0
    return 1


def audit_hash_payload(
    tenant_id: str,
    batch_id: str,
    decisions: list[PolicyDecision],
    stats: ExportStats,
) -> str:
    dec_part = ";".join(
        f"{d.policy_id}|{d.effective_decision}|{d.last_eval_seq}"
        for d in sorted(decisions, key=lambda x: x.policy_id)
    )
    stats_part = (
        f"evals_applied={stats.evals_applied};denies_overridden={stats.denies_overridden};"
        f"missing_attr_rejected={stats.missing_attr_rejected};duplicate_skipped={stats.duplicate_skipped}"
    )
    return f"{tenant_id}|{batch_id}|{dec_part}|{stats_part}"


def sha256_hex(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def latest_batch_id(conn: sqlite3.Connection, tenant_id: str) -> str:
    row = conn.execute(
        "SELECT batch_id FROM abac_batches WHERE tenant_id=? ORDER BY ingested_at DESC LIMIT 1",
        (tenant_id,),
    ).fetchone()
    return row[0] if row else ""


def load_decisions(conn: sqlite3.Connection, tenant_id: str) -> list[PolicyDecision]:
    rows = conn.execute(
        """SELECT policy_id, effective_decision, last_eval_seq
           FROM abac_policy_state WHERE tenant_id=? ORDER BY policy_id""",
        (tenant_id,),
    ).fetchall()
    return [
        PolicyDecision(r[0], int(r[1]), int(r[2]))
        for r in rows
    ]


def export_stats(conn: sqlite3.Connection, tenant_id: str, batch_id: str) -> ExportStats:
    if batch_id:
        row = conn.execute(
            """SELECT evals_applied, denies_overridden, missing_attr_rejected, duplicate_skipped
               FROM abac_batches WHERE batch_id=?""",
            (batch_id,),
        ).fetchone()
        if row:
            return ExportStats(int(row[0]), int(row[1]), int(row[2]), int(row[3]))
        return ExportStats(0, 0, 0, 0)
    dup = conn.execute(
        "SELECT duplicate_skipped FROM abac_tenant_stats WHERE tenant_id=?",
        (tenant_id,),
    ).fetchone()
    skipped = int(dup[0]) if dup else 0
    return ExportStats(0, 0, 0, skipped)


def max_utc_offset(conn: sqlite3.Connection, tenant_id: str) -> int:
    row = conn.execute(
        "SELECT COALESCE(MAX(utc_offset_sec),0) FROM abac_eval_events WHERE tenant_id=?",
        (tenant_id,),
    ).fetchone()
    return int(row[0]) if row else 0


def reported_at_unix(conn: sqlite3.Connection, tenant_id: str, profile: dict) -> int:
    return int(profile["abac_epoch_base"]) + max_utc_offset(conn, tenant_id)


def expected_audit_hash(conn: sqlite3.Connection, tenant_id: str) -> str:
    batch_id = latest_batch_id(conn, tenant_id)
    decisions = load_decisions(conn, tenant_id)
    stats = export_stats(conn, tenant_id, batch_id)
    payload = audit_hash_payload(tenant_id, batch_id, decisions, stats)
    return sha256_hex(payload)


def parse_report(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def assert_report_matches_db(report: dict, db_path: Path, tenant_id: str) -> None:
    profile = load_profile()
    conn = sqlite3.connect(db_path)
    try:
        batch_id = latest_batch_id(conn, tenant_id)
        assert report["tenant_id"] == tenant_id
        assert report["batch_id"] == batch_id
        assert report["reported_at_unix"] == reported_at_unix(conn, tenant_id, profile)
        expected_decisions = [
            {
                "policy_id": d.policy_id,
                "effective_decision": d.effective_decision,
                "last_eval_seq": d.last_eval_seq,
            }
            for d in load_decisions(conn, tenant_id)
        ]
        assert report["decisions"] == expected_decisions
        stats = export_stats(conn, tenant_id, batch_id)
        assert report["stats"] == {
            "evals_applied": stats.evals_applied,
            "denies_overridden": stats.denies_overridden,
            "missing_attr_rejected": stats.missing_attr_rejected,
            "duplicate_skipped": stats.duplicate_skipped,
        }
        assert report["audit_hash"] == expected_audit_hash(conn, tenant_id)
    finally:
        conn.close()


def top_level_key_order(report: dict) -> list[str]:
    return list(report.keys())
