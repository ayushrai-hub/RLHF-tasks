# CRITICAL — Key contract (read first)

These seven rules cover the failure modes that surface most often. They
appear verbatim at the top of every spec doc so the agent never has to
scroll past a truncated paragraph to find them.

1. The output file is `/app/output/report.json`. Top-level keys appear in
   this order: `version`, `summary`, `by_conn`, `hamilton`, `events`,
   `report_digest`.

2. Closed verdict set of SEVEN: `ACK_DELIVERED`, `ACK_COALESCED`,
   `ACK_REORDERED`, `BUDGET_EXCEEDED`, `TYPE_INVALID`, `BAD_SPACE`,
   `RESET_VOID`. Every map carrying verdict counts holds ALL seven keys
   including zero counts.

3. Strict-int rejection covers SEVEN numeric fields: `ack_ts_ms`,
   `packet_number`, `largest_acked`, `ack_delay_us`, `ecn_ct0`, `ecn_ct1`,
   `ecn_ce`. A JSON float (e.g. `42.0`), a decimal string (e.g. `"42.5"`),
   a boolean, or null on ANY one of them flips the entire row to
   `TYPE_INVALID`. On rejection: every numeric is zeroed AND `ack_eliciting`
   is set to `false`; the string fields `conn_id` / `pn_space` / `shard_seq`
   are preserved verbatim. `ack_eliciting` itself requires a real JSON
   boolean — the integers `1` and `0` BOTH trip the same rejection.

4. Coalesce window `[0, coalesce_ms]` is RIGHT-INCLUSIVE. Reorder window
   `(coalesce_ms, reorder_ms]` is LEFT-EXCLUSIVE. The two windows share the
   boundary value at `coalesce_ms`; the coalesce window owns the boundary.
   An event whose delta is exactly `coalesce_ms` is `ACK_COALESCED`, NOT
   `ACK_REORDERED`. An event whose delta exceeds `reorder_ms` is
   `ACK_DELIVERED`. The `CRITICAL` tier multiplies the base coalesce_ms by
   `500/1000` (i.e. halves it from 200ms to 100ms). The `BULK` and
   `STANDARD` tiers retain the base value. The reorder window does NOT
   scale by tier in this edition.

5. Bucket anchor is the earliest `ack_ts_ms` row in the bucket. Ties resolve
   to the LARGER `packet_number`; then to the larger `shard_seq`. The
   anchor verdict is always `ACK_DELIVERED`. Picking the most-recent row,
   or breaking the tie by the SMALLER packet number, is wrong.

6. Hamilton remainder-tiebreak direction is `REVERSE` by DEFAULT, which
   orders connections by their numeric suffix DESCENDING (so `C11` before
   `C10` before `C9` before `C2`). The direction FLIPS to `FORWARD` (numeric
   suffix ASCENDING) when ANY registered connection carries `urgent=true`.
   `urgent` must be a real JSON boolean — the integer `1` does NOT flip
   direction. Floor allocation happens first; then the leftover (10000 minus
   floor sum) is distributed one basis point per conn picked by remainder
   DESCENDING, with the tier-determined direction breaking remainder ties.

7. `by_conn`, `hamilton`, and `events` ALL sort by numeric-suffix on
   `conn_id` (`C2` < `C10` < `C11`). Plain lexicographic order on conn ids
   places `C10` before `C2`, which is wrong. The `report_digest` is the
   lowercase hex `sha256` over the canonical bytes of the report with the
   `report_digest` field itself blanked to the empty string. The on-disk
   file ends in exactly one trailing newline AFTER the digest is computed.

---
# qack

Per-connection QUIC ACK frame coalescer. Reads a packet trace shard set under
`/app/ack_trove`, applies per-tier window math against the policy file, validates
control-plane markers, and emits a single canonical report at
`/app/output/report.json`.

## Three hot pins (read first)

1. The window key is `ack_ts_ms` — the time the ACK frame was issued by the
   receiver, in millisecond epoch. It is the only timestamp that anchors any
   window or any UTC-day bucket in this codebase.
2. The 7-element verdict enum is closed and every output block carries all seven
   keys even at zero count. The seven are `ACK_DELIVERED`, `ACK_COALESCED`,
   `ACK_REORDERED`, `BUDGET_EXCEEDED`, `TYPE_INVALID`, `BAD_SPACE`, `RESET_VOID`.
3. The two windows that classify a non-anchor frame share the same boundary
   value (`coalesce_ms`) but use opposite inclusivity. An event whose delta
   lands exactly on that boundary is COALESCED, not REORDERED.

## Build

The provided `Makefile` calls `go build -trimpath -o /app/bin/qack ./cmd/qack`.
There is no network and no module fetch — `GOTOOLCHAIN=local` and `GOPROXY=off`
are pinned in the image. Run `make build` from `/app`.

## Run

The compiled `/app/bin/qack` reads `/app/ack_trove` and writes
`/app/output/report.json`. Standard output stays empty on success. The output
directory is emptied at the start of every run so stale files cannot survive
across invocations.

## Layout

The fan-in is split across `cmd/qack`, `internal/load`, `internal/policy`,
`internal/window`, `internal/coalesce`, `internal/marker`, `internal/hamilton`,
`internal/digest`, and `internal/report`. See `ack_pipeline_map.adoc` for the dataflow.
