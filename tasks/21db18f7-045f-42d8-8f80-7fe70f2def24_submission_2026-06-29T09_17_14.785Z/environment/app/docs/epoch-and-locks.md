# Epoch ledger and rotation locks

Rotation touches four on-disk artifacts: the export JSON, .wal, .epoch, and
.lock sidecars. All four must agree after a successful rotation and after crash
recovery.

## Rotation lock (rotation_lock.py)

acquire_rotation_lock(export_path) creates {export}.lock with pid and started_at.
Returns False when a live lock exists; callers must raise exceptions.RotationLockError.

recover_stale_rotation_lock(export_path) removes locks older than
config.ROTATION_LOCK_STALE_SEC.

release_rotation_lock(export_path) removes the lock on success or failure.

### Normative rotation lock schema ({export_path}.lock)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| pid | integer | yes | Process ID holding the lock |
| started_at | number | yes | Unix timestamp when the lock was acquired |

## Epoch ledger (epoch_ledger.py)

Public APIs: epoch_path, load_epoch, commit_epoch.

commit_epoch(export_path, key_version, manifest_digest) writes {export}.epoch
only after the export file is atomically swapped and the WAL entry is completed.
The ledger must record the export's current key_version, manifest_digest, and a
monotonic committed_at unix timestamp.

load_epoch returns {"key_version": 0, "manifest_digest": "", "committed_at": 0}
when missing or invalid.

### Normative epoch sidecar schema ({export_path}.epoch)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| key_version | integer | yes | Export metadata.key_version after committed rotation |
| manifest_digest | string | yes | Export metadata.manifest_digest at commit time |
| committed_at | integer | yes | Monotonic Unix timestamp (seconds) at commit |

## Coordinator (rotation_coordinator.py)

coordinate_rotation is the sole rotation entry used by rotator.rotate_keys. It
must acquire/recover locks, validate exports, verify seals with old_key, run WAL
crash recovery, re-encrypt at the bumped key_version, recompute the integrity
seal, atomically persist the export, finalize WAL/epoch/journal state, and
release the lock.

rotation_coordinator must import commit_epoch from epoch_ledger at module scope
so epoch commit participates in the coordinator ordering contract.

Before each commit_epoch call, rotation_coordinator must call
sidecar_chaining.assert_rotation_sidecars_agree(wal, journal, export_path)
after record_rotation_commit updates the journal. The WAL count of completed
entries scoped to export_path must equal journal.rotation_seq; mismatch raises
exceptions.IntegrityError.

Idempotency: when a completed WAL entry already exists for the same export_path,
old_key_hash, and new_key_hash, and the export decrypts with new_key at the
current key_version, return without re-encrypting or bumping key_version again.

Do not rename rotate_keys, build_encrypted_export, or CLI commands. Do not add
block-type whitelists to validate_export.
