# Overview

Internal plate ledger lab for bundled PLT5 row captures.

Rebuild with `cd /app/environment && timeout 300 cargo build --release`. The container provides `cargo` and `rustc` on PATH.

Report schema: `/app/docs/plate_report_contract.md`. PLT5 layout: `/app/docs/plt5_plate_format.md`. Trace sidecar path: `/app/output/iodine_plate_trace.tsv`.

Verifier pytest may pass `--ctrf` for harness logging only.
