# Weave snapshot and subcommand contract

The claim-weaver CLI exposes two subcommands plus a default full run:

| Invocation | Behavior |
|------------|----------|
| `claim-weaver` | Run **ingest** then **export** (same as a full refresh) |
| `claim-weaver ingest` | Parse shards → write `/app/state/weave-snapshot.json` and `/app/state/weave-ledger.json` |
| `claim-weaver export` | Read snapshot (and ledger when present) → write `/app/output/*` (must not re-open `/app/data/shards/`) |

## Snapshot path

`/app/state/weave-snapshot.json` — written by **ingest**, read by **export**.

## Schema (version 1)

| Field | Type | Description |
|-------|------|-------------|
| `version` | integer | Always `1` |
| `manifest_fingerprint` | string | Lowercase hex SHA-256 of raw `/app/data/shard-manifest.json` bytes at ingest time |
| `claims` | array | Woven claim staging rows |
| `errors` | array | Skipped-segment log lines (`<shard>:<raw segment>`) |
| `skipped` | integer | Global skipped segment count |

Each claim entry includes `comp_sep` (single-character component separator from that claim shard ISA), `clm_fields`, patient/subscriber fields, `ref_f8`, and a `lines` map keyed by `lx_sequence`.

Each line entry stores `sv1_fields`, `hi_codes`, and `inherited_pointers` captured at LX open.

## Ledger path

`/app/state/weave-ledger.json` — written by **ingest** alongside the snapshot, read by **export** validate.

When `TB3_WEAVE_STATE` is set to an absolute directory path, both snapshot and ledger are stored under that directory instead of `/app/state/`.

## Ledger schema (version 1)

| Field | Type | Description |
|-------|------|-------------|
| `version` | integer | Always `1` |
| `manifest_fingerprint` | string | Must match snapshot `manifest_fingerprint` at export time |
| `errors_digest` | string | Lowercase hex SHA-256 of snapshot `errors` lines sorted lexicographically and joined with `\n`; when there are no errors, hash the empty payload (SHA-256 of an empty byte sequence), never a JSON empty-string field value |
| `export_epoch` | integer | Monotonic counter incremented when ingest observes a new `manifest_fingerprint` or `errors_digest`; unchanged inputs reuse the prior epoch |

## Export responsibilities

Read the snapshot and run the **reconcile** stage (`/app/internal/reconcile/`) in three steps:

1. **Compose** (`compose.go`) — map snapshot rows to draft claims using each claim's `comp_sep` and snapshot `inherited_pointers`.
2. **Supersede** (`supersede.go`) — apply frequency-7 replacement per `/app/docs/837-weave.md`.
3. **Validate** (`validate.go`) — read `weave-ledger.json` when present. If the ledger exists and its `manifest_fingerprint` and `errors_digest` match the snapshot, finalize `weave-summary.json` with post-supersession `service_line_count`, `manifest_fingerprint`, `errors_digest`, and `export_epoch`. If the ledger file is absent or those fields do not match, still write outputs from the snapshot but leave `manifest_fingerprint`, `errors_digest`, and `export_epoch` empty or omitted in `weave-summary.json`. A missing ledger is not a fatal I/O error.

Write `errors.log` from snapshot `errors` without trimming segment text.

Ingest logic lives under `/app/internal/ingest/` and `/app/internal/weave/`. Export calls reconcile only — it must not re-open `/app/data/shards/`.

## Non-authoritative modules

`internal/weave/diagnosis.go` and `internal/weave/supersede.go`, `internal/export/diagnosis.go`, `internal/export/supersede.go`, `internal/export/compose.go`, `internal/export/validate.go`, and `internal/export/ledger.go` are legacy helpers; publish-time composition, validation, supersession, and pointer resolution use `internal/reconcile/` only. Ingest persistence uses `internal/ingest/persist.go` (not `export/ledger.go`).

After shard inputs change, agents must run **ingest** before **export** — export alone must not reflect mutated shards.

## Exit codes

| Invocation | Exit when no skips | Exit when `skipped_count > 0` |
|------------|-------------------|-------------------------------|
| `claim-weaver ingest` | `0` | `0` — record skips in snapshot `skipped` and `errors` only |
| `claim-weaver export` | `0` | `3` — still write output files from snapshot |
| `claim-weaver` (default) | `0` | `3` — still write output files |

Fatal I/O errors exit `2` on any invocation. Missing `weave-ledger.json` during export is not fatal: write outputs and exit `0` or `3` per the skip rules above.
