#!/usr/bin/env python3
"""Build StampGate policy database, nonce cache, keys, and assertion ledger."""
from __future__ import annotations

import base64
import csv
import json
import os
import sqlite3
from pathlib import Path

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, ed25519, padding, rsa
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature

WORKSPACE = Path(os.environ.get("WORKSPACE", "/workspace"))
DATA = WORKSPACE / "data"
KEYS = WORKSPACE / "keys"
LEDGER = DATA / "assertion-ledger.csv"
POLICY_DB = DATA / "stampgate-policy.sqlite"
NONCE_DB = DATA / "nonce-cache.sqlite"
NONCE_SQL = WORKSPACE / "sql" / "nonce-schema.sql"

BASE_TS = 1718487000

GLOBAL_POLICY = {
    "allowed_algorithms": ["RS256", "ES256", "EdDSA"],
    "default_max_clock_skew_sec": 60,
    "require_jti_min_length": 5,
    "issuer_prefix": "https://stampgate.classroom/",
}

ISSUERS = [
    {"issuer_id": "acme-lab", "status": "active", "skew_override": 0, "alg": "RS256", "kid": "ACME-2024-A"},
    {"issuer_id": "ops", "status": "active", "skew_override": 120, "alg": "RS256", "kid": "OPS-2024-A"},
    {"issuer_id": "bravo", "status": "active", "skew_override": None, "alg": "EdDSA", "kid": "bravo-ed25519-a"},
    {"issuer_id": "charlie", "status": "revoked", "skew_override": None, "alg": "RS256", "kid": "CHARLIE-REV"},
    {"issuer_id": "delta", "status": "active", "skew_override": 45, "alg": "RS256", "kid": "DELTA-2024-A"},
    {"issuer_id": "echo", "status": "active", "skew_override": None, "alg": "RS256", "kid": "ECHO-2024-A"},
    {"issuer_id": "foxtrot", "status": "active", "skew_override": None, "alg": "RS256", "kid": "FOXTROT-2024-A"},
    {"issuer_id": "golf", "status": "active", "skew_override": None, "alg": "RS256", "kid": "GOLF-2024-A"},
    {"issuer_id": "hotel", "status": "pending", "skew_override": None, "alg": "RS256", "kid": "HOTEL-PENDING"},
    {"issuer_id": "india", "status": "active", "skew_override": None, "alg": "ES256", "kid": "INDIA-ES256-A"},
    {"issuer_id": "juliet", "status": "active", "skew_override": None, "alg": "RS256", "kid": "JULIET-2024-A"},
]

AUDIT_FLAGS = [
    {"issuer_id": "echo", "require_exact_iat": 1},
    {"issuer_id": "juliet", "require_exact_iat": 1},
]


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def b64url_json(obj: dict) -> str:
    return b64url(json.dumps(obj, separators=(",", ":"), sort_keys=True).encode("utf-8"))


def generate_keys() -> dict[str, dict]:
    material: dict[str, dict] = {}
    for row in ISSUERS:
        issuer_id = row["issuer_id"]
        if row["status"] not in ("active", "revoked"):
            continue
        alg = row["alg"]
        kid = row["kid"]
        if alg == "RS256":
            private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            public_numbers = private_key.public_key().public_numbers()
            n = b64url(public_numbers.n.to_bytes((public_numbers.n.bit_length() + 7) // 8, "big"))
            e = b64url(public_numbers.e.to_bytes((public_numbers.e.bit_length() + 7) // 8, "big"))
            jwk = {"kty": "RSA", "kid": kid, "use": "sig", "alg": "RS256", "n": n, "e": e}
        elif alg == "EdDSA":
            private_key = ed25519.Ed25519PrivateKey.generate()
            public_bytes = private_key.public_key().public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw,
            )
            jwk = {
                "kty": "OKP",
                "crv": "Ed25519",
                "kid": kid,
                "use": "sig",
                "alg": "EdDSA",
                "x": b64url(public_bytes),
            }
        else:
            private_key = ec.generate_private_key(ec.SECP256R1())
            public_numbers = private_key.public_key().public_numbers()
            x = b64url(public_numbers.x.to_bytes(32, "big"))
            y = b64url(public_numbers.y.to_bytes(32, "big"))
            jwk = {"kty": "EC", "crv": "P-256", "kid": kid, "use": "sig", "alg": "ES256", "x": x, "y": y}

        pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        key_path = KEYS / f"{issuer_id}.pem"
        key_path.write_bytes(pem)
        material[issuer_id] = {"private_key": private_key, "jwk": jwk, "alg": alg, "kid": kid}
    return material


def sign_detached(
    private_key,
    alg: str,
    kid: str,
    payload: dict,
    header_alg: str | None = None,
    header_kid: str | None = None,
) -> tuple[str, str]:
    use_alg = header_alg or alg
    header = {"alg": use_alg, "typ": "JWT", "kid": header_kid or kid}
    payload_b64 = b64url_json(payload)
    header_b64 = b64url_json(header)
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")

    if alg == "RS256":
        signature = private_key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
    elif alg == "ES256":
        der_sig = private_key.sign(signing_input, ec.ECDSA(hashes.SHA256()))
        signature = _der_to_raw_ecdsa(der_sig, 32)
    elif alg == "EdDSA":
        signature = private_key.sign(signing_input)
    else:
        raise ValueError(f"unsupported alg {alg}")

    detached = f"{header_b64}..{b64url(signature)}"
    return detached, payload_b64


def _der_to_raw_ecdsa(der_sig: bytes, size: int) -> bytes:
    if len(der_sig) == size * 2:
        return der_sig
    r, s = decode_dss_signature(der_sig)
    return r.to_bytes(size, "big") + s.to_bytes(size, "big")


def payload_for(
    issuer_id: str,
    jti: str,
    iat: int,
    nbf: int | None = None,
    iss: str | None = None,
) -> dict:
    prefix = GLOBAL_POLICY["issuer_prefix"]
    doc = {
        "iss": iss or f"{prefix}{issuer_id}",
        "jti": jti,
        "iat": iat,
        "sub": "audit-fixture",
    }
    if nbf is not None:
        doc["nbf"] = nbf
    return doc


def build_policy_db(keys: dict[str, dict]) -> None:
    conn = sqlite3.connect(POLICY_DB)
    conn.executescript(
        """
        CREATE TABLE policy (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            allowed_algorithms TEXT NOT NULL,
            default_max_clock_skew_sec INTEGER NOT NULL,
            require_jti_min_length INTEGER NOT NULL,
            issuer_prefix TEXT NOT NULL
        );
        CREATE TABLE issuers (
            issuer_id TEXT PRIMARY KEY,
            status TEXT NOT NULL,
            skew_override INTEGER
        );
        CREATE TABLE issuer_keys (
            issuer_id TEXT NOT NULL,
            kid TEXT NOT NULL,
            alg TEXT NOT NULL,
            jwk_json TEXT NOT NULL,
            PRIMARY KEY (issuer_id, kid)
        );
        CREATE TABLE issuer_flags (
            issuer_id TEXT PRIMARY KEY,
            require_exact_iat INTEGER NOT NULL DEFAULT 0
        );
        """
    )
    conn.execute(
        "INSERT INTO policy (id, allowed_algorithms, default_max_clock_skew_sec, "
        "require_jti_min_length, issuer_prefix) VALUES (1, ?, ?, ?, ?)",
        (
            json.dumps(GLOBAL_POLICY["allowed_algorithms"]),
            GLOBAL_POLICY["default_max_clock_skew_sec"],
            GLOBAL_POLICY["require_jti_min_length"],
            GLOBAL_POLICY["issuer_prefix"],
        ),
    )
    for row in ISSUERS:
        conn.execute(
            "INSERT INTO issuers (issuer_id, status, skew_override) VALUES (?, ?, ?)",
            (row["issuer_id"], row["status"], row["skew_override"]),
        )
        if row["status"] not in ("active", "revoked"):
            continue
        material = keys[row["issuer_id"]]
        conn.execute(
            "INSERT INTO issuer_keys (issuer_id, kid, alg, jwk_json) VALUES (?, ?, ?, ?)",
            (row["issuer_id"], material["kid"], material["alg"], json.dumps(material["jwk"])),
        )
    for row in AUDIT_FLAGS:
        conn.execute(
            "INSERT INTO issuer_flags (issuer_id, require_exact_iat) VALUES (?, ?)",
            (row["issuer_id"], row["require_exact_iat"]),
        )
    conn.commit()
    conn.close()


def build_nonce_db() -> None:
    schema = NONCE_SQL.read_text(encoding="utf-8")
    conn = sqlite3.connect(NONCE_DB)
    conn.executescript(schema)
    conn.commit()
    conn.close()


def build_ledger(keys: dict[str, dict]) -> list[dict]:
    rows_spec = [
        ("asrt-001", "acme-lab", "jti-acme-001", BASE_TS, BASE_TS, BASE_TS, None, None),
        ("asrt-002", "acme-lab", "jti-acme-002", BASE_TS - 30, BASE_TS - 30, BASE_TS, None, None),
        ("asrt-003", "acme-lab", "jti-acme-003", BASE_TS, BASE_TS, BASE_TS, "bad_sig", None),
        ("asrt-004", "ops", "jti-ops-004", BASE_TS, BASE_TS, BASE_TS, None, None),
        ("asrt-005", "charlie", "jti-ch-005", BASE_TS, BASE_TS, BASE_TS, None, None),
        ("asrt-006", "ops", "jti-ops-006", BASE_TS + 90, BASE_TS + 90, BASE_TS + 90, None, None),
        ("asrt-007", "acme-lab", "jti-acme-001", BASE_TS + 5, BASE_TS + 5, BASE_TS + 5, None, None),
        ("asrt-008", "delta", "jti-delta-008", BASE_TS - 300, BASE_TS - 300, BASE_TS, None, None),
        ("asrt-009", "delta", "jti-delta-009", BASE_TS, BASE_TS, BASE_TS, None, None),
        ("asrt-010", "echo", "jti-echo-010", BASE_TS, BASE_TS, BASE_TS, None, None),
        ("asrt-011", "echo", "jti-echo-011", BASE_TS - 30, BASE_TS - 30, BASE_TS, None, None),
        ("asrt-012", "bravo", "jti-bravo-012", BASE_TS, BASE_TS, BASE_TS, None, None),
        ("asrt-013", "bravo", "jti-bravo-013", BASE_TS, BASE_TS, BASE_TS, None, "ES256"),
        ("asrt-014", "foxtrot", "jti-fox-014", BASE_TS, BASE_TS, BASE_TS, None, None),
        ("asrt-015", "foxtrot", "jti-fox-015", BASE_TS - 45, BASE_TS - 45, BASE_TS, None, None),
        ("asrt-016", "golf", "jti-golf-replay-a", BASE_TS, BASE_TS, BASE_TS, None, None),
        ("asrt-017", "golf", "jti-golf-replay-a", BASE_TS + 5, BASE_TS + 5, BASE_TS + 5, None, None),
        ("asrt-018", "foxtrot", "jti-fox-018", BASE_TS, BASE_TS, BASE_TS, None, None),
        ("asrt-019", "foxtrot", "jti-fox-018", BASE_TS + 3, BASE_TS + 3, BASE_TS + 3, None, None),
        ("asrt-020", "india", "jti-india-020", BASE_TS, BASE_TS, BASE_TS, None, None),
        ("asrt-021", "acme-lab", "jt01", BASE_TS, BASE_TS, BASE_TS, None, None),
        ("asrt-022", "delta", "jti-delta-022", BASE_TS + 80, BASE_TS + 105, BASE_TS + 100, None, None),
        ("asrt-023", "india", "jti-india-020", BASE_TS + 8, BASE_TS + 8, BASE_TS + 8, None, None),
        ("asrt-024", "ops", "jti-ops-024", BASE_TS + 280, BASE_TS + 180, BASE_TS + 200, None, None, None, None),
        ("asrt-025", "delta", "jti-delta-025", BASE_TS + 460, BASE_TS + 460, BASE_TS + 500, None, None, None, None),
        ("asrt-026", "delta", "jti-delta-026", BASE_TS + 554, BASE_TS + 554, BASE_TS + 600, None, None, None, None),
        ("asrt-028", "bravo", "jti-bravo-028", BASE_TS, BASE_TS, BASE_TS, None, None, "BRAVO-ED25519-A", None),
        ("asrt-029", "juliet", "jti-juliet-029", BASE_TS + 400, BASE_TS + 400, BASE_TS + 400, None, None, None, None),
        ("asrt-030", "juliet", "jti-juliet-030", BASE_TS + 399, BASE_TS + 399, BASE_TS + 400, None, None, None, None),
        ("asrt-031", "golf", "jti-golf-031", BASE_TS + 20, BASE_TS + 20, BASE_TS + 20, None, None, None, "ES256", None),
        ("asrt-032", "foxtrot", "jti-fox-032", BASE_TS + 640, BASE_TS + 640, BASE_TS + 700, None, None, None, None, None),
        ("asrt-033", "foxtrot", "jti-fox-033", BASE_TS + 639, BASE_TS + 639, BASE_TS + 700, None, None, None, None, None),
        (
            "asrt-034",
            "foxtrot",
            "jti-fox-034",
            BASE_TS + 710,
            BASE_TS + 710,
            BASE_TS + 710,
            None,
            None,
            None,
            None,
            f"{GLOBAL_POLICY['issuer_prefix']}acme-lab",
        ),
        ("asrt-036", "ops", "jti-ops-036", BASE_TS + 620, BASE_TS + 500, BASE_TS + 500, None, None, None, None, None),
        ("asrt-037", "ops", "jti-ops-037", BASE_TS + 621, BASE_TS + 500, BASE_TS + 500, None, None, None, None, None),
    ]

    ledger_rows: list[dict] = []
    for spec in rows_spec:
        padded = list(spec) + [None] * (11 - len(spec))
        (
            assertion_id,
            issuer_id,
            jti,
            iat,
            nbf,
            observed_at,
            bad_sig,
            header_alg,
            header_kid,
            ledger_alg,
            iss_override,
        ) = padded[:11]
        material = keys[issuer_id]
        payload = payload_for(issuer_id, jti, iat, nbf, iss_override)
        if bad_sig:
            header = {"alg": material["alg"], "typ": "JWT", "kid": material["kid"]}
            header_b64 = b64url_json(header)
            payload_b64 = b64url_json(payload)
            detached = f"{header_b64}..aW52YWxpZHNpZw"
        else:
            detached, payload_b64 = sign_detached(
                material["private_key"],
                material["alg"],
                material["kid"],
                payload,
                header_alg=header_alg,
                header_kid=header_kid,
            )
        ledger_rows.append(
            {
                "assertion_id": assertion_id,
                "issuer": issuer_id,
                "jti": jti,
                "alg": ledger_alg or header_alg or material["alg"],
                "iat": iat,
                "nbf": nbf,
                "observed_at_utc": observed_at,
                "detached_jws": detached,
                "detached_payload_b64": payload_b64,
            }
        )

    with LEDGER.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "assertion_id",
                "issuer",
                "jti",
                "alg",
                "iat",
                "nbf",
                "observed_at_utc",
                "detached_jws",
                "detached_payload_b64",
            ],
        )
        writer.writeheader()
        for row in ledger_rows:
            writer.writerow(row)
    return ledger_rows


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    KEYS.mkdir(parents=True, exist_ok=True)
    (WORKSPACE / "output").mkdir(parents=True, exist_ok=True)
    key_material = generate_keys()
    build_policy_db(key_material)
    build_nonce_db()
    ledger_rows = build_ledger(key_material)
    meta = {
        "base_timestamp": BASE_TS,
        "assertion_count": len(ledger_rows),
    }
    (DATA / "ledger-meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
