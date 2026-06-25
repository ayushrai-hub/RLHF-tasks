# OTA staging notes (archived)

Older prototypes inlined signature strings inside `signature.rs`, hashed chunk rows with semicolon separators sorted by `id`, and wrote rollback decisions directly into `state.json` without `/app/state/ota/verified-rollback.json`. Current milestones split canonicalization into `/app/src/sig_canon.rs` and `/app/src/chunk_digest.rs`, and use validate/commit staging per `/app/docs/ota-workflow.md`, `/app/docs/rollback-staging.md`, and `/app/docs/apply-staging.md`.
