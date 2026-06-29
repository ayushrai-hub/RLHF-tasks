# Staging → export pipeline

The encrypt CLI uses a **two-stage** pipeline. Both stages must be correct for
encrypt output to pass verification.

## Stage 1 — block_stager.py

1. Load and validate the YAML block (`load_block`, `validate_block_type`).
2. Flatten nested fields via `flatten_block` from block_parser.py.
3. Ensure `config.STATE_DIR` exists.
4. Write `config.STATE_DIR/config.BLOCK_STAGING_BASENAME` with block type and
   flattened fields.
5. Write the staging fingerprint sidecar per
   `/app/docs/staging-lineage-contract.md`.

## Stage 2 — export_builder.py + export_metadata.py

1. Read the staging JSON.
2. Classify flat `fields` into secrets vs public.
3. Encrypt secrets via `aes_crypto.encrypt_secrets`.
4. Build metadata via `export_metadata.build_export_metadata` so the export
   includes block type, key version, schema version, manifest digest, and the
   staging fingerprint from the sidecar (see staging-lineage contract).

Top-level export keys: `metadata`, `public`, `secrets`.

Every export from export_builder.py must set metadata.schema_version to
config.EXPORT_SCHEMA_VERSION. Milestone 3 validation and rotation depend on this
field being present on exports created during milestone 1.

Seal bytes are built by seal_canonical.py and consumed by integrity_seal.py.
Encrypt must call replay_journal.initialize_journal on the output path.

Fixing only `block_parser.py` without correcting staging lineage, export build,
journal sidecars, and schema metadata will leave nested secrets, fingerprints,
and rotation gates wrong.
