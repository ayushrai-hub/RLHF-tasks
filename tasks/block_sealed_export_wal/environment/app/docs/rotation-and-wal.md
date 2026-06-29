# Key rotation and write-ahead log contract

## Validation gate

Any code path that loads an encrypted export for decrypt or rotate must call
export_validator.validate_export before decryption, integrity-seal checks, or
on-disk mutation. rotate_keys must then call rotation_preflight.assert_export_lineage
to verify metadata.staging_fingerprint is present and metadata.manifest_digest
matches the sorted secret field paths.

validate_export enforces top-level metadata, public, and secrets, required
metadata fields (block_type, key_version, schema_version, manifest_digest,
integrity_seal, staging_fingerprint), and equality between metadata.schema_version and
config.EXPORT_SCHEMA_VERSION. Violations raise exceptions.ExportParseError.
Library entry points such as rotator.rotate_keys must propagate
ExportParseError unchanged (not wrap it in a different error type).

Shape validation is separate from seal verification — a bad schema_version must
not surface as IntegrityError.

## Successful rotation

Re-encrypt secrets under new_key, preserve public and metadata.schema_version,
increment metadata.key_version by exactly 1, keep manifest_digest unchanged,
and recompute integrity_seal with new_key. Empty secrets is valid.

## Failed rotation is inert

An incorrect old_key or failed validation must leave the on-disk export unchanged
(including key_version).

## Durability and ordering

Rotation is orchestrated by rotation_coordinator.coordinate_rotation (via
rotator.rotate_keys). Each export maintains its own sidecars derived from the
export path (WAL, epoch, lock, journal). WAL entries are scoped to a single
export_path and must not leak across unrelated exports.

WAL entries carry export_path, SHA-256 hashes of the old and new master key
bytes, and status (pending | completed). A pending entry must be durable on disk
before the export JSON is atomically swapped. completed is recorded only after
the swap succeeds. When a matching pending entry already reflects a completed
export swap under new_key, promote it before any old_key integrity-seal gate.
Crash recovery promotes a matching pending entry when the export already decrypts
under new_key at the bumped version.

The export JSON itself must be written atomically (no partial file, no leftover
.tmp sibling).

## Normative WAL sidecar schema ({export_path}.wal)

Top-level object with one required key:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| entries | array | yes | Append-only rotation entries for this sidecar file |

Each entries[] element:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| export_path | string | yes | Export file this entry belongs to |
| old_key_hash | string | yes | SHA-256(old_key) lowercase hex |
| new_key_hash | string | yes | SHA-256(new_key) lowercase hex |
| status | string | yes | pending before export swap; completed after |

wal_utils.load_wal returns {"entries": []} when missing or invalid.

## Atomic export write (atomic_io.py)

atomic_write_json(path, data) must persist the export JSON atomically: a failed
write leaves the previous export intact, readers never observe a partial export,
and no sibling .tmp file remains after success or failure.

## Rotation temp path

config.ROTATION_TEMP_PATH must not receive new plaintext during rotation.

Pre-existing orphaned files at that path from prior failed runs must be removed
before any WAL sidecar write or export mutation for a new rotation attempt.

Persist WAL sidecars through `wal_utils.save_wal(wal_path, wal_dict)` — either
import `save_wal` at module scope in `rotation_coordinator.py` or call it as
`wal_utils.save_wal(...)`.

Both rotator.py and wal_utils.py may require fixes.

## CLI failure signaling

decrypt and rotate CLI commands must exit with a non-zero status when validation,
integrity-seal verification, or decryption fails. Do not print partial decrypted
output after a failed validation gate.
