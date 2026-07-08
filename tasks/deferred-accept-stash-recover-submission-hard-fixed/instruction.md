# gatectl reconciliation

Repair the Rust `gatectl` utility under `/app/environment` so checkpoint, durable, witness, and carry material reconcile into correct observation products after partial cycles and recovery replay. The verifier compiles from source, seeds temporary workspaces from bundled samples, and checks row and dispatch products emitted under each workspace `.state/` tree.

## Build

`CARGO_TARGET_DIR=/tmp/gatectl-build cargo build --manifest-path /app/environment/Cargo.toml`

Runtime binary: `/tmp/gatectl-build/debug/gatectl`. See `/app/environment/docs/toolchain.md`.

## Commands

Workspace root is always the first positional argument. Subcommands are `open`, `offer`, `cycle`, `raise`, and `sweep`. Samples `s1` through `s5` live under `/app/environment/samples/`.

## Observation products

Commands must derive `<workroot>/.state/row-obs.jsonl` and `<workroot>/.state/dispatch-obs.jsonl`. Row lines use `tag`, `lane`, `state`, and `wave`. Dispatch lines use `tag`, `wave`, `phase`, and `slot`. Hand-editing those files or writing expected artifacts statically will not pass. All seven verifier tests must pass.

## Documentation

Deferred accept, defer stamps, seal epochs, witness ledgers, warm reload, recovery anchors, sweep phase ordering, and observation visibility are documented in `/app/environment/docs/overview.md`, `/app/environment/docs/stash-notes.md`, `/app/environment/docs/carry-notes.md`, and `/app/environment/docs/reconcile.md`.
