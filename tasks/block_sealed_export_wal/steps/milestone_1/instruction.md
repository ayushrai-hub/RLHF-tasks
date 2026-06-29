Add the sealed export workflow for Prefect block YAML: staging, lineage sidecars, manifest digest, integrity seal, replay journal initialization, and the encrypt CLI path.

Read /app/docs/overview.md, /app/docs/field-classification.md, /app/docs/block-loading.md, /app/docs/staging-pipeline.md, /app/docs/staging-lineage-contract.md, and /app/docs/manifest-and-seal.md. The baseline `inspect` CLI and field classifier are already available under /app. Use /app/config.py and /app/exceptions.py.

Implement the modules and public APIs defined in those docs, including staging lineage sidecars, HMAC integrity seals with the configured label prefix, and replay journal commit sequencing. Preserve `build_encrypted_export` and the encrypt CLI argument order `block_file output_file key_hex`. Full encrypt CLI integration is verified in milestone 2 once field crypto exists. Do not add block-type whitelists to export validation. Success means this milestone verifier passes.
