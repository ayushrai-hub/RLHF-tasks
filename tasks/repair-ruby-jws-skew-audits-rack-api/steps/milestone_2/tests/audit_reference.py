"""Reference solver for StampGate JWS window verifiers."""
from __future__ import annotations

import base64
import csv
import json
import os
import sqlite3
from pathlib import Path

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec, ed25519, padding
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature

WORKSPACE = Path(os.environ.get("WORKSPACE", "/workspace"))
DATA = WORKSPACE / "data"
LEDGER = DATA / "assertion-ledger.csv"
POLICY_DB = DATA / "stampgate-policy.sqlite"
NONCE_DB = DATA / "nonce-cache.sqlite"
API_BASE = "http://127.0.0.1:8966"

WINDOW_DECISIONS = {
    "asrt-001": "valid_window",
    "asrt-002": "outside_skew",
    "asrt-003": "invalid_signature",
    "asrt-004": "valid_window",
    "asrt-005": "revoked",
    "asrt-006": "valid_window",
    "asrt-007": "valid_window",
    "asrt-008": "outside_skew",
    "asrt-009": "valid_window",
    "asrt-010": "valid_window",
    "asrt-011": "outside_skew",
    "asrt-012": "valid_window",
    "asrt-013": "alg_mismatch",
    "asrt-014": "valid_window",
    "asrt-015": "valid_window",
    "asrt-016": "valid_window",
    "asrt-017": "valid_window",
    "asrt-018": "valid_window",
    "asrt-019": "valid_window",
    "asrt-020": "valid_window",
    "asrt-021": "invalid_jti",
    "asrt-022": "outside_skew",
    "asrt-023": "valid_window",
    "asrt-024": "valid_window",
    "asrt-025": "valid_window",
    "asrt-026": "outside_skew",
    "asrt-028": "invalid_signature",
    "asrt-029": "valid_window",
    "asrt-030": "outside_skew",
    "asrt-031": "alg_mismatch",
    "asrt-032": "valid_window",
    "asrt-033": "outside_skew",
    "asrt-034": "invalid_signature",
    "asrt-036": "valid_window",
    "asrt-037": "outside_skew",
}

AUDIT_DECISIONS = {
    "asrt-001": "valid",
    "asrt-002": "outside_skew",
    "asrt-003": "invalid_signature",
    "asrt-004": "valid",
    "asrt-005": "revoked",
    "asrt-006": "valid",
    "asrt-007": "replay",
    "asrt-008": "outside_skew",
    "asrt-009": "valid",
    "asrt-010": "valid",
    "asrt-011": "outside_skew",
    "asrt-012": "valid",
    "asrt-013": "alg_mismatch",
    "asrt-014": "valid",
    "asrt-015": "valid",
    "asrt-016": "valid",
    "asrt-017": "replay",
    "asrt-018": "valid",
    "asrt-019": "replay",
    "asrt-020": "valid",
    "asrt-021": "invalid_jti",
    "asrt-022": "outside_skew",
    "asrt-023": "replay",
    "asrt-024": "valid",
    "asrt-025": "valid",
    "asrt-026": "outside_skew",
    "asrt-028": "invalid_signature",
    "asrt-029": "valid",
    "asrt-030": "outside_skew",
    "asrt-031": "alg_mismatch",
    "asrt-032": "valid",
    "asrt-033": "outside_skew",
    "asrt-034": "invalid_signature",
    "asrt-036": "valid",
    "asrt-037": "outside_skew",
}

VALID_REPLAY_COUNT = 16
REPORT_VALID_COUNT = 16
REPORT_REPLAY_COUNT = 4
REPORT_REJECTED_COUNT = 15


def load_json(path: str | Path) -> dict:
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def read_text(path: str | Path) -> str:
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def output_path(name: str) -> str:
    return str(WORKSPACE / "output" / name)


def b64url_decode(data: str) -> bytes:
    pad = "=" * ((4 - len(data) % 4) % 4)
    return base64.urlsafe_b64decode(data + pad)


def load_policy_rows() -> tuple[dict, list[dict]]:
    conn = sqlite3.connect(POLICY_DB)
    conn.row_factory = sqlite3.Row
    policy = dict(conn.execute("SELECT * FROM policy WHERE id = 1").fetchone())
    issuers = [dict(row) for row in conn.execute(
        "SELECT issuer_id, status, skew_override FROM issuers ORDER BY issuer_id"
    )]
    conn.close()
    return policy, issuers


def load_audit_flags(issuer_id: str) -> dict:
    conn = sqlite3.connect(POLICY_DB)
    row = conn.execute(
        "SELECT require_exact_iat FROM issuer_flags WHERE issuer_id = ?",
        (issuer_id,),
    ).fetchone()
    conn.close()
    if row and row[0]:
        return {"require_exact_iat": True}
    return {}


def load_jwk(issuer_id: str, kid: str) -> dict | None:
    conn = sqlite3.connect(POLICY_DB)
    row = conn.execute(
        "SELECT jwk_json FROM issuer_keys WHERE issuer_id = ? AND kid = ?",
        (issuer_id, kid),
    ).fetchone()
    conn.close()
    if row is None:
        return None
    return json.loads(row[0])


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


def load_ledger_rows() -> list[dict]:
    with LEDGER.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def effective_skew(cache: dict, issuer_id: str, audit_flags: dict) -> int:
    if audit_flags.get("require_exact_iat"):
        return 0
    override = cache["issuer_overrides"].get(issuer_id)
    if override and "max_clock_skew_sec" in override:
        return override["max_clock_skew_sec"]
    return cache["global_policy"]["default_max_clock_skew_sec"]


def jwk_to_public_key(jwk: dict):
    alg = jwk["alg"]
    if alg == "RS256":
        n = int.from_bytes(b64url_decode(jwk["n"]), "big")
        e = int.from_bytes(b64url_decode(jwk["e"]), "big")
        return rsa_public_numbers(n, e)
    if alg == "ES256":
        x = b64url_decode(jwk["x"])
        y = b64url_decode(jwk["y"])
        return ec_public_key(x, y)
    if alg == "EdDSA":
        raw = b64url_decode(jwk["x"])
        return ed25519.Ed25519PublicKey.from_public_bytes(raw)
    raise ValueError(f"unsupported jwk alg {alg}")


def rsa_public_numbers(n: int, e: int):
    from cryptography.hazmat.primitives.asymmetric import rsa

    return rsa.RSAPublicNumbers(e, n).public_key()


def ec_public_key(x: bytes, y: bytes):
    from cryptography.hazmat.primitives.asymmetric import ec

    public_numbers = ec.EllipticCurvePublicNumbers(
        int.from_bytes(x, "big"),
        int.from_bytes(y, "big"),
        ec.SECP256R1(),
    )
    return public_numbers.public_key()


def verify_signature(alg: str, header_b64: str, payload_b64: str, sig_b64: str, jwk: dict) -> bool:
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    signature = b64url_decode(sig_b64)
    key = jwk_to_public_key(jwk)
    try:
        if alg == "RS256":
            key.verify(signature, signing_input, padding.PKCS1v15(), hashes.SHA256())
            return True
        if alg == "ES256":
            if len(signature) == 64:
                r = int.from_bytes(signature[:32], "big")
                s = int.from_bytes(signature[32:], "big")
                der_sig = encode_dss_signature(r, s)
            else:
                der_sig = signature
            key.verify(der_sig, signing_input, ec.ECDSA(hashes.SHA256()))
            return True
        if alg == "EdDSA":
            key.verify(signature, signing_input)
            return True
    except Exception:
        return False
    return False


def validate_assertion(cache: dict, row: dict) -> dict:
    global_policy = cache["global_policy"]
    jti = row.get("jti", "")
    min_len = global_policy["require_jti_min_length"]
    if not jti or len(jti) < min_len:
        return {"ok": False, "reason": "invalid_jti"}

    parts = row["detached_jws"].split("..", 1)
    if len(parts) != 2:
        return {"ok": False, "reason": "invalid_signature"}

    header_b64, sig_b64 = parts
    payload_b64 = row["detached_payload_b64"]
    try:
        header = json.loads(b64url_decode(header_b64))
        payload = json.loads(b64url_decode(payload_b64))
    except (json.JSONDecodeError, ValueError):
        return {"ok": False, "reason": "invalid_signature"}

    expected_iss = f"{global_policy['issuer_prefix']}{row['issuer']}"
    if payload.get("iss") != expected_iss:
        return {"ok": False, "reason": "invalid_signature"}

    kid = header.get("kid", "")
    jwk = load_jwk(row["issuer"], kid)
    if jwk is None:
        return {"ok": False, "reason": "invalid_signature"}

    header_alg = header.get("alg", "")
    if header_alg != jwk["alg"] or header_alg != row["alg"]:
        return {"ok": False, "reason": "alg_mismatch"}

    if not verify_signature(header_alg, header_b64, payload_b64, sig_b64, jwk):
        return {"ok": False, "reason": "invalid_signature"}

    observed = int(row["observed_at_utc"])
    iat = int(payload["iat"])
    nbf = int(payload["nbf"]) if "nbf" in payload else iat
    if nbf > observed:
        return {"ok": False, "reason": "outside_skew"}

    audit_flags = load_audit_flags(row["issuer"])
    if audit_flags.get("require_exact_iat"):
        if iat != observed:
            return {"ok": False, "reason": "outside_skew"}
    else:
        skew = effective_skew(cache, row["issuer"], audit_flags)
        if abs(observed - iat) > skew:
            return {"ok": False, "reason": "outside_skew"}

    return {"ok": True, "matched_iat": iat}


def event_payload(row: dict, decision: str, matched_iat: int | None = None) -> dict:
    payload = {
        "assertion_id": row["assertion_id"],
        "issuer": row["issuer"],
        "observed_at_utc": int(row["observed_at_utc"]),
        "decision": decision,
    }
    if matched_iat is not None and decision in {"valid_window", "valid", "replay"}:
        payload["matched_iat"] = matched_iat
    return payload


def expected_window_check(policy_path: str, ledger_path: str) -> dict:
    cache = load_json(policy_path)
    events = []
    for row in load_ledger_rows():
        if row["issuer"] in cache["revoked_issuers"]:
            events.append(event_payload(row, "revoked"))
            continue
        result = validate_assertion(cache, row)
        if result["ok"]:
            events.append(event_payload(row, "valid_window", result["matched_iat"]))
        else:
            events.append(event_payload(row, result["reason"]))
    events.sort(key=lambda item: item["assertion_id"])
    return {
        "schema_version": "1.0",
        "ledger_path": ledger_path,
        "policy_path": policy_path,
        "events": events,
    }


def expected_audit_report(policy_path: str, ledger_path: str, cache_path: str) -> dict:
    cache = load_json(policy_path)
    events = []
    seen: set[tuple[str, str, str]] = set()
    valid_c = replay_c = rejected_c = 0
    for row in load_ledger_rows():
        if row["issuer"] in cache["revoked_issuers"]:
            events.append(event_payload(row, "revoked"))
            rejected_c += 1
            continue
        result = validate_assertion(cache, row)
        if not result["ok"]:
            events.append(event_payload(row, result["reason"]))
            rejected_c += 1
            continue
        key = (row["issuer"], row["jti"], row["alg"])
        if key in seen:
            events.append(event_payload(row, "replay", result["matched_iat"]))
            replay_c += 1
        else:
            seen.add(key)
            events.append(event_payload(row, "valid", result["matched_iat"]))
            valid_c += 1
    events.sort(key=lambda item: item["assertion_id"])
    return {
        "schema_version": "1.0",
        "ledger_path": ledger_path,
        "policy_path": policy_path,
        "cache_path": cache_path,
        "valid_count": valid_c,
        "replay_count": replay_c,
        "rejected_count": rejected_c,
        "events": events,
    }


def nonce_row_count() -> int:
    conn = sqlite3.connect(NONCE_DB)
    count = conn.execute("SELECT COUNT(*) FROM nonce_seen").fetchone()[0]
    conn.close()
    return count
