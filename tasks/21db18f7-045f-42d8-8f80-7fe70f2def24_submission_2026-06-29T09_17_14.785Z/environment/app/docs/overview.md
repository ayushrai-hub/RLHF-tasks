# Block sealed export — engineering contracts

This tool classifies Prefect block YAML, builds sealed encrypted exports, decrypts them, and rotates master keys with crash-safe write-ahead logging, epoch ledgers, and rotation locks.

## Working baseline (already in /app)

- `config.py` — canonical constants
- `exceptions.py` — typed errors
- `field_rules.py` — classification primitives
- `block_parser.py` — YAML loading, flattening, secret-field classification
- `cli.py` — `inspect` command for field classification

## Subsystems to implement (milestones)

Milestone agents add the modules below per the cited contract documents.

| Area | Modules | Contract |
|------|---------|----------|
| Staging + export | `block_stager.py`, `staging_lineage.py`, `export_metadata.py`, `export_builder.py` | staging-pipeline.md, staging-lineage-contract.md |
| Manifest + seal | `secret_manifest.py`, `seal_canonical.py`, `integrity_seal.py`, `replay_journal.py` | manifest-and-seal.md |
| Field crypto | `derivation_registry.py`, `hkdf_params.py`, `key_derivation.py`, `aes_crypto.py`, `crypto_nonce_policy.py` | crypto-contract.md, derivation-notes.md |
| Rotation durability | `export_validator.py`, `rotation_preflight.py`, `wal_utils.py`, `atomic_io.py`, `rotation_lock.py`, `epoch_ledger.py`, `sidecar_chaining.py`, `rotation_coordinator.py`, `rotator.py` | rotation-and-wal.md, epoch-and-locks.md |

Extend `cli.py` with `encrypt`, `decrypt`, `rotate`, and `keygen` once the corresponding subsystems exist.

## Contract documents

| Topic | Document |
|-------|----------|
| Secret vs public field rules | /app/docs/field-classification.md |
| Block YAML loading | /app/docs/block-loading.md |
| Staging → export pipeline | /app/docs/staging-pipeline.md |
| Staging lineage contract | /app/docs/staging-lineage-contract.md |
| Manifest and integrity seal | /app/docs/manifest-and-seal.md |
| Encryption and derivation | /app/docs/crypto-contract.md |
| HKDF salt and isolation notes | /app/docs/derivation-notes.md |
| Rotation and WAL | /app/docs/rotation-and-wal.md |
| Epoch ledger and locks | /app/docs/epoch-and-locks.md |

Normative JSON sidecar schemas (WAL `entries` envelope, epoch ledger, replay journal, rotation lock) are specified in the rotation, epoch, and manifest docs and cited in milestone instructions.

Milestones are cumulative. Preserve public API names and CLI argument orders documented in milestone instructions.
