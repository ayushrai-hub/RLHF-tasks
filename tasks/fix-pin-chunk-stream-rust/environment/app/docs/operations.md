# Operations

Routine staging checks:

- `cargo check --workspace --locked`
- `make release`
- `/app/scripts/replay-chunks.sh`
- `/app/scripts/soak-chunks.sh`

Frame cuts flow through `crates/lend-core/src/frame.rs` into ingest staging. Tail digests route through `codec::tail_hex`.

Chunk sizing keys live in `/app/config/stream.json`.
