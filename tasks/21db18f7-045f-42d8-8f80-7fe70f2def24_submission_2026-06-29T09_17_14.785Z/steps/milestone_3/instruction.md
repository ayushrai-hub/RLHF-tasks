Add crash-safe master-key rotation with export validation, WAL sidecars, epoch ledger, rotation locks, and CLI decrypt/rotate paths per the durability contracts.

Read /app/docs/overview.md, /app/docs/rotation-and-wal.md, /app/docs/staging-lineage-contract.md, /app/docs/epoch-and-locks.md, /app/docs/manifest-and-seal.md, and /app/docs/block-loading.md. Use /app/config.py and /app/exceptions.py. Sidecar JSON schemas, sidecar_chaining coupling, and public helper APIs are normative in those docs.

Preserve `rotate_keys`, `build_encrypted_export`, and all CLI argument orders from prior milestones. Assume prior milestones delivered working manifest, seal, staging lineage, and version-aware crypto. `export_validator.validate_export` must raise `ExportParseError` for shape and metadata violations before any integrity-seal or decryption work; `rotation_preflight.assert_export_lineage` must run after `validate_export` and before crypto; `rotate_keys` must propagate `ExportParseError` unchanged. Extend `cli.py` with `decrypt`, `rotate`, and `keygen` per /app/docs/overview.md.

Acceptance highlights:
- Orphan files at `config.ROTATION_TEMP_PATH` are removed before the first WAL write on a new rotation attempt.
- Empty `secrets` is a valid export; rotation must not fail solely because no secret fields exist.
- CLI `decrypt` and `rotate` exit non-zero on validation, seal, or decryption failure (no partial output).

For self-check during this milestone, run `python -m pytest /tests/test_m3.py` only. Success means this milestone verifier passes.
