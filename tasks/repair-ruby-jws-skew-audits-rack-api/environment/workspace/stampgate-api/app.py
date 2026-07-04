#!/usr/bin/env python3
"""StampGate classroom policy API."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from flask import Flask, jsonify

DB_PATH = Path("/workspace/data/stampgate-policy.sqlite")

app = Flask(__name__)


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@app.get("/health")
def health():
    return jsonify({"status": "ok", "service": "stampgate"})


@app.get("/api/policy")
def policy():
    conn = connect()
    row = conn.execute("SELECT * FROM policy WHERE id = 1").fetchone()
    conn.close()
    allowed = json.loads(row["allowed_algorithms"])
    return jsonify(
        {
            "allowed_algorithms": allowed,
            "default_max_clock_skew_sec": row["default_max_clock_skew_sec"],
            "require_jti_min_length": row["require_jti_min_length"],
            "issuer_prefix": row["issuer_prefix"],
        }
    )


@app.get("/api/v2/jwks")
def legacy_jwks():
    """Deprecated route kept for regression drills. Do not use for audits."""
    return jsonify({"keys": [], "issuer": "stampgate-legacy", "status": "deprecated"})


@app.get("/api/issuers")
def issuers():
    conn = connect()
    rows = conn.execute(
        "SELECT issuer_id, status, skew_override FROM issuers ORDER BY issuer_id"
    ).fetchall()
    conn.close()
    payload = []
    for row in rows:
        item = {"issuer_id": row["issuer_id"], "status": row["status"]}
        if row["skew_override"] is not None:
            item["skew_override"] = row["skew_override"]
        payload.append(item)
    return jsonify(payload)


@app.get("/api/issuers/<issuer_id>/jwks")
def issuer_jwks(issuer_id: str):
    conn = connect()
    row = conn.execute(
        "SELECT status FROM issuers WHERE issuer_id = ?",
        (issuer_id,),
    ).fetchone()
    if row is None:
        conn.close()
        return jsonify({"error": "unknown_issuer"}), 404
    if row["status"] != "active":
        conn.close()
        return jsonify({"error": "issuer_unavailable", "issuer_id": issuer_id}), 404
    keys = conn.execute(
        "SELECT kid, alg, jwk_json FROM issuer_keys WHERE issuer_id = ? ORDER BY kid",
        (issuer_id,),
    ).fetchall()
    conn.close()
    return jsonify({"issuer_id": issuer_id, "keys": [json.loads(k["jwk_json"]) for k in keys]})


@app.get("/api/issuers/<issuer_id>/audit-flags")
def issuer_audit_flags(issuer_id: str):
    conn = connect()
    row = conn.execute(
        "SELECT require_exact_iat FROM issuer_flags WHERE issuer_id = ?",
        (issuer_id,),
    ).fetchone()
    conn.close()
    if row is None:
        return jsonify({"error": "no_audit_flags"}), 404
    return jsonify(
        {
            "issuer_id": issuer_id,
            "require_exact_iat": bool(row["require_exact_iat"]),
        }
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8966)
