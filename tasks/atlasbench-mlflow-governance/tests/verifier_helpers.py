"""Schema readers and digest helpers for public verifier tests."""

from __future__ import annotations

import hashlib
import re
import sqlite3
from pathlib import Path

HEX64 = re.compile(r"^[0-9a-f]{64}$")

VALID_ACTION_STATUS = {"applied", "already_compliant", "skipped_conflict"}
VALID_RESOLUTION_STATUS = {
    "winner",
    "skipped_conflict",
    "inactive",
    "window_miss",
    "scope_miss",
    "predicate_miss",
}
VALID_URI_STATUS = {
    "redacted",
    "already_env",
    "no_password",
    "unsupported_scheme",
    "unmapped_credential",
}

POLICY_ACTION_COLUMNS = [
    "action_id",
    "source_file",
    "profile_id",
    "rule_id",
    "target_path",
    "old_value",
    "new_value",
    "exception_id",
    "status",
    "reason_code",
    "value_digest",
]

EXCEPTION_RESOLUTION_COLUMNS = [
    "resolution_id",
    "profile_id",
    "source_doc",
    "source_ordinal",
    "exception_id",
    "rule_id",
    "target_path",
    "scope_class",
    "scope_id",
    "amendment_seq",
    "resolution_status",
    "reason_code",
    "precedence_key",
]

URI_REDACTION_COLUMNS = [
    "redaction_id",
    "source_file",
    "profile_id",
    "target_path",
    "username",
    "uri_prefix",
    "cred_ref",
    "status",
]

LINEAGE_EDGE_COLUMNS = [
    "edge_id",
    "profile_id",
    "model_name",
    "experiment_id",
    "experiment_present",
    "experiment_quarantined",
    "model_quarantined_after",
]

RUN_SUMMARY_COLUMNS = [
    "dossier_digest",
    "input_configs_digest",
    "output_configs_digest",
    "evidence_chain_digest",
    "profile_count",
    "action_count",
    "exception_resolution_count",
    "uri_redaction_count",
    "lineage_edge_count",
]

EVIDENCE_TABLES = {
    "policy_actions",
    "exception_resolution",
    "uri_redactions",
    "lineage_edges",
    "run_summary",
}


def configs_digest(config_dir: Path, relative_paths: list[str]) -> str:
    """Lowercase SHA-256 over sorted relative paths and file bytes."""
    h = hashlib.sha256()
    for rel in sorted(relative_paths):
        data = (config_dir / rel).read_bytes()
        h.update(rel.encode())
        h.update(b"\n")
        h.update(data)
        h.update(b"\n")
    return h.hexdigest()


def list_participating_paths(config_dir: Path) -> list[str]:
    """Collect yaml/yml/toml paths up to one subdirectory level."""
    paths: list[str] = []
    for item in sorted(config_dir.iterdir(), key=lambda p: p.name):
        if item.is_file() and item.suffix.lower() in {".yaml", ".yml", ".toml"}:
            paths.append(item.name)
        elif item.is_dir():
            for sub in sorted(item.iterdir(), key=lambda p: p.name):
                if sub.is_file() and sub.suffix.lower() in {".yaml", ".yml", ".toml"}:
                    paths.append(f"{item.name}/{sub.name}")
    return sorted(paths)


def value_digest(rule_id: str, target_path: str, old_value: str, new_value: str, status: str) -> str:
    payload = f"{rule_id}\x1f{target_path}\x1f{old_value}\x1f{new_value}\x1f{status}\n"
    return hashlib.sha256(payload.encode()).hexdigest()


def evidence_chain_digest(db_path: Path) -> str:
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            "SELECT source_file, profile_id, rule_id, target_path, old_value, new_value, "
            "exception_id, status, reason_code FROM policy_actions ORDER BY action_id"
        ).fetchall()
    finally:
        conn.close()
    h = hashlib.sha256()
    for row in rows:
        parts = []
        for val in row:
            if val is None:
                parts.append("<NULL>")
            else:
                parts.append(str(val))
        h.update(("\x1f".join(parts) + "\n").encode())
    return h.hexdigest()


def read_run_summary(db_path: Path) -> dict:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT dossier_digest, input_configs_digest, output_configs_digest, "
            "evidence_chain_digest, profile_count, action_count, "
            "exception_resolution_count, uri_redaction_count, lineage_edge_count "
            "FROM run_summary"
        ).fetchone()
    finally:
        conn.close()
    return dict(row)


def read_policy_actions(db_path: Path) -> list[dict]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT action_id, source_file, profile_id, rule_id, target_path, old_value, "
            "new_value, exception_id, status, reason_code, value_digest "
            "FROM policy_actions ORDER BY action_id"
        ).fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]


def assert_schema_contract(db_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    try:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            ).fetchall()
        }
        assert tables == EVIDENCE_TABLES

        pa_cols = [c[1] for c in conn.execute("PRAGMA table_info(policy_actions)").fetchall()]
        assert pa_cols == POLICY_ACTION_COLUMNS

        er_cols = [c[1] for c in conn.execute("PRAGMA table_info(exception_resolution)").fetchall()]
        assert er_cols == EXCEPTION_RESOLUTION_COLUMNS

        ur_cols = [c[1] for c in conn.execute("PRAGMA table_info(uri_redactions)").fetchall()]
        assert ur_cols == URI_REDACTION_COLUMNS

        le_cols = [c[1] for c in conn.execute("PRAGMA table_info(lineage_edges)").fetchall()]
        assert le_cols == LINEAGE_EDGE_COLUMNS

        rs_cols = [c[1] for c in conn.execute("PRAGMA table_info(run_summary)").fetchall()]
        assert rs_cols == RUN_SUMMARY_COLUMNS

        statuses = {
            row[0] for row in conn.execute("SELECT DISTINCT status FROM policy_actions").fetchall()
        }
        assert statuses <= VALID_ACTION_STATUS

        summary_rows = conn.execute("SELECT COUNT(*) FROM run_summary").fetchone()[0]
        assert summary_rows == 1
    finally:
        conn.close()
