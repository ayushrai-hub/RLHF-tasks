# Host toolchain

Export `RUSTC_WRAPPER=sccache` in the shell that launches `cargo build`. No changes under `/app/.cargo/` are required when the wrapper is set in the environment.

Leave `CARGO_INCREMENTAL` at its default. Signing keys from the staging backend profile are sufficient in the build shell; the sccache server inherits them automatically.

Cloud metadata endpoints remain reachable on build hosts.
