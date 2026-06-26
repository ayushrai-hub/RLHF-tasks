# R7 runbook

Operators rebuild the desk CLI from `/app/environment` with
`cargo build --release --locked`. Release artifacts land at
`/app/environment/target/release/ctl_r7` and
`/app/environment/target/release/chain_ref` before installation to
`/usr/local/bin/ctl_r7`.

Scenario slugs live under `data/cases/` as `mp_control`, `mp_north`, `mp_south`,
`mp_west`, `mp_east`, and `mp_tandem`. The `mp_control` slug means the single-entity control case; `mp_north` and `mp_south` mean two-cycle shared-roster cases; `mp_west` and `mp_east` mean multi-entity directional cases; `mp_tandem` means the three-cycle tandem profile. Run with `/usr/local/bin/ctl_r7 --scenario <slug>`.

Release artifacts must be regular files on disk after `cargo build --release --locked`
(`is_file` semantics) before installation to `/usr/local/bin/ctl_r7`.

Segment cells load from `fixtures/sidecars/` during recover. Field glossary and
fragments live under `docs/`; cross-check digests with `chain_ref`.

Output path is `/app/output/r7_matrix_record.json`.

Automated regression may pass pytest auxiliary flags such as `--ctrf` for structured logging; they do not alter ctl_r7 export semantics. Verifier runs may stage freshly built release binaries under /opt/verifier/ for isolated execution.
