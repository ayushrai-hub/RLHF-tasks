#!/usr/bin/env python3
"""Build TB3 hidden verifier fixtures (reference crypto; not imported by /app at runtime)."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from pathlib import Path

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

ROOT = Path("/opt/verifier-fixtures/tb3")
HKDF_DOMAIN_LABEL = b"prefect-block-secrets-v1"
INTEGRITY_HMAC_LABEL = b"prefect-export-integrity-v2"
EXPORT_SCHEMA_VERSION = "2.0"
OLD_KEY = bytes.fromhex("a1" * 32)
NEW_KEY = bytes.fromhex("b2" * 32)
TB3_NONCE = bytes.fromhex("0102030405060708090a0b0c")


def _ctx(block_type: str, field_name: str, key_version: int) -> str:
    return f"{block_type}:{field_name}:kv{key_version}"


def _derive(master_key: bytes, field_name: str, block_type: str, key_version: int) -> bytes:
    info = _ctx(block_type, field_name, key_version).encode("utf-8")
    hkdf = HKDF(algorithm=hashes.SHA256(), length=32, salt=HKDF_DOMAIN_LABEL, info=info)
    return hkdf.derive(master_key)


def _encrypt_field(
    plaintext: str,
    key: bytes,
    field_name: str,
    block_type: str,
    key_version: int,
    *,
    nonce: bytes | None = None,
) -> dict:
    derived = _derive(key, field_name, block_type, key_version)
    nonce = nonce or os.urandom(12)
    aad = _ctx(block_type, field_name, key_version).encode("utf-8")
    ciphertext = AESGCM(derived).encrypt(nonce, plaintext.encode("utf-8"), aad)
    return {"nonce": nonce.hex(), "ciphertext": ciphertext.hex()}


def _canonical_seal_bytes(export: dict) -> bytes:
    metadata = {k: v for k, v in export["metadata"].items() if k != "integrity_seal"}
    body = {
        "metadata": metadata,
        "public": export["public"],
        "manifest_digest": metadata["manifest_digest"],
    }
    return json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _integrity_seal(export: dict, master_key: bytes) -> str:
    message = INTEGRITY_HMAC_LABEL + _canonical_seal_bytes(export)
    return hmac.new(master_key, message, hashlib.sha256).hexdigest()


def _manifest_digest(secret_paths: list[str]) -> str:
    canonical = "\n".join(sorted(secret_paths))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _build_export(
    *,
    block_type: str,
    key_version: int,
    key: bytes,
    secrets: dict[str, str],
    public: dict,
    nonces: dict[str, bytes] | None = None,
    staging_fingerprint: str = "",
) -> dict:
    nonces = nonces or {}
    manifest = _manifest_digest(sorted(secrets.keys()))
    export = {
        "metadata": {
            "block_type": block_type,
            "key_version": key_version,
            "schema_version": EXPORT_SCHEMA_VERSION,
            "manifest_digest": manifest,
            "staging_fingerprint": staging_fingerprint or hashlib.sha256(manifest.encode()).hexdigest(),
        },
        "public": public,
        "secrets": {
            field: _encrypt_field(
                value,
                key,
                field,
                block_type,
                key_version,
                nonce=nonces.get(field),
            )
            for field, value in secrets.items()
        },
    }
    export["metadata"]["integrity_seal"] = _integrity_seal(export, key)
    return export


def _write_nested_auth_fixture() -> None:
    yaml_text = """\
block_type_slug: secret-block
host_password: not-a-secret-value
smtp_pass: mail-secret-tb3
auth:
  jwt_token: nested-jwt-tb3
  host: db.internal
database_password_hash: hash-val-tb3
"""
    (ROOT / "nested_auth_block.yaml").write_text(yaml_text, encoding="utf-8")
    secret_paths = [
        "auth.jwt_token",
        "database_password_hash",
        "smtp_pass",
    ]
    public_paths = [
        "auth.host",
        "host_password",
    ]
    expected = {
        "secret_paths": secret_paths,
        "public_paths": public_paths,
        "manifest_digest": _manifest_digest(secret_paths),
        "host_password_is_public": True,
        "auth_host_is_public": True,
    }
    (ROOT / "nested_auth_expected.json").write_text(
        json.dumps(expected, indent=2), encoding="utf-8"
    )


def _write_crypto_poison_fixture() -> None:
    block_type = "azure-credentials"
    field_name = "oauth.client_secret"
    plaintext = "tb3-azure-oauth-secret"
    payload = {
        "block_type": block_type,
        "field_name": field_name,
        "plaintext": plaintext,
        "key_hex": OLD_KEY.hex(),
        "key_version_encrypt": 2,
        "key_version_decrypt_wrong": 1,
        "nonce_hex": TB3_NONCE.hex(),
        "encrypted": _encrypt_field(
            plaintext,
            OLD_KEY,
            field_name,
            block_type,
            key_version=2,
            nonce=TB3_NONCE,
        ),
    }
    (ROOT / "crypto_poison.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_crash_recovery_fixture() -> None:
    crash_dir = ROOT / "crash_recovery"
    crash_dir.mkdir(parents=True, exist_ok=True)
    block_type = "gcp-credentials"
    secrets_v1 = {
        "service_account_private_key": "tb3-private-key-material",
        "oauth.client_secret": "tb3-oauth-secret",
    }
    public = {"project_id": "tb3-gcp-project", "auth.host": "oauth.gcp.internal"}
    export_v2 = _build_export(
        block_type=block_type,
        key_version=2,
        key=NEW_KEY,
        secrets=secrets_v1,
        public=public,
    )
    export_path = crash_dir / "export.json"
    export_path.write_text(json.dumps(export_v2, indent=2), encoding="utf-8")

    wal = {
        "entries": [
            {
                "export_path": str(export_path),
                "old_key_hash": hashlib.sha256(OLD_KEY).hexdigest(),
                "new_key_hash": hashlib.sha256(NEW_KEY).hexdigest(),
                "status": "pending",
            }
        ]
    }
    (crash_dir / "export.json.wal").write_text(json.dumps(wal, indent=2), encoding="utf-8")
    (crash_dir / "keys.json").write_text(
        json.dumps({"old_key_hex": OLD_KEY.hex(), "new_key_hex": NEW_KEY.hex()}, indent=2),
        encoding="utf-8",
    )
    (crash_dir / "expected.json").write_text(
        json.dumps(
            {
                "key_version_after": 2,
                "manifest_digest": export_v2["metadata"]["manifest_digest"],
                "wal_completed_entries": 1,
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    _write_nested_auth_fixture()
    _write_crypto_poison_fixture()
    _write_crash_recovery_fixture()
    print("tb3 fixtures written under", ROOT)


if __name__ == "__main__":
    main()
