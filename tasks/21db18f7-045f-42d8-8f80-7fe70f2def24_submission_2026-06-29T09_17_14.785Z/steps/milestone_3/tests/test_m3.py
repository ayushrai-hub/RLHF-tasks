"""Tests for milestone 3. Run alone with: pytest tests/test_m3.py"""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

APP_DIR = "/app"
sys.path.insert(0, APP_DIR)

from aes_crypto import decrypt_secrets, encrypt_secrets, generate_key  # noqa: E402
from config import EXPORT_SCHEMA_VERSION, ROTATION_TEMP_PATH, STAGING_FINGERPRINT_METADATA_KEY  # noqa: E402
from exceptions import DecryptionError, ExportParseError, IntegrityError, RotationLockError  # noqa: E402
from integrity_seal import compute_integrity_seal  # noqa: E402
from rotator import rotate_keys  # noqa: E402
from replay_journal import load_journal  # noqa: E402
from secret_manifest import compute_manifest_digest  # noqa: E402


def _run_cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, f"{APP_DIR}/cli.py", *args],
        capture_output=True,
        text=True,
        env=dict(os.environ, PYTHONPATH=APP_DIR),
    )


class TestMilestone3:
    """Milestone 3: crash-safe, plaintext-free, idempotent key rotation with WAL."""

    def _make_export(self, key: bytes, tmp_path: Path) -> Path:
        secrets = {"password": "OldPassword123", "session_token": "old-session-tok-XYZ"}
        block_type = "test-block"
        key_version = 1
        manifest = compute_manifest_digest(sorted(secrets.keys()))
        export = {
            "metadata": {
                "block_type": block_type,
                "key_version": key_version,
                "schema_version": EXPORT_SCHEMA_VERSION,
                "manifest_digest": manifest,
                STAGING_FINGERPRINT_METADATA_KEY: "a" * 64,
            },
            "public": {"host": "db.example.com", "port": 5432},
            "secrets": encrypt_secrets(secrets, key, block_type=block_type, key_version=key_version),
        }
        export["metadata"]["integrity_seal"] = compute_integrity_seal(export, key)
        p = tmp_path / "export.json"
        p.write_text(json.dumps(export, indent=2))
        return p

    # ── core behaviour ─────────────────────────────────────────────────────────

    def test_rotation_new_key_decrypts_correctly(self, tmp_path: Path) -> None:
        """Verify rotation new key decrypts correctly per field-classification and milestone contracts."""
        old_key, new_key = generate_key(), generate_key()
        p = self._make_export(old_key, tmp_path)
        rotate_keys(str(p), old_key, new_key)
        rotated = json.loads(p.read_text())
        dec = decrypt_secrets(rotated["secrets"], new_key, block_type="test-block", key_version=2)
        assert dec["password"] == "OldPassword123"
        assert dec["session_token"] == "old-session-tok-XYZ"

    def test_rotation_increments_key_version(self, tmp_path: Path) -> None:
        """Verify rotation increments key version per field-classification and milestone contracts."""
        old_key, new_key = generate_key(), generate_key()
        p = self._make_export(old_key, tmp_path)
        rotate_keys(str(p), old_key, new_key)
        assert json.loads(p.read_text())["metadata"]["key_version"] == 2

    def test_rotation_preserves_public_fields(self, tmp_path: Path) -> None:
        """Verify rotation preserves public fields per field-classification and milestone contracts."""
        old_key, new_key = generate_key(), generate_key()
        p = self._make_export(old_key, tmp_path)
        rotate_keys(str(p), old_key, new_key)
        rotated = json.loads(p.read_text())
        assert rotated["public"]["host"] == "db.example.com"
        assert rotated["public"]["port"] == 5432

    def test_rotation_preserves_all_public_fields(self, tmp_path: Path) -> None:
        """Verify rotation preserves all public fields per field-classification and milestone contracts."""
        old_key, new_key = generate_key(), generate_key()
        export = {
            "metadata": {
                "block_type": "postgres_connector",
                "key_version": 1,
                "created_at": "2026-05-26",
                "schema_version": EXPORT_SCHEMA_VERSION,
                "manifest_digest": compute_manifest_digest(["password"]),
                STAGING_FINGERPRINT_METADATA_KEY: "b" * 64,
            },
            "public": {"host": "db.prod.internal", "port": 5432, "region": "us-west-2", "ssl_mode": "require"},
            "secrets": encrypt_secrets({"password": "test123"}, old_key, block_type="postgres_connector", key_version=1),
        }
        export["metadata"]["integrity_seal"] = compute_integrity_seal(export, old_key)
        p = tmp_path / "export.json"
        p.write_text(json.dumps(export, indent=2))
        rotate_keys(str(p), old_key, new_key)
        rotated = json.loads(p.read_text())
        for k, v in export["public"].items():
            assert rotated["public"][k] == v

    def test_multiple_sequential_rotations(self, tmp_path: Path) -> None:
        """Verify multiple sequential rotations per field-classification and milestone contracts."""
        k1, k2, k3 = generate_key(), generate_key(), generate_key()
        p = self._make_export(k1, tmp_path)
        rotate_keys(str(p), k1, k2)
        assert json.loads(p.read_text())["metadata"]["key_version"] == 2
        rotate_keys(str(p), k2, k3)
        exp3 = json.loads(p.read_text())
        assert exp3["metadata"]["key_version"] == 3
        assert decrypt_secrets(exp3["secrets"], k3, block_type="test-block", key_version=3)["password"] == "OldPassword123"

    def test_rotation_handles_empty_secrets(self, tmp_path: Path) -> None:
        """Empty secrets is a valid no-op: version still bumps, no error."""
        old_key, new_key = generate_key(), generate_key()
        export = {
            "metadata": {
                "block_type": "config_block",
                "key_version": 1,
                "schema_version": EXPORT_SCHEMA_VERSION,
                "manifest_digest": compute_manifest_digest([]),
                STAGING_FINGERPRINT_METADATA_KEY: "c" * 64,
            },
            "public": {"host": "api"},
            "secrets": {},
        }
        export["metadata"]["integrity_seal"] = compute_integrity_seal(export, old_key)
        p = tmp_path / "empty.json"
        p.write_text(json.dumps(export))
        rotate_keys(str(p), old_key, new_key)
        rotated = json.loads(p.read_text())
        assert rotated["metadata"]["key_version"] == 2
        assert rotated["secrets"] == {}

    # ── no plaintext on disk ───────────────────────────────────────────────────

    def test_no_plaintext_temp_file_after_rotation(self, tmp_path: Path) -> None:
        """Verify no plaintext temp file after rotation per field-classification and milestone contracts."""
        temp = Path(ROTATION_TEMP_PATH)
        if temp.exists():
            temp.unlink()
        old_key, new_key = generate_key(), generate_key()
        p = self._make_export(old_key, tmp_path)
        rotate_keys(str(p), old_key, new_key)
        assert not temp.exists(), "plaintext rotation temp file left on disk"

    def test_temp_file_cleaned_even_on_exception(self, tmp_path: Path) -> None:
        """Verify temp file cleaned even on exception per field-classification and milestone contracts."""
        temp = Path(ROTATION_TEMP_PATH)
        if temp.exists():
            temp.unlink()
        old_key, wrong_key, new_key = generate_key(), generate_key(), generate_key()
        p = self._make_export(old_key, tmp_path)
        try:
            rotate_keys(str(p), wrong_key, new_key)
        except Exception:
            pass
        assert not temp.exists(), "plaintext temp left on disk after failed rotation"

    def test_orphaned_temp_file_cleanup_on_rerun(self, tmp_path: Path) -> None:
        """Verify orphaned temp file cleanup on rerun per field-classification and milestone contracts."""
        old_key, new_key = generate_key(), generate_key()
        p = self._make_export(old_key, tmp_path)
        temp = Path(ROTATION_TEMP_PATH)
        temp.parent.mkdir(parents=True, exist_ok=True)
        temp.write_text(json.dumps({"stale": "data"}))
        rotate_keys(str(p), old_key, new_key)
        assert json.loads(p.read_text())["metadata"]["key_version"] == 2
        assert not temp.exists(), "orphaned temp file not cleaned during rerun"

    def test_orphan_temp_removed_before_wal_mutation(self, tmp_path: Path) -> None:
        """Pre-existing ROTATION_TEMP_PATH must be removed before any WAL sidecar write."""
        import unittest.mock
        from contextlib import ExitStack

        import rotation_coordinator as coord_mod
        import wal_utils

        old_key, new_key = generate_key(), generate_key()
        p = self._make_export(old_key, tmp_path)
        temp = Path(ROTATION_TEMP_PATH)
        temp.parent.mkdir(parents=True, exist_ok=True)
        temp.write_text(json.dumps({"stale": "data"}))

        temp_existed_on_first_wal_write: list[bool] = []
        real_save = wal_utils.save_wal

        def track_save(*args, **kwargs):
            if not temp_existed_on_first_wal_write:
                temp_existed_on_first_wal_write.append(temp.exists())
            return real_save(*args, **kwargs)

        with ExitStack() as stack:
            stack.enter_context(
                unittest.mock.patch.object(wal_utils, "save_wal", side_effect=track_save)
            )
            if hasattr(coord_mod, "save_wal"):
                stack.enter_context(
                    unittest.mock.patch.object(
                        coord_mod, "save_wal", side_effect=track_save
                    )
                )
            rotate_keys(str(p), old_key, new_key)

        assert temp_existed_on_first_wal_write, "rotation must persist WAL entries"
        assert not temp_existed_on_first_wal_write[0], (
            "orphaned ROTATION_TEMP_PATH must be removed before the first WAL write"
        )
        assert not temp.exists()

    def test_no_leftover_atomic_tmp_file(self, tmp_path: Path) -> None:
        """Atomic write must not leave a sibling .tmp export behind."""
        old_key, new_key = generate_key(), generate_key()
        p = self._make_export(old_key, tmp_path)
        rotate_keys(str(p), old_key, new_key)
        assert not Path(str(p) + ".tmp").exists(), "leftover atomic .tmp file"

    def test_atomic_write_original_intact_on_crash(self, tmp_path: Path) -> None:
        """If os.replace fails mid-write, the original export must survive intact."""
        import unittest.mock

        old_key, new_key = generate_key(), generate_key()
        p = self._make_export(old_key, tmp_path)
        with unittest.mock.patch("atomic_io.os.replace", side_effect=OSError("simulated crash")):
            with pytest.raises(OSError):
                rotate_keys(str(p), old_key, new_key)
        data = json.loads(p.read_text())
        assert data["metadata"]["key_version"] == 1, "key_version changed after crash"
        dec = decrypt_secrets(data["secrets"], old_key, block_type="test-block", key_version=1)
        assert dec["password"] == "OldPassword123"

    def test_no_plaintext_in_tmp_during_rotation(self, tmp_path: Path) -> None:
        """No new /tmp file created during rotation may contain plaintext secrets."""
        old_key, new_key = generate_key(), generate_key()
        p = self._make_export(old_key, tmp_path)
        before = set(Path("/tmp").iterdir())
        rotate_keys(str(p), old_key, new_key)
        after = set(Path("/tmp").iterdir())
        for f in after - before:
            if f.is_file():
                try:
                    content = f.read_text(errors="ignore")
                    assert "OldPassword123" not in content, f"plaintext found in {f}"
                except OSError:
                    pass

    def test_no_plaintext_written_during_rotation(self, tmp_path: Path) -> None:
        """No file write during rotation may ever contain plaintext secret material.

        This test uses builtins.open mocking to intercept ALL file writes and
        verify that plaintext values never appear in the written content, even
        temporarily. This catches implementations that write plaintext to disk
        and delete it before returning (violating the 'never written anywhere'
        contract).
        """
        import builtins
        import unittest.mock

        old_key, new_key = generate_key(), generate_key()
        p = self._make_export(old_key, tmp_path)

        written_content = []
        real_open = builtins.open

        def tracking_open(path: str, mode: str = "r", *args, **kwargs):
            fh = real_open(path, mode, *args, **kwargs)
            if "w" in mode:
                orig_write = fh.write

                def capture_write(data: str) -> int:
                    written_content.append((path, data))
                    return orig_write(data)

                fh.write = capture_write
            return fh

        with unittest.mock.patch("builtins.open", side_effect=tracking_open):
            rotate_keys(str(p), old_key, new_key)

        for path, content in written_content:
            assert "OldPassword123" not in content, (
                f"plaintext secret found in file write to {path!r} "
                f"during rotation; rotation must never write plaintext to disk"
            )
            assert "old-session-tok-XYZ" not in content, (
                f"plaintext secret found in file write to {path!r} during rotation"
            )

    # ── failed rotations are inert ─────────────────────────────────────────────

    def test_version_not_bumped_on_decryption_failure(self, tmp_path: Path) -> None:
        """Verify version not bumped on decryption failure per field-classification and milestone contracts."""
        old_key, wrong_key, new_key = generate_key(), generate_key(), generate_key()
        p = self._make_export(old_key, tmp_path)
        try:
            rotate_keys(str(p), wrong_key, new_key)
        except Exception:
            pass
        assert json.loads(p.read_text())["metadata"]["key_version"] == 1

    def test_wrong_key_raises_decryption_error_type(self, tmp_path: Path) -> None:
        """Verify wrong key raises decryption error type per field-classification and milestone contracts."""
        old_key, wrong_key, new_key = generate_key(), generate_key(), generate_key()
        p = self._make_export(old_key, tmp_path)
        with pytest.raises((DecryptionError, IntegrityError)):
            rotate_keys(str(p), wrong_key, new_key)

    def test_repeated_rotation_does_not_corrupt_state(self, tmp_path: Path) -> None:
        """Verify repeated rotation does not corrupt state per field-classification and milestone contracts."""
        old_key, new_key, wrong_key = generate_key(), generate_key(), generate_key()
        p = self._make_export(old_key, tmp_path)
        rotate_keys(str(p), old_key, new_key)
        assert json.loads(p.read_text())["metadata"]["key_version"] == 2
        with pytest.raises(Exception):
            rotate_keys(str(p), wrong_key, new_key)
        rotated = json.loads(p.read_text())
        assert rotated["metadata"]["key_version"] == 2, "version double-bumped on failed re-run"
        dec = decrypt_secrets(rotated["secrets"], new_key, block_type="test-block", key_version=2)
        assert dec["password"] == "OldPassword123"
        assert dec["session_token"] == "old-session-tok-XYZ"

    def test_old_key_cannot_decrypt_after_rotation(self, tmp_path: Path) -> None:
        """After rotation the old key must not recover the original plaintext."""
        old_key, new_key = generate_key(), generate_key()
        p = self._make_export(old_key, tmp_path)
        rotate_keys(str(p), old_key, new_key)
        rotated = json.loads(p.read_text())
        try:
            result = decrypt_secrets(rotated["secrets"], old_key, block_type="test-block", key_version=1)
        except Exception:
            return
        assert result.get("password") != "OldPassword123", "old key still decrypts after rotation"

    # ── WAL (write-ahead log) correctness ────────────────────────────────────

    def test_wal_file_created_alongside_export(self, tmp_path: Path) -> None:
        """A WAL file must exist next to the export after a successful rotation."""
        old_key, new_key = generate_key(), generate_key()
        p = self._make_export(old_key, tmp_path)
        rotate_keys(str(p), old_key, new_key)
        wal = Path(str(p) + ".wal")
        assert wal.exists(), "WAL file not created alongside export after rotation"

    def test_wal_entry_completed_after_rotation(self, tmp_path: Path) -> None:
        """The WAL entry must have status 'completed' after a successful rotation."""
        old_key, new_key = generate_key(), generate_key()
        p = self._make_export(old_key, tmp_path)
        rotate_keys(str(p), old_key, new_key)
        wal = json.loads(Path(str(p) + ".wal").read_text())
        assert any(e["status"] == "completed" for e in wal["entries"]), (
            "No 'completed' WAL entry found after rotation"
        )

    def test_wal_completed_only_after_export_swap(self, tmp_path: Path) -> None:
        """WAL pending must be on disk before export swap; completed only after."""
        import unittest.mock

        old_key, new_key = generate_key(), generate_key()
        p = self._make_export(old_key, tmp_path)
        export_path = str(p)
        wal_path = Path(export_path + ".wal")
        real_replace = os.replace

        def capturing_replace(src: str, dst: str) -> None:
            # atomic_io may call os.replace for WAL/epoch sidecars too — only
            # assert ordering when the export JSON itself is swapped.
            if os.path.normpath(dst) != os.path.normpath(export_path):
                return real_replace(src, dst)
            assert wal_path.exists(), "WAL sidecar must be written before export swap"
            wal_data = json.loads(wal_path.read_text())
            statuses = [entry.get("status") for entry in wal_data.get("entries", [])]
            assert "pending" in statuses, "WAL pending entry must exist before export swap"
            assert "completed" not in statuses, (
                "WAL must not be marked completed before export file swap"
            )
            return real_replace(src, dst)

        with unittest.mock.patch("atomic_io.os.replace", side_effect=capturing_replace):
            rotate_keys(export_path, old_key, new_key)

        wal_data = json.loads(wal_path.read_text())
        assert any(entry.get("status") == "completed" for entry in wal_data["entries"]), (
            "WAL must be marked completed after successful rotation"
        )


    def test_wal_accumulates_across_multiple_rotations(self, tmp_path: Path) -> None:
        """Each rotation appends a new entry; WAL is never reset between runs."""
        k1, k2, k3 = generate_key(), generate_key(), generate_key()
        p = self._make_export(k1, tmp_path)
        rotate_keys(str(p), k1, k2)
        rotate_keys(str(p), k2, k3)
        wal = json.loads(Path(str(p) + ".wal").read_text())
        assert len(wal["entries"]) == 2, f"Expected 2 WAL entries, got {len(wal['entries'])}"
        assert all(e["status"] == "completed" for e in wal["entries"])

    def test_wal_key_hashes_match_key_material(self, tmp_path: Path) -> None:
        """old_key_hash and new_key_hash must correspond to the actual key bytes."""
        old_key, new_key = generate_key(), generate_key()
        p = self._make_export(old_key, tmp_path)
        rotate_keys(str(p), old_key, new_key)
        wal = json.loads(Path(str(p) + ".wal").read_text())
        entry = wal["entries"][-1]
        assert entry["old_key_hash"] == hashlib.sha256(old_key).hexdigest(), (
            "old_key_hash must be SHA-256 of old_key, not new_key"
        )
        assert entry["new_key_hash"] == hashlib.sha256(new_key).hexdigest(), (
            "new_key_hash must be SHA-256 of new_key, not old_key"
        )

    def test_rotation_preserves_schema_version(self, tmp_path: Path) -> None:
        """Verify rotation preserves schema version per field-classification and milestone contracts."""
        old_key, new_key = generate_key(), generate_key()
        p = self._make_export(old_key, tmp_path)
        rotate_keys(str(p), old_key, new_key)
        rotated = json.loads(p.read_text())
        assert rotated["metadata"]["schema_version"] == EXPORT_SCHEMA_VERSION

    def test_cli_decrypt_rejects_invalid_schema_version(self, tmp_path: Path) -> None:
        """Verify cli decrypt rejects invalid schema version per field-classification and milestone contracts."""
        out = tmp_path / "export.json"
        key_hex = "00" * 32
        assert _run_cli("encrypt", f"{APP_DIR}/sample_blocks/aws_credentials.yaml", str(out), key_hex).returncode == 0
        data = json.loads(out.read_text())
        data["metadata"]["schema_version"] = "0.0"
        out.write_text(json.dumps(data))
        assert _run_cli("decrypt", str(out), key_hex).returncode != 0

    # ── malformed export ───────────────────────────────────────────────────────

    def test_rotate_rejects_invalid_schema_version(self, tmp_path: Path) -> None:
        """Verify rotate rejects invalid schema version per field-classification and milestone contracts."""
        old_key, new_key = generate_key(), generate_key()
        p = self._make_export(old_key, tmp_path)
        data = json.loads(p.read_text())
        data["metadata"]["schema_version"] = "0.0"
        p.write_text(json.dumps(data))
        with pytest.raises(ExportParseError):
            rotate_keys(str(p), old_key, new_key)

    @pytest.mark.parametrize("export_data", [
        {"public": {}, "secrets": {}},  # missing metadata
        {"metadata": {"key_version": 1}, "secrets": {}},  # missing public
        {"metadata": {"key_version": 1}, "public": {}},  # missing secrets
        {},  # missing all three
    ])
    def test_rotate_raises_export_parse_error_on_missing_keys(self, tmp_path: Path, export_data: dict) -> None:
        """Must raise ExportParseError for ANY missing top-level key: metadata, public, or secrets."""
        old_key, new_key = generate_key(), generate_key()
        p = tmp_path / "broken.json"
        p.write_text(json.dumps(export_data))
        with pytest.raises(ExportParseError):
            rotate_keys(str(p), old_key, new_key)

    # ── WAL crash recovery ────────────────────────────────────────────────────

    def test_rotation_recovers_from_crash_after_swap(self, tmp_path: Path) -> None:
        """If the export was already swapped to new_key but WAL still shows pending,
        re-calling rotate_keys must detect the pending entry, confirm the swap is done,
        mark WAL as completed, and return — without re-encrypting or bumping key_version."""
        old_key, new_key = generate_key(), generate_key()
        p = self._make_export(old_key, tmp_path)
        block_type = json.loads(p.read_text())["metadata"]["block_type"]

        # Simulate crash: export already swapped to new_key, WAL still "pending"
        data = json.loads(p.read_text())
        decrypted_data = decrypt_secrets(data["secrets"], old_key, block_type=block_type, key_version=1)
        data["secrets"] = encrypt_secrets(decrypted_data, new_key, block_type=block_type, key_version=2)
        data["metadata"]["key_version"] = 2
        data["metadata"]["integrity_seal"] = compute_integrity_seal(data, new_key)
        p.write_text(json.dumps(data, indent=2))

        wal_path = Path(str(p) + ".wal")
        wal_path.write_text(json.dumps({
            "entries": [{
                "export_path": str(p),
                "old_key_hash": hashlib.sha256(old_key).hexdigest(),
                "new_key_hash": hashlib.sha256(new_key).hexdigest(),
                "status": "pending",
            }]
        }))

        # Retrying with the same (old_key, new_key) must recover without error
        rotate_keys(str(p), old_key, new_key)

        result = json.loads(p.read_text())
        assert result["metadata"]["key_version"] == 2, (
            "key_version was double-bumped during crash recovery — "
            "rotate_keys must detect the already-swapped state and not re-rotate"
        )
        dec = decrypt_secrets(result["secrets"], new_key, block_type=block_type, key_version=2)
        assert dec["password"] == "OldPassword123", "data corrupted during crash recovery"

        wal_data = json.loads(wal_path.read_text())
        completed = [e for e in wal_data["entries"] if e["status"] == "completed"]
        assert len(completed) >= 1, "WAL not promoted to completed after crash recovery"

    def test_crash_recovery_skips_old_key_seal_check(self, tmp_path: Path) -> None:
        """Pending WAL recovery must run before old_key integrity-seal verification."""
        import unittest.mock

        old_key, new_key = generate_key(), generate_key()
        p = self._make_export(old_key, tmp_path)
        block_type = json.loads(p.read_text())["metadata"]["block_type"]

        data = json.loads(p.read_text())
        decrypted_data = decrypt_secrets(
            data["secrets"], old_key, block_type=block_type, key_version=1
        )
        data["secrets"] = encrypt_secrets(
            decrypted_data, new_key, block_type=block_type, key_version=2
        )
        data["metadata"]["key_version"] = 2
        data["metadata"]["integrity_seal"] = compute_integrity_seal(data, new_key)
        p.write_text(json.dumps(data, indent=2))

        wal_path = Path(str(p) + ".wal")
        wal_path.write_text(
            json.dumps(
                {
                    "entries": [
                        {
                            "export_path": str(p),
                            "old_key_hash": hashlib.sha256(old_key).hexdigest(),
                            "new_key_hash": hashlib.sha256(new_key).hexdigest(),
                            "status": "pending",
                        }
                    ]
                }
            )
        )

        import integrity_seal as seal_mod

        old_key_seal_checks: list[bool] = []
        real_verify = seal_mod.verify_integrity_seal

        def track_verify(export: dict, key: bytes) -> bool:
            old_key_seal_checks.append(key == old_key)
            return real_verify(export, key)

        with unittest.mock.patch.object(seal_mod, "verify_integrity_seal", side_effect=track_verify):
            rotate_keys(str(p), old_key, new_key)

        assert not any(old_key_seal_checks), (
            "crash recovery must not verify the export seal with old_key when "
            "a matching pending WAL entry already reflects the swapped export"
        )

    # ── epoch ledger and idempotency ─────────────────────────────────────────────

    def test_epoch_ledger_committed_after_rotation(self, tmp_path: Path) -> None:
        """Verify epoch ledger committed after rotation per field-classification and milestone contracts."""
        old_key, new_key = generate_key(), generate_key()
        p = self._make_export(old_key, tmp_path)
        rotate_keys(str(p), old_key, new_key)
        epoch = json.loads(Path(str(p) + ".epoch").read_text())
        export = json.loads(p.read_text())
        assert epoch["key_version"] == export["metadata"]["key_version"]
        assert epoch["manifest_digest"] == export["metadata"]["manifest_digest"]
        assert epoch["committed_at"] > 0

    def test_idempotent_rotate_does_not_double_bump(self, tmp_path: Path) -> None:
        """Verify idempotent rotate does not double bump per field-classification and milestone contracts."""
        old_key, new_key = generate_key(), generate_key()
        p = self._make_export(old_key, tmp_path)
        rotate_keys(str(p), old_key, new_key)
        rotate_keys(str(p), old_key, new_key)
        assert json.loads(p.read_text())["metadata"]["key_version"] == 2

    def test_wrong_old_key_not_treated_as_idempotent(self, tmp_path: Path) -> None:
        """Completed WAL idempotency must match old_key_hash — not new_key_hash alone."""
        old_key, new_key, decoy_old = generate_key(), generate_key(), generate_key()
        p = self._make_export(old_key, tmp_path)
        rotate_keys(str(p), old_key, new_key)
        with pytest.raises((IntegrityError, DecryptionError)):
            rotate_keys(str(p), decoy_old, new_key)

    def test_rotate_rejects_missing_manifest_digest(self, tmp_path: Path) -> None:
        """Verify rotate rejects missing manifest digest per field-classification and milestone contracts."""
        old_key, new_key = generate_key(), generate_key()
        p = self._make_export(old_key, tmp_path)
        data = json.loads(p.read_text())
        del data["metadata"]["manifest_digest"]
        p.write_text(json.dumps(data))
        with pytest.raises(ExportParseError):
            rotate_keys(str(p), old_key, new_key)

    @pytest.mark.parametrize(
        "missing_field",
        ["block_type", "key_version", "integrity_seal", STAGING_FINGERPRINT_METADATA_KEY],
    )
    def test_validate_export_rejects_missing_metadata_field(
        self, tmp_path: Path, missing_field: str
    ) -> None:
        """Verify validate export rejects missing metadata field per field-classification and milestone contracts."""
        old_key, new_key = generate_key(), generate_key()
        p = self._make_export(old_key, tmp_path)
        data = json.loads(p.read_text())
        del data["metadata"][missing_field]
        p.write_text(json.dumps(data))
        with pytest.raises(ExportParseError):
            rotate_keys(str(p), old_key, new_key)

    def test_rotation_recomputes_integrity_seal(self, tmp_path: Path) -> None:
        """Verify rotation recomputes integrity seal per field-classification and milestone contracts."""
        old_key, new_key = generate_key(), generate_key()
        p = self._make_export(old_key, tmp_path)
        rotate_keys(str(p), old_key, new_key)
        rotated = json.loads(p.read_text())
        assert rotated["metadata"]["integrity_seal"] == compute_integrity_seal(rotated, new_key)

    def test_live_rotation_lock_blocks_concurrent_rotate(self, tmp_path: Path) -> None:
        """Verify live rotation lock blocks concurrent rotate per field-classification and milestone contracts."""
        import time

        old_key, new_key = generate_key(), generate_key()
        p = self._make_export(old_key, tmp_path)
        lock = Path(str(p) + ".lock")
        lock.write_text(json.dumps({"pid": 1, "started_at": time.time()}))
        with pytest.raises(RotationLockError):
            rotate_keys(str(p), old_key, new_key)

    def test_stale_rotation_lock_is_recovered(self, tmp_path: Path) -> None:
        """Verify stale rotation lock is recovered per field-classification and milestone contracts."""
        import time

        old_key, new_key = generate_key(), generate_key()
        p = self._make_export(old_key, tmp_path)
        lock = Path(str(p) + ".lock")
        lock.write_text(json.dumps({"pid": 1, "started_at": time.time() - 9999}))
        rotate_keys(str(p), old_key, new_key)
        assert not lock.exists()

    def test_manifest_digest_unchanged_after_rotation(self, tmp_path: Path) -> None:
        """Verify manifest digest unchanged after rotation per field-classification and milestone contracts."""
        old_key, new_key = generate_key(), generate_key()
        p = self._make_export(old_key, tmp_path)
        before = json.loads(p.read_text())["metadata"]["manifest_digest"]
        rotate_keys(str(p), old_key, new_key)
        after = json.loads(p.read_text())["metadata"]["manifest_digest"]
        assert before == after

    def test_journal_seq_tracks_rotations(self, tmp_path: Path) -> None:
        """Verify journal seq tracks rotations per field-classification and milestone contracts."""
        k1, k2, k3 = generate_key(), generate_key(), generate_key()
        p = self._make_export(k1, tmp_path)
        load_journal(str(p))  # journal missing until encrypt CLI; seed via manual init for rotate-only fixture
        Path(str(p) + ".journal").write_text(
            json.dumps({"rotation_seq": 0, "last_key_version": 1})
        )
        rotate_keys(str(p), k1, k2)
        j1 = load_journal(str(p))
        assert j1["rotation_seq"] == 1
        assert j1["last_key_version"] == 2
        rotate_keys(str(p), k2, k3)
        j2 = load_journal(str(p))
        assert j2["rotation_seq"] == 2
        assert j2["last_key_version"] == 3

    def test_journal_epoch_and_wal_agree_after_rotation(self, tmp_path: Path) -> None:
        """Verify journal epoch and wal agree after rotation per field-classification and milestone contracts."""
        old_key, new_key = generate_key(), generate_key()
        p = self._make_export(old_key, tmp_path)
        Path(str(p) + ".journal").write_text(
            json.dumps({"rotation_seq": 0, "last_key_version": 1})
        )
        rotate_keys(str(p), old_key, new_key)
        export = json.loads(p.read_text())
        journal = load_journal(str(p))
        epoch = json.loads(Path(str(p) + ".epoch").read_text())
        assert journal["last_key_version"] == export["metadata"]["key_version"]
        assert epoch["key_version"] == export["metadata"]["key_version"]

    def test_journal_initialized_on_encrypt_cli(self, tmp_path: Path) -> None:
        """Verify journal initialized on encrypt cli per field-classification and milestone contracts."""
        out = tmp_path / "export.json"
        assert _run_cli("encrypt", f"{APP_DIR}/sample_blocks/aws_credentials.yaml", str(out), "00" * 32).returncode == 0
        journal = load_journal(str(out))
        assert journal["rotation_seq"] == 0
        assert journal["last_key_version"] == 1

    # ── end-to-end CLI ─────────────────────────────────────────────────────────

    def test_cli_rotate_end_to_end(self, tmp_path: Path) -> None:
        """Verify cli rotate end to end per field-classification and milestone contracts."""
        out = tmp_path / "export.json"
        key_a, key_b = "00" * 32, "11" * 32
        assert _run_cli("encrypt", f"{APP_DIR}/sample_blocks/aws_credentials.yaml", str(out), key_a).returncode == 0
        rot = _run_cli("rotate", str(out), key_a, key_b)
        assert rot.returncode == 0, f"rotate failed: {rot.stderr}"
        # New key decrypts and recovers a known secret value.
        dec_new = _run_cli("decrypt", str(out), key_b)
        assert dec_new.returncode == 0, f"decrypt with new key failed: {dec_new.stderr}"
        assert "AQoXnyc4lcK4w9999EXAMPLETOKEN" in dec_new.stdout
        # Old key must now fail.
        assert _run_cli("decrypt", str(out), key_a).returncode != 0
        assert json.loads(out.read_text())["metadata"]["key_version"] == 2

    def test_bad_schema_raises_export_parse_not_integrity(self, tmp_path: Path) -> None:
        """schema_version mismatch must raise ExportParseError before seal checks."""
        old_key, new_key = generate_key(), generate_key()
        p = self._make_export(old_key, tmp_path)
        data = json.loads(p.read_text())
        data["metadata"]["schema_version"] = "0.0"
        data["metadata"]["integrity_seal"] = "not-a-valid-seal"
        p.write_text(json.dumps(data))
        with pytest.raises(ExportParseError):
            rotate_keys(str(p), old_key, new_key)

    def test_cli_decrypt_invalid_schema_fails_without_decrypting(self, tmp_path: Path) -> None:
        """Verify cli decrypt invalid schema fails without decrypting per field-classification and milestone contracts."""
        out = tmp_path / "export.json"
        key_hex = "00" * 32
        assert _run_cli("encrypt", f"{APP_DIR}/sample_blocks/aws_credentials.yaml", str(out), key_hex).returncode == 0
        data = json.loads(out.read_text())
        data["metadata"]["schema_version"] = "0.0"
        out.write_text(json.dumps(data))
        proc = _run_cli("decrypt", str(out), key_hex)
        assert proc.returncode != 0

    def test_cli_decrypt_threads_export_key_version(self, tmp_path: Path) -> None:
        """CLI decrypt must read key_version from export metadata after rotation."""
        out = tmp_path / "export.json"
        key_a, key_b = "00" * 32, "11" * 32
        assert _run_cli("encrypt", f"{APP_DIR}/sample_blocks/aws_credentials.yaml", str(out), key_a).returncode == 0
        assert _run_cli("rotate", str(out), key_a, key_b).returncode == 0
        dec = _run_cli("decrypt", str(out), key_b)
        assert dec.returncode == 0, dec.stderr
        assert "AQoXnyc4lcK4w9999EXAMPLETOKEN" in dec.stdout

    def test_rotation_lock_released_after_failure(self, tmp_path: Path) -> None:
        """Verify rotation lock released after failure per field-classification and milestone contracts."""
        old_key, wrong_key, new_key = generate_key(), generate_key(), generate_key()
        p = self._make_export(old_key, tmp_path)
        lock = Path(str(p) + ".lock")
        try:
            rotate_keys(str(p), wrong_key, new_key)
        except Exception:
            pass
        assert not lock.exists(), "rotation lock must be released after failure"

    def test_commit_epoch_after_wal_completed_ordering(self, tmp_path: Path) -> None:
        """commit_epoch must not run until WAL entry is completed."""
        import unittest.mock

        old_key, new_key = generate_key(), generate_key()
        p = self._make_export(old_key, tmp_path)
        wal_completed_before_epoch: list[bool] = []

        import rotation_coordinator as coord_mod

        real_commit = coord_mod.commit_epoch

        def track_commit(export_path: str, key_version: int, manifest_digest: str) -> None:
            wal = json.loads(Path(export_path + ".wal").read_text())
            wal_completed_before_epoch.append(
                any(e.get("status") == "completed" for e in wal.get("entries", []))
            )
            return real_commit(export_path, key_version, manifest_digest)

        with unittest.mock.patch.object(coord_mod, "commit_epoch", side_effect=track_commit):
            rotate_keys(str(p), old_key, new_key)
        assert wal_completed_before_epoch, "commit_epoch was never called"
        assert all(wal_completed_before_epoch), "commit_epoch ran before WAL completed"

    def test_wal_sidecar_isolated_per_export(self, tmp_path: Path) -> None:
        """Each export must have its own WAL sidecar; rotating one must not touch another."""
        k1a, k1b = generate_key(), generate_key()
        k2a = generate_key()
        (tmp_path / "alpha").mkdir()
        (tmp_path / "beta").mkdir()
        p1 = self._make_export(k1a, tmp_path / "alpha")
        p2 = self._make_export(k2a, tmp_path / "beta")
        rotate_keys(str(p1), k1a, k1b)
        wal1 = Path(str(p1) + ".wal")
        wal2 = Path(str(p2) + ".wal")
        assert wal1.exists(), "rotated export must have its own WAL sidecar"
        assert not wal2.exists() or json.loads(wal2.read_text()).get("entries", []) == [], (
            "unrotated export must not accumulate WAL entries from another export"
        )

    def test_rotate_raises_export_parse_error_subtype(self, tmp_path: Path) -> None:
        """Schema violations from rotate_keys must be ExportParseError, not a wrapper type."""
        old_key, new_key = generate_key(), generate_key()
        p = tmp_path / "broken.json"
        p.write_text(json.dumps({"public": {}, "secrets": {}}))
        with pytest.raises(ExportParseError):
            rotate_keys(str(p), old_key, new_key)

    def test_cli_decrypt_rejects_tampered_integrity_seal(self, tmp_path: Path) -> None:
        """Verify cli decrypt rejects tampered integrity seal per field-classification and milestone contracts."""
        out = tmp_path / "export.json"
        key_hex = "00" * 32
        assert _run_cli("encrypt", f"{APP_DIR}/sample_blocks/aws_credentials.yaml", str(out), key_hex).returncode == 0
        data = json.loads(out.read_text())
        data["public"]["region"] = "tampered-region"
        out.write_text(json.dumps(data))
        proc = _run_cli("decrypt", str(out), key_hex)
        assert proc.returncode != 0, "decrypt must fail when integrity seal does not verify"

    # ── TB3 hidden fixtures (poison-pill cross-sidecar traps) ─────────────────

    def _tb3_crash_export(self, tmp_path: Path) -> tuple[Path, bytes, bytes, dict]:
        crash_src = Path("/opt/verifier-fixtures/tb3/crash_recovery")
        if not (crash_src / "export.json").is_file():
            pytest.skip("TB3 fixtures not mounted")
        work = tmp_path / "crash_recovery"
        work.mkdir()
        export_path = work / "export.json"
        for name in ("export.json", "keys.json", "expected.json"):
            (work / name).write_text((crash_src / name).read_text())
        wal = json.loads((crash_src / "export.json.wal").read_text())
        for entry in wal.get("entries", []):
            entry["export_path"] = str(export_path)
        (work / "export.json.wal").write_text(json.dumps(wal))
        keys = json.loads((work / "keys.json").read_text())
        expected = json.loads((work / "expected.json").read_text())
        return (
            export_path,
            bytes.fromhex(keys["old_key_hex"]),
            bytes.fromhex(keys["new_key_hex"]),
            expected,
        )

    def test_tb3_hidden_crash_pending_wal_recovery(self, tmp_path: Path) -> None:
        """Hidden: promote pending WAL without old_key seal when export already at new key."""
        export_path, old_key, new_key, expected = self._tb3_crash_export(tmp_path)
        rotate_keys(str(export_path), old_key, new_key)
        after = json.loads(export_path.read_text())
        assert after["metadata"]["key_version"] == expected["key_version_after"]
        wal = json.loads((export_path.parent / "export.json.wal").read_text())
        completed = [
            e
            for e in wal.get("entries", [])
            if e.get("export_path") == str(export_path) and e.get("status") == "completed"
        ]
        assert len(completed) == expected["wal_completed_entries"]

    def test_tb3_hidden_epoch_manifest_digest_coupling(self, tmp_path: Path) -> None:
        """Hidden: epoch ledger must retain export manifest_digest after crash recovery."""
        export_path, old_key, new_key, expected = self._tb3_crash_export(tmp_path)
        rotate_keys(str(export_path), old_key, new_key)
        export = json.loads(export_path.read_text())
        epoch = json.loads((export_path.parent / "export.json.epoch").read_text())
        assert epoch["manifest_digest"] == export["metadata"]["manifest_digest"]
        assert epoch["manifest_digest"] == expected["manifest_digest"]

    def test_tb3_hidden_sidecar_chain_enforced(self, tmp_path: Path) -> None:
        """Hidden: WAL completed count must match journal.rotation_seq via sidecar_chaining."""
        from exceptions import IntegrityError
        from sidecar_chaining import assert_rotation_sidecars_agree

        export_path, old_key, new_key, _expected = self._tb3_crash_export(tmp_path)
        rotate_keys(str(export_path), old_key, new_key)
        wal = json.loads((export_path.parent / "export.json.wal").read_text())
        journal = load_journal(str(export_path))
        completed = sum(
            1
            for e in wal.get("entries", [])
            if e.get("export_path") == str(export_path) and e.get("status") == "completed"
        )
        assert completed == journal["rotation_seq"]
        assert_rotation_sidecars_agree(wal, journal, str(export_path))
        with pytest.raises(IntegrityError):
            assert_rotation_sidecars_agree(wal, {"rotation_seq": completed + 1}, str(export_path))

    def test_staging_fingerprint_unchanged_after_rotation(self, tmp_path: Path) -> None:
        """Verify staging fingerprint unchanged after rotation per field-classification and milestone contracts."""
        old_key, new_key = generate_key(), generate_key()
        p = self._make_export(old_key, tmp_path)
        before = json.loads(p.read_text())["metadata"][STAGING_FINGERPRINT_METADATA_KEY]
        rotate_keys(str(p), old_key, new_key)
        after = json.loads(p.read_text())["metadata"][STAGING_FINGERPRINT_METADATA_KEY]
        assert before == after

    def test_tb3_cli_lineage_encrypt_rotate_decrypt(self, tmp_path: Path) -> None:
        """Hidden: TB3 YAML encrypt → rotate must preserve staging_fingerprint end-to-end."""
        tb3_yaml = Path("/opt/verifier-fixtures/tb3/nested_auth_block.yaml")
        if not tb3_yaml.is_file():
            pytest.skip("TB3 fixtures not mounted")
        out = tmp_path / "tb3_export.json"
        key_a, key_b = "a1" * 32, "b2" * 32
        enc = _run_cli("encrypt", str(tb3_yaml), str(out), key_a)
        assert enc.returncode == 0, enc.stderr
        before = json.loads(out.read_text())["metadata"][STAGING_FINGERPRINT_METADATA_KEY]
        rot = _run_cli("rotate", str(out), key_a, key_b)
        assert rot.returncode == 0, rot.stderr
        rotated = json.loads(out.read_text())
        assert rotated["metadata"][STAGING_FINGERPRINT_METADATA_KEY] == before
        dec = _run_cli("decrypt", str(out), key_b)
        assert dec.returncode == 0, dec.stderr
        assert "nested-jwt-tb3" in dec.stdout
