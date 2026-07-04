"""Reference solver for StampGate policy cache verifiers."""
from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

WORKSPACE = Path(os.environ.get("WORKSPACE", "/workspace"))
DATA = WORKSPACE / "data"
POLICY_DB = DATA / "stampgate-policy.sqlite"
API_BASE = "http://127.0.0.1:8966"

GLOBAL_POLICY = {
    "allowed_algorithms": ["RS256", "ES256", "EdDSA"],
    "default_max_clock_skew_sec": 60,
    "require_jti_min_length": 5,
    "issuer_prefix": "https://stampgate.classroom/",
}


def load_json(path: str | Path) -> dict:
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def read_text(path: str | Path) -> str:
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def output_path(name: str) -> str:
    return str(WORKSPACE / "output" / name)


def load_policy_rows() -> tuple[dict, list[dict]]:
    conn = sqlite3.connect(POLICY_DB)
    conn.row_factory = sqlite3.Row
    policy = dict(conn.execute("SELECT * FROM policy WHERE id = 1").fetchone())
    issuers = [dict(row) for row in conn.execute(
        "SELECT issuer_id, status, skew_override FROM issuers ORDER BY issuer_id"
    )]
    conn.close()
    return policy, issuers


def expected_policy_cache(api_base: str = API_BASE) -> dict:
    policy, issuers = load_policy_rows()
    active = sorted(row["issuer_id"] for row in issuers if row["status"] == "active")
    revoked = sorted(row["issuer_id"] for row in issuers if row["status"] == "revoked")
    overrides: dict[str, dict] = {}
    for row in issuers:
        if row["status"] == "active" and row["skew_override"] is not None:
            overrides[row["issuer_id"]] = {"max_clock_skew_sec": row["skew_override"]}
    allowed = json.loads(policy["allowed_algorithms"])
    return {
        "schema_version": "1.0",
        "api_base": api_base,
        "global_policy": {
            "allowed_algorithms": allowed,
            "default_max_clock_skew_sec": policy["default_max_clock_skew_sec"],
            "require_jti_min_length": policy["require_jti_min_length"],
            "issuer_prefix": policy["issuer_prefix"],
        },
        "active_issuers": active,
        "revoked_issuers": revoked,
        "issuer_overrides": overrides,
        "issuer_count": len(active),
        "revoked_count": len(revoked),
        "policy_sources": ["/api/policy", "/api/issuers"],
    }
