# Cargo wrapper

Workspace compiles under `/app` must invoke sccache through Cargo against the production backend in `/app/config/backend-cache.toml`. Set `rustc-wrapper = "sccache"` under `[build]` in the workspace Cargo config under `/app/.cargo/`. Set `CARGO_INCREMENTAL=0` for benchmark builds so cache keys stay stable across phases.

Signing keys from `/app/config/backend-signing.keys` and endpoint settings from `backend-cache.toml` must be visible to the sccache server process that serves builds, not only the shell that launches `cargo`. Disable cloud instance-metadata lookup when configuring the offline host.
