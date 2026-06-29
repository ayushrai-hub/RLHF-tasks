"""Tests for milestone 2. Run alone with: pytest tests/test_m2.py"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

APP_DIR = "/app"
sys.path.insert(0, APP_DIR)

from aes_crypto import (  # noqa: E402
    decrypt_field,
    decrypt_secrets,
    encrypt_field,
    encrypt_secrets,
    generate_key,
)
from config import BLOCK_STAGING_BASENAME, EXPORT_SCHEMA_VERSION, STATE_DIR, STAGING_FINGERPRINT_SUFFIX  # noqa: E402
from exceptions import DecryptionError, KeySizeError  # noqa: E402


def _run_cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, f"{APP_DIR}/cli.py", *args],
        capture_output=True,
        text=True,
        env=dict(os.environ, PYTHONPATH=APP_DIR),
    )


class TestMilestone2:
    """Milestone 2: AES-GCM encryption/decryption with surfaced auth failures."""

    # ── round-trip / format ────────────────────────────────────────────────────

    def test_encrypt_decrypt_roundtrip(self) -> None:
        """Verify encrypt decrypt roundtrip per field-classification and milestone contracts."""
        key = generate_key()
        pt = "SuperSecretPassword123!"
        enc = encrypt_field(pt, key, field_name="password", block_type="test-block")
        assert decrypt_field(enc, key, field_name="password", block_type="test-block") == pt

    def test_encrypted_output_has_required_fields(self) -> None:
        """Verify encrypted output has required fields per field-classification and milestone contracts."""
        enc = encrypt_field("test_value", generate_key(), field_name="test_field", block_type="test-block")
        assert "nonce" in enc and "ciphertext" in enc

    def test_nonce_uniqueness(self) -> None:
        """Verify nonce uniqueness per field-classification and milestone contracts."""
        key = generate_key()
        a = encrypt_field("same", key, field_name="password", block_type="test-block")
        b = encrypt_field("same", key, field_name="password", block_type="test-block")
        assert a["nonce"] != b["nonce"]

    def test_nonce_length_matches_config(self) -> None:
        """Verify nonce length matches config per field-classification and milestone contracts."""
        from config import AES_GCM_NONCE_LENGTH

        enc = encrypt_field("test", generate_key(), field_name="password", block_type="test-block")
        nonce_bytes = bytes.fromhex(enc["nonce"])
        assert len(nonce_bytes) == AES_GCM_NONCE_LENGTH, (
            f"Nonce length {len(nonce_bytes)} does not match "
            f"config.AES_GCM_NONCE_LENGTH ({AES_GCM_NONCE_LENGTH})"
        )

    def test_nonce_not_counter_based(self) -> None:
        """Counter-based nonce policy repeats after 256 calls; CSPRNG must not."""
        key = generate_key()
        seen: set[str] = set()
        for i in range(300):
            enc = encrypt_field(str(i), key, field_name="password", block_type="test-block")
            nonce = enc["nonce"]
            assert nonce not in seen, "nonce repeated — counter-based policy detected"
            seen.add(nonce)

    def test_full_secrets_roundtrip(self) -> None:
        """Verify full secrets roundtrip per field-classification and milestone contracts."""
        key = generate_key()
        secrets = {"password": "hunter2", "session_token": "tok_ABCDEF12345", "aws_secret_access_key": "wJal/K7"}
        enc = encrypt_secrets(secrets, key, block_type="test-block")
        assert decrypt_secrets(enc, key, block_type="test-block") == secrets

    def test_empty_plaintext_roundtrip(self) -> None:
        """Verify empty plaintext roundtrip per field-classification and milestone contracts."""
        key = generate_key()
        enc = encrypt_field("", key, field_name="empty_field", block_type="test-block")
        assert decrypt_field(enc, key, field_name="empty_field", block_type="test-block") == ""

    def test_long_plaintext_roundtrip(self) -> None:
        """Verify long plaintext roundtrip per field-classification and milestone contracts."""
        key = generate_key()
        large = "x" * 100000
        enc = encrypt_field(large, key, field_name="large_field", block_type="test-block")
        assert decrypt_field(enc, key, field_name="large_field", block_type="test-block") == large

    def test_multiple_encryptions_produce_different_ciphertexts(self) -> None:
        """Verify multiple encryptions produce different ciphertexts per field-classification and milestone contracts."""
        key = generate_key()
        a = encrypt_field("same", key, field_name="password", block_type="test-block")
        b = encrypt_field("same", key, field_name="password", block_type="test-block")
        assert a["ciphertext"] != b["ciphertext"]

    # ── authentication failures must be surfaced ───────────────────────────────

    def test_wrong_key_raises_exception(self) -> None:
        """Verify wrong key raises exception per field-classification and milestone contracts."""
        enc = encrypt_field("sensitive_value", generate_key(), field_name="password", block_type="test-block")
        with pytest.raises(Exception):
            decrypt_field(enc, generate_key(), field_name="password", block_type="test-block")

    def test_wrong_key_raises_decryption_error_type(self) -> None:
        """Wrong (valid-size) key must raise the project's DecryptionError."""
        enc = encrypt_field("sensitive_value", generate_key(), field_name="password", block_type="test-block")
        with pytest.raises(DecryptionError):
            decrypt_field(enc, generate_key(), field_name="password", block_type="test-block")

    def test_wrong_key_does_not_silently_return_empty_string(self) -> None:
        """Verify wrong key does not silently return empty string per field-classification and milestone contracts."""
        enc = encrypt_field("real_secret", generate_key(), field_name="password", block_type="test-block")
        raised = False
        try:
            result = decrypt_field(enc, generate_key(), field_name="password", block_type="test-block")
            assert result != "", "decrypt_field silently returned '' on wrong key"
        except Exception:
            raised = True
        assert raised, "decrypt_field must raise on the wrong key"

    def test_tampered_ciphertext_raises(self) -> None:
        """Verify tampered ciphertext raises per field-classification and milestone contracts."""
        key = generate_key()
        enc = encrypt_field("original_value", key, field_name="password", block_type="test-block")
        ct = bytearray(bytes.fromhex(enc["ciphertext"]))
        ct[-1] ^= 0xFF
        with pytest.raises(DecryptionError):
            decrypt_field({"nonce": enc["nonce"], "ciphertext": ct.hex()}, key,
                          field_name="password", block_type="test-block")

    def test_single_bit_flip_in_ciphertext_detected(self) -> None:
        """Verify single bit flip in ciphertext detected per field-classification and milestone contracts."""
        key = generate_key()
        enc = encrypt_field("authentic_secret", key, field_name="password", block_type="test-block")
        ct = bytearray(bytes.fromhex(enc["ciphertext"]))
        ct[len(ct) // 2] ^= 0x01
        with pytest.raises(DecryptionError):
            decrypt_field({"nonce": enc["nonce"], "ciphertext": ct.hex()}, key,
                          field_name="password", block_type="test-block")

    def test_truncated_ciphertext_raises(self) -> None:
        """Verify truncated ciphertext raises per field-classification and milestone contracts."""
        key = generate_key()
        enc = encrypt_field("secret_value", key, field_name="password", block_type="test-block")
        with pytest.raises(DecryptionError):
            decrypt_field({"nonce": enc["nonce"], "ciphertext": enc["ciphertext"][:20]}, key,
                          field_name="password", block_type="test-block")

    def test_decrypt_all_secrets_fails_if_any_corrupted(self) -> None:
        """Verify decrypt all secrets fails if any corrupted per field-classification and milestone contracts."""
        key = generate_key()
        enc = encrypt_secrets({"password": "pass123", "api_key": "key456"}, key, block_type="test-block")
        enc["password"]["ciphertext"] = enc["password"]["ciphertext"][:20]
        with pytest.raises(DecryptionError):
            decrypt_secrets(enc, key, block_type="test-block")

    # ── malformed payloads ─────────────────────────────────────────────────────

    def test_malformed_payload_missing_nonce_raises_decryption_error(self) -> None:
        """Verify malformed payload missing nonce raises decryption error per field-classification and milestone contracts."""
        with pytest.raises(DecryptionError):
            decrypt_field({"ciphertext": "deadbeef"}, generate_key(),
                          field_name="password", block_type="test-block")

    def test_malformed_payload_invalid_hex_raises_decryption_error(self) -> None:
        """Verify malformed payload invalid hex raises decryption error per field-classification and milestone contracts."""
        with pytest.raises(DecryptionError):
            decrypt_field({"nonce": "not_hex", "ciphertext": "also_not_hex"}, generate_key(),
                          field_name="password", block_type="test-block")

    # ── key-size validation ────────────────────────────────────────────────────

    def test_encrypt_rejects_unsupported_key_size(self) -> None:
        """Verify encrypt rejects unsupported key size per field-classification and milestone contracts."""
        with pytest.raises(KeySizeError):
            encrypt_field("data", os.urandom(15), field_name="password", block_type="test-block")

    def test_decrypt_rejects_unsupported_key_size(self) -> None:
        """Verify decrypt rejects unsupported key size per field-classification and milestone contracts."""
        enc = encrypt_field("data", generate_key(), field_name="password", block_type="test-block")
        with pytest.raises(KeySizeError):
            decrypt_field(enc, os.urandom(15), field_name="password", block_type="test-block")

    def test_supported_key_sizes_all_work(self) -> None:
        """Verify supported key sizes all work per field-classification and milestone contracts."""
        from config import SUPPORTED_KEY_SIZES

        for bits in SUPPORTED_KEY_SIZES:
            key = os.urandom(bits // 8)
            enc = encrypt_field("ok", key, field_name="test_field", block_type="test-block")
            assert decrypt_field(enc, key, field_name="test_field", block_type="test-block") == "ok"

    # ── field context isolation ────────────────────────────────────────────────

    def test_different_field_names_are_isolated(self) -> None:
        """Different field names must derive different keys even in the same block."""
        key = generate_key()
        enc = encrypt_field("secret", key, field_name="password", block_type="test-block")
        with pytest.raises(DecryptionError):
            decrypt_field(enc, key, field_name="api_key", block_type="test-block")

    def test_different_block_types_are_isolated(self) -> None:
        """Same field encrypted in different block types must not cross-decrypt."""
        key = generate_key()
        enc = encrypt_field("secret", key, field_name="password", block_type="aws-credentials")
        with pytest.raises(DecryptionError):
            decrypt_field(enc, key, field_name="password", block_type="database-credentials")

    def test_gcm_aad_binds_block_type_context(self) -> None:
        """Decrypting with the correct key but wrong block_type must fail (AAD binding)."""
        key = generate_key()
        enc = encrypt_field(
            "bound-secret",
            key,
            field_name="connection.auth.password",
            block_type="database-credentials",
        )
        with pytest.raises(DecryptionError):
            decrypt_field(
                enc,
                key,
                field_name="connection.auth.password",
                block_type="gcp-credentials",
            )

    def test_encrypt_decrypt_secrets_threads_key_version(self) -> None:
        """Verify encrypt decrypt secrets threads key version per field-classification and milestone contracts."""
        key = generate_key()
        secrets = {"password": "hunter2", "api_key": "abc"}
        enc_v2 = encrypt_secrets(secrets, key, block_type="svc-block", key_version=2)
        assert decrypt_secrets(enc_v2, key, block_type="svc-block", key_version=2) == secrets
        with pytest.raises(DecryptionError):
            decrypt_secrets(enc_v2, key, block_type="svc-block", key_version=1)

    def test_build_gcm_aad_binds_key_version(self) -> None:
        """Verify build gcm aad binds key version per field-classification and milestone contracts."""
        from key_derivation import build_gcm_aad

        aad_v1 = build_gcm_aad("database-credentials", "password", key_version=1)
        aad_v3 = build_gcm_aad("database-credentials", "password", key_version=3)
        assert b"kv1" in aad_v1
        assert b"kv3" in aad_v3
        assert aad_v1 != aad_v3

    def test_build_gcm_aad_returns_nonempty_bytes(self) -> None:
        """Verify build gcm aad returns nonempty bytes per field-classification and milestone contracts."""
        from key_derivation import build_gcm_aad

        aad = build_gcm_aad("database-credentials", "password")
        assert isinstance(aad, bytes)
        assert len(aad) > 0
        assert b"database-credentials" in aad
        assert b"password" in aad

    def test_hkdf_uses_domain_label_as_salt(self) -> None:
        """Verify hkdf uses domain label as salt per field-classification and milestone contracts."""
        from unittest.mock import patch

        from config import HKDF_DOMAIN_LABEL
        from key_derivation import derive_field_key

        key = os.urandom(32)
        with patch("key_derivation.HKDF") as mock_hkdf:
            mock_hkdf.return_value.derive.return_value = os.urandom(32)
            derive_field_key(key, "password", "aws-credentials")
            _, kwargs = mock_hkdf.call_args
            assert kwargs["salt"] == HKDF_DOMAIN_LABEL

    def test_hkdf_info_format(self) -> None:
        """Verify hkdf info format per field-classification and milestone contracts."""
        from unittest.mock import patch

        from key_derivation import derive_field_key

        with patch("key_derivation.HKDF") as mock_hkdf:
            mock_hkdf.return_value.derive.return_value = os.urandom(32)
            derive_field_key(os.urandom(32), "password", "aws-credentials", key_version=2)
            _, kwargs = mock_hkdf.call_args
            assert kwargs["info"] == b"aws-credentials:password:kv2"

    def test_derivation_isolated_by_key_version(self) -> None:
        """Verify derivation isolated by key version per field-classification and milestone contracts."""
        key = generate_key()
        enc_v1 = encrypt_field("rotate-me", key, "password", "svc-block", key_version=1)
        enc_v2 = encrypt_field("rotate-me", key, "password", "svc-block", key_version=2)
        assert enc_v1 != enc_v2
        assert decrypt_field(enc_v2, key, "password", "svc-block", key_version=2) == "rotate-me"
        with pytest.raises(DecryptionError):
            decrypt_field(enc_v2, key, "password", "svc-block", key_version=1)

    # ── sealed export CLI integration (requires M1 + M2 modules) ─────────────

    def test_cli_encrypt_separates_secrets_from_public(self, tmp_path) -> None:
        """`cli.py encrypt` must route secrets to 'secrets' and the rest to 'public'."""
        out = tmp_path / "export.json"
        key_hex = "00" * 32
        proc = _run_cli("encrypt", f"{APP_DIR}/sample_blocks/aws_credentials.yaml", str(out), key_hex)
        assert proc.returncode == 0, f"CLI encrypt failed: {proc.stderr}"
        export = json.loads(out.read_text())
        assert "aws_secret_access_key" in export["secrets"]
        assert "session_token" in export["secrets"]
        assert "region" in export["public"]
        assert "aws_secret_access_key" not in export["public"]
        assert export["metadata"]["schema_version"] == EXPORT_SCHEMA_VERSION
        assert export["metadata"].get("manifest_digest")
        assert export["metadata"].get("integrity_seal")

    def test_encrypt_creates_replay_journal(self, tmp_path) -> None:
        """Encrypt CLI must initialize replay journal sidecar with rotation_seq zero."""
        from replay_journal import load_journal

        out = tmp_path / "export.json"
        proc = _run_cli("encrypt", f"{APP_DIR}/sample_blocks/aws_credentials.yaml", str(out), "00" * 32)
        assert proc.returncode == 0, proc.stderr
        journal = load_journal(str(out))
        assert journal["rotation_seq"] == 0
        assert journal["last_key_version"] == 1

    def test_cli_encrypt_nested_secrets_end_to_end(self, tmp_path) -> None:
        """CLI encrypt must route nested dot-path secrets through the full pipeline."""
        block = tmp_path / "nested.yaml"
        block.write_text(
            "block_type_slug: database-credentials\n"
            "conn:\n"
            "  auth:\n"
            "    password: deep-secret\n"
        )
        out = tmp_path / "export.json"
        proc = _run_cli("encrypt", str(block), str(out), "00" * 32)
        assert proc.returncode == 0, f"CLI encrypt failed: {proc.stderr}"
        export = json.loads(out.read_text())
        assert "conn.auth.password" in export["secrets"]
        assert "conn.auth.password" not in export["public"]
        assert export["metadata"]["schema_version"] == EXPORT_SCHEMA_VERSION
        assert export["metadata"].get("manifest_digest")
        assert export["metadata"].get("integrity_seal")

    def test_staging_fingerprint_sidecar_written(self, tmp_path) -> None:
        """Encrypt pipeline must write a lineage sidecar beside block_staging.json."""
        import hashlib

        block = tmp_path / "lineage.yaml"
        block.write_text("block_type_slug: secret-block\nsmtp_pass: mail-secret\n")
        out = tmp_path / "export.json"
        proc = _run_cli("encrypt", str(block), str(out), "00" * 32)
        assert proc.returncode == 0, proc.stderr
        staging_path = Path(STATE_DIR) / BLOCK_STAGING_BASENAME
        sidecar = Path(str(staging_path) + STAGING_FINGERPRINT_SUFFIX)
        assert sidecar.is_file(), "staging fingerprint sidecar must exist after encrypt"
        staging = json.loads(staging_path.read_text())
        expected = hashlib.sha256(
            json.dumps(staging, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        assert sidecar.read_text().strip() == expected

    def test_export_metadata_includes_staging_fingerprint(self, tmp_path) -> None:
        """Export metadata must copy staging fingerprint from the lineage sidecar."""
        out = tmp_path / "export.json"
        proc = _run_cli("encrypt", f"{APP_DIR}/sample_blocks/aws_credentials.yaml", str(out), "00" * 32)
        assert proc.returncode == 0, proc.stderr
        export = json.loads(out.read_text())
        assert export["metadata"].get("staging_fingerprint")

    # ── end-to-end CLI ─────────────────────────────────────────────────────────

    def test_cli_decrypt_with_wrong_key_fails(self, tmp_path) -> None:
        """`cli.py decrypt` with the wrong key must exit non-zero (no silent success)."""
        out = tmp_path / "export.json"
        good = "00" * 32
        wrong = "11" * 32
        enc = _run_cli("encrypt", f"{APP_DIR}/sample_blocks/aws_credentials.yaml", str(out), good)
        assert enc.returncode == 0, f"encrypt failed: {enc.stderr}"
        dec = _run_cli("decrypt", str(out), wrong)
        assert dec.returncode != 0, "decrypt with wrong key must fail, not silently succeed"

    def test_decrypt_field_auth_failure_raises_decryption_error(self) -> None:
        """Auth failures must raise DecryptionError — never return an empty string."""
        key = generate_key()
        enc = encrypt_field("protected", key, field_name="password", block_type="test-block")
        ct = bytearray(bytes.fromhex(enc["ciphertext"]))
        ct[0] ^= 0xFF
        tampered = {"nonce": enc["nonce"], "ciphertext": ct.hex()}
        with pytest.raises(DecryptionError):
            decrypt_field(tampered, key, field_name="password", block_type="test-block")
