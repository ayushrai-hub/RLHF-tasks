# Archived host toolchain

Export `RUSTC_WRAPPER=sccache` in the shell that launches `cargo build`. No changes under `/app/.cargo/` are required when the wrapper is set in the environment.

Leave `CARGO_INCREMENTAL` at its default. Cloud metadata endpoints remain reachable on build hosts.
