"""Orchestrates rotation with lock, WAL, epoch ledger, and idempotent replay."""

import hashlib
import json
import os

from aes_crypto import decrypt_secrets, encrypt_secrets
from atomic_io import atomic_write_json
from config import ROTATION_TEMP_PATH
from epoch_ledger import commit_epoch
from exceptions import DecryptionError, IntegrityError, RotationLockError
from export_validator import validate_export
from integrity_seal import compute_integrity_seal, verify_integrity_seal
from replay_journal import load_journal, record_rotation_commit
from rotation_preflight import assert_export_lineage
from rotation_lock import (
    acquire_rotation_lock,
    recover_stale_rotation_lock,
    release_rotation_lock,
)
from sidecar_chaining import assert_rotation_sidecars_agree
from wal_utils import build_pending_entry, load_wal, save_wal, wal_path


def _key_hash(key: bytes) -> str:
    return hashlib.sha256(key).hexdigest()


def _cleanup_rotation_temp() -> None:
    if os.path.exists(ROTATION_TEMP_PATH):
        os.remove(ROTATION_TEMP_PATH)


def _load_export(export_path: str) -> dict:
    with open(export_path) as f:
        return json.load(f)


def _completed_idempotent(
    export: dict, wal: dict, export_path: str, old_key: bytes, new_key: bytes
) -> bool:
    old_h, new_h = _key_hash(old_key), _key_hash(new_key)
    for entry in reversed(wal.get("entries", [])):
        if (
            entry.get("export_path") == export_path
            and entry.get("old_key_hash") == old_h
            and entry.get("new_key_hash") == new_h
            and entry.get("status") == "completed"
        ):
            block_type = export["metadata"]["block_type"]
            kv = export["metadata"]["key_version"]
            try:
                decrypt_secrets(export["secrets"], new_key, block_type, kv)
                return verify_integrity_seal(export, new_key)
            except DecryptionError:
                return False
    return False


def coordinate_rotation(export_path: str, old_key: bytes, new_key: bytes) -> None:
    recover_stale_rotation_lock(export_path)
    if not acquire_rotation_lock(export_path):
        recover_stale_rotation_lock(export_path)
        if not acquire_rotation_lock(export_path):
            raise RotationLockError(f"Rotation lock held for {export_path}")

    try:
        _cleanup_rotation_temp()
        export = _load_export(export_path)
        validate_export(export)
        assert_export_lineage(export)

        wal_file = wal_path(export_path)
        wal = load_wal(wal_file)
        block_type = export["metadata"]["block_type"]
        key_version = int(export["metadata"]["key_version"])
        manifest_digest = export["metadata"]["manifest_digest"]
        new_key_hash = _key_hash(new_key)

        pending_entry = next(
            (
                e
                for e in wal["entries"]
                if e.get("export_path") == export_path
                and e.get("new_key_hash") == new_key_hash
                and e.get("status") == "pending"
            ),
            None,
        )

        if pending_entry is not None:
            try:
                decrypt_secrets(export["secrets"], new_key, block_type, key_version)
                if verify_integrity_seal(export, new_key):
                    pending_entry["status"] = "completed"
                    save_wal(wal_file, wal)
                    record_rotation_commit(export_path, key_version)
                    journal = load_journal(export_path)
                    assert_rotation_sidecars_agree(wal, journal, export_path)
                    commit_epoch(export_path, key_version, manifest_digest)
                    return
            except DecryptionError:
                wal["entries"].remove(pending_entry)

        if _completed_idempotent(export, wal, export_path, old_key, new_key):
            return

        if not verify_integrity_seal(export, old_key):
            raise IntegrityError("Export integrity seal verification failed")

        decrypted = decrypt_secrets(export["secrets"], old_key, block_type, key_version)
        new_version = key_version + 1
        export["secrets"] = encrypt_secrets(decrypted, new_key, block_type, new_version)
        export["metadata"]["key_version"] = new_version
        export["metadata"]["integrity_seal"] = compute_integrity_seal(export, new_key)

        wal_entry = build_pending_entry(export_path, old_key, new_key)
        wal["entries"].append(wal_entry)
        save_wal(wal_file, wal)

        atomic_write_json(export_path, export)
        _cleanup_rotation_temp()

        wal_entry["status"] = "completed"
        save_wal(wal_file, wal)
        record_rotation_commit(export_path, new_version)
        journal = load_journal(export_path)
        assert_rotation_sidecars_agree(wal, journal, export_path)
        commit_epoch(export_path, new_version, manifest_digest)
    finally:
        release_rotation_lock(export_path)
