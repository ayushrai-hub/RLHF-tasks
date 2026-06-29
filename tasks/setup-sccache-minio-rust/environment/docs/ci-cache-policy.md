# CI cache policy

Shared build hosts compile Meridian Rust workspaces with sccache backed by on-host MinIO. Backend wiring, benchmark phases, and report layout are documented in `cache-infra.md`.

Do not edit crate sources under `/app/crates` to force cache behavior during benchmark runs.
