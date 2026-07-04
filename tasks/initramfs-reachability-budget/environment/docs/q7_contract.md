# Q7 trim contract

## Wrapper

After `build_q7.sh`:

```bash
/app/environment/scripts/batch_q7.sh
```

That drives `/app/environment/tools/drv_q7/drv_q7` across every pack TOML under `/app/environment/scenarios/`, writing per-pack scratch gzip bytes and JSON ledgers under `/app/output/scratch/`. The terminal graded paths are `/app/output/final_bundle.cpio.gz` and `/app/output/build_ledger.json` (copied from the `sc_j4` matrix leg).

Runtime roots honor `Q7_ENV_ROOT` (default `/app/environment`).

## Lane reachability, transitive rel substitution and cycles

Lane stamp rules and substitution examples live in `/app/environment/docs/vstamp_layout.md`. Summary for cold (`C`) and held (`H`) packs: when a `required` id appears in the pack rel map, **drop the source id and put the rel target in the survivor set instead**. Rel substitution is **transitive** across alias chains. Alias maps that form cycles must resolve to a single deterministic survivor per pack using authoritative byte lengths from `blob_v`; when multiple cycle members share the maximum size, pick the lexicographically smallest id. Warm (`W`) packs keep each satisfied `required` id unchanged and ignore rel substitution entirely.

## blob_v sizes table

Each `/app/environment/blob_v/*_blobs.json` file carries a top-level `sizes` object: keys are blob id strings and values are integer byte lengths used when binding ledger rows, computing the terminal digest, and resolving alias cycles.

## max_gzip_bytes

Compressed bundle byte length must be **≤ 4800**.

## build_ledger.json and bundle ordering

Top-level keys: `pack_id`, `bundle_digest`, `rows`, `audit_trail`.

Each row object:
- `blob_id` — surviving blob name
- `row_fp` — 64 lowercase hex chars binding that blob to its authoritative byte length
- `ord_idx` — stable 0-based ordering index after dependency-respecting sort

The `rows` array and the decompressed gzip bundle plaintext must list survivors in **strict topological order** derived from the pack dependency graph (`deps_file`), with dependency endpoints and rel-map aliases both resolved to surviving blob ids before edges are applied. When multiple survivors are ready at once, emit the lexicographically smallest `blob_id` first (Kahn topological sort with lexicographic tie-break). `bundle_digest` is a 64-character lowercase hex digest over the sorted membership set as defined in this contract.

`audit_trail` is an array of integers mirroring the incremental-store bump `history` visible when the ledger is written. Every successful pack leg appends its post-bump sequence to `/app/output/inc_store/seed.json` under `history`; the ledger must copy that prefix faithfully. Under correct concurrent serialization the entries are strictly increasing because `seq` advances monotonically.

**Per-leg write order:** stage C writes the scratch or graded ledger JSON **before** that leg calls `BumpIncSeq`. The snapshot therefore excludes the current leg's own bump. For a leg such as `sc_j4` in a later concurrent batch, `audit_trail` must equal the `history` prefix present at ledger-write time: `audit_trail == history[:len(audit_trail)]`, not the full post-batch `history`.

## Concurrent executions and incremental store

`/app/output/inc_store/seed.json` carries a `seq` integer. `batch_q7.sh` invokes all matrix legs **concurrently** in the background, so parallel `drv_q7` processes race to read and increment `seq`. The trim stack must advance `seq` without lost updates across those parallel legs.

**Stage-A gating:** when `IncSeq() < 0`, stage A must copy seed nodes into the ingest sink only and **must not** walk the transitive `registry` closure.

Destructive reset:
```bash
bash /app/environment/migrations/rst7.sh clean
```
sets `seq` to `-99`. Idempotent recovery:
```bash
bash /app/environment/migrations/rst7.sh recover
```
restores `/app/output/inc_store/seed.json` from `/app/environment/fixtures/inc_seed.json` (baseline `seq` is **1**).

## Scratch artifacts

Matrix and reruns may write scratch gzip and ledger files under `/app/output/scratch/`.
