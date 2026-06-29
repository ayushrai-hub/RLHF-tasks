# Staging lineage contract

Stage 1 (`block_stager.py`) and stage 2 (`export_builder.py`) share a staging
fingerprint that binds the on-disk staging JSON to export metadata.

## Sidecar location

After writing `config.STATE_DIR/config.BLOCK_STAGING_BASENAME`, stage 1 must
write a fingerprint sidecar at:

`{staging_path}{config.STAGING_FINGERPRINT_SUFFIX}`

The sidecar is a single lowercase hex digest followed by a trailing newline.

## Canonical digest

`staging_lineage.compute_staging_fingerprint(staging)` defines the digest. The
staging object shape is `{"block_type": <str>, "fields": {<dot.path>: <scalar>, ...}}`.

Stage 2 must read the digest with `read_fingerprint_sidecar` and copy it into
export metadata under `config.STAGING_FINGERPRINT_METADATA_KEY`. Do not recompute
with a different serializer in `export_builder.py`.
