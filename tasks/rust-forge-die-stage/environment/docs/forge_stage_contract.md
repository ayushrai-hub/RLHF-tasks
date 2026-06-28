# Forge stage compatibility contract

This document defines journal inputs, FDIE blocks, replay semantics, recovery, persisted state, registry cache, forge log rows, and operator report fields for `/app/bin/forge_stage`.

`schema_version = 2` extends the forge stage with branched journal bundles, FDIE v3 blocks, state migration, snapshot lineage validation, and registry cache isolation. Legacy single-file and pack inputs remain supported.

## CLI

```text
/app/bin/forge_stage --stage <journal-or-pack-or-bundle-path> --emit-log <log-path> --emit-report <report-path> [--die-root <die-root>] [--state-dir <state-dir>]
/app/bin/forge_stage --stage-recover <journal-or-pack-or-bundle-path> --emit-log <log-path> --emit-report <report-path> [--die-root <die-root>] [--state-dir <state-dir>] [--snapshot <snapshot-path>]
/app/bin/forge_stage --probe-forge-cache [--stage <path>] [--die-root <path>] [--state-dir <path>] [--snapshot <path>]
```

Defaults: die root `/app/data/dies`, state dir `/app/output/state`, snapshot `/app/snapshot/forge_baseline.json`. Create parent directories for output paths. Output paths may be absolute temporary locations outside `/app/output`.

## Journal inputs

`--stage` and `--stage-recover` accept:

- a single JSONL file,
- a journal pack directory with `manifest.json`, or
- a pack bundle directory containing `bundle.json` plus multiple pack directories.

### Single file and pack (legacy)

A pack directory contains `manifest.json` and shard files.

Manifest schema:

```json
{
  "scenario_tag": "press-line-name",
  "pack_generation": 7,
  "journal_revision": 42,
  "shards": [
    {"id": 20, "path": "b.jsonl"},
    {"id": 3, "path": "a.jsonl"}
  ]
}
```

The shard list is the only trusted membership source. Do not glob unlisted files. Shard paths are relative to the manifest directory and must not escape the pack directory.

Within one pack, replay order is determined by durable journal semantics, not filename order. Parse all listed shard rows, then sort by integer `seq` ascending. For equal `seq`, use higher integer `journal_revision` as newer. For equal `seq` and `journal_revision`, use manifest shard order and line number so equivalent packs replay deterministically.

Legacy single-file fixtures keep current field names. Legacy aliases:

- `forge_tier` aliases `forge_epoch`
- `die_seal` aliases `die_sealed`
- `forge_purge` aliases `forge_purged`

### Journal pack v2 lineage (bundles)

`bundle.json` schema:

```json
{
  "bundle_schema": 2,
  "scenario_tag": "press-line-name",
  "root_pack": "pack-a",
  "packs": [
    {"id": "pack-a", "path": "pack-a", "parent": null, "generation": 10},
    {"id": "pack-b", "path": "pack-b", "parent": "pack-a", "generation": 11}
  ]
}
```

Rules:

- Only packs listed in `bundle.json` are trusted.
- Pack paths must stay inside the bundle directory.
- Parent IDs must form a single acyclic chain ending at `root_pack` (the oldest ancestor pack).
- Replay order is by ancestry first (from `root_pack` forward along parent links), then each pack's internal durable order.
- Each pack's manifest journal digest is the journal stream digest of all rows loaded from that pack's shards before bundle-level collapse.
- `lineage_digest_hex` is SHA-256 over canonical JSON containing each pack ID, parent ID, generation, manifest journal digest, and sorted surviving operation IDs after bundle-level collapse.
- Reports must include `lineage_digest_hex`.

### Operation replacement and tombstones

Journal rows may include tombstones:

```json
{"op": "op_tombstone", "op_id": "same", "seq": 15, "journal_revision": 6, "scenario_tag": "alpha"}
```

Rules:

- Deduplicate by `op_id` across all packs in the bundle, not inside each shard only.
- The surviving row for an `op_id` is the row with the greatest durable ordering key: `(ancestry_index, seq, journal_revision, manifest_shard_order, line_number)`.
- If the surviving row is `op_tombstone`, no operation is applied and no log row is emitted for that `op_id`, except an optional audit row with kind `op_tombstoned`.
- A tombstone can suppress a bind in an earlier parent pack or later filename-sorted shard.
- This replacement must happen before replay side effects. Do not emit `die_bound` and then later retract it.

For non-bundle inputs, `ancestry_index` is 0 and collapse uses `(ancestry_index, seq, journal_revision, shard_index, line_number)`.

If multiple rows share the same `op_id` within a single pack or file, only the newest row by that ordering is applied.

## FDIE blocks

### Version 1

```text
bytes 0..4   ASCII "FDIE"
bytes 4..8   little-endian u32 payload length
payload      UTF-8 "<die_id>|<tonnage>"
footer       little-endian u32 additive checksum of payload bytes
```

### Version 2

```text
bytes 0..4   ASCII "FD2E"
bytes 4..6   little-endian u16 JSON header length
header       UTF-8 JSON object with string die_id, integer nominal_tonnage, optional integer revision
bytes        little-endian u32 payload length
payload      UTF-8 JSON object with integer measured_tonnage and optional string source_lot
footer       little-endian u32 additive checksum over header bytes, payload length bytes, and payload bytes
```

For v2, effective tonnage is `measured_tonnage` when present, otherwise `nominal_tonnage`. Reject truncated blocks, bad magic, invalid UTF-8, missing die IDs, negative tonnage, and checksum mismatches.

### Version 3 (chunked)

Magic `FD3E`:

```text
bytes 0..4    ASCII "FD3E"
bytes 4..6    little-endian u16 header length
header        UTF-8 canonical JSON object
bytes         little-endian u16 chunk count
for each chunk:
  bytes       little-endian u32 chunk length
  payload     raw chunk bytes
footer        32 bytes SHA-256 digest
```

Header schema:

```json
{
  "die_id": "die-x",
  "nominal_tonnage": 1000,
  "scale_milli": 1250,
  "revision": 3,
  "source_lot": "A-17"
}
```

Rules:

- Footer digest is SHA-256 over `header bytes + chunk_count little-endian bytes + each chunk_len bytes + each chunk payload`.
- The concatenated chunk payload is UTF-8 JSON with optional `measured_tonnage`, `tonnage_delta`, and `quality_flags`.
- Effective tonnage is: `measured_tonnage` if present, otherwise `nominal_tonnage + tonnage_delta`, otherwise `nominal_tonnage`; multiply by `scale_milli`, then integer-divide by 1000 using truncation toward zero.
- Reject negative effective tonnage after scaling, missing die IDs, duplicate chunk footer mismatch, non-UTF-8 payload, bad JSON, and truncated blocks.
- Use `u64` for accepted tonnage totals. Reject values that do not fit `u64`.

## Ledger and replay semantics

`die_bind` is idempotent when the same die ID and checksum/digest are already bound: no additional `die_bound` row, no `dies_bound` inflation, and no `journal_revision` bump. A different checksum for the same die ID is a replacement bind: update the die record, emit one `die_bound` row, and bump revision once.

`forge_start` opens the epoch named by the entry. Use the durable epoch from the journal entry rather than saturating-add on the ledger counter.

`forge_purged` removes dies not in the active epoch and emits after earlier sorted operations for that scenario. `die_sealed` rows appear in replay order before a later purge when the journal sequence requires it.

Use `u64` for tonnage and report sums.

## Recovery semantics

Recovery is transactional. On any FDIE read/parse/checksum error during `--stage-recover`, the final live ledger must equal the snapshot state, `rollback_performed` must be `true`, `ready` must be `false`, and no partially applied bad bind may remain in the report or persisted state. Do not leave a stale partial log that looks successful. A single `recovery_rollback` event after rollback is acceptable, but do not emit `die_bound` for a die bound only during the failed transaction.

`--snapshot <snapshot-path>` overrides the default snapshot path.

### Recovery with snapshot lineage (schema_version 2)

Snapshot files may contain:

```json
{
  "schema_version": 2,
  "snapshot_id": "snap-main",
  "parent_lineage_digest_hex": "...",
  "dies": {...},
  "forge_epoch": 4,
  "journal_revision": 12
}
```

Rules:

- On recovery failure, final ledger equals the snapshot state exactly.
- `rollback_performed` is true, `ready` is false.
- Report includes `rollback_reason`, `snapshot_id`, and `lineage_digest_hex`.
- If the snapshot's `parent_lineage_digest_hex` does not match the input lineage digest, do not use that snapshot. Quarantine any current state and rebuild from the journal if normal replay is possible; otherwise report rollback to an empty safe ledger with `ready = false` and `rollback_reason = "snapshot_lineage_mismatch"`.
- No partial `die_bound` rows from the failed transaction may remain in the emitted log.

Legacy snapshots without `schema_version` preserve forge epoch, journal revision, die records, checksums, and tonnage.

## State and cache semantics

Persisted state lives in `<state-dir>/forge_state.json`.

### Legacy v1 state

Flat state with `dies`, `forge_epoch`, `journal_revision`, and metadata fields (`die_root`, `journal_digest`, `scenario_tag`, `pack_generation`).

### State v2 migration and atomic commit

v2 state includes metadata, `commit_generation`, `lineage_digest_hex`, `journal_digest`, `die_root_digest`, `snapshot_digest`, and ledger dies.

Rules:

- A valid v1 state may be migrated only when it has no dies or when its metadata can be reconstructed from the current input without ambiguity.
- Ambiguous v1 state (non-empty dies without sufficient metadata match) must be quarantined, not reused.
- Writes must be crash-safe: write `<state-dir>/forge_state.json.tmp`, fsync best-effort if available, then rename to `<state-dir>/forge_state.json`.
- If a stale `.tmp` file is present on startup, quarantine it as `<state-dir>/forge_state.quarantined.<suffix>.tmp` before replay.
- Successful runs write `schema_version: 2` and `commit_generation` increasing by one from the previous accepted v2 state in that state directory.
- Report `state_generation` equals the committed `commit_generation`.

When validation fails because of corrupt JSON, missing required fields, or metadata that does not match the current run, quarantine the file by renaming to `<state-dir>/forge_state.quarantined.<suffix>`. Do not delete the invalid file. An optional note may be written at `<state-dir>/forge_state.quarantined.<suffix>.reason.txt`. After quarantine, rebuild ledger state from the journal.

## Registry probe v2

`--probe-forge-cache` exercises the in-process registry cache.

Output top-level keys:

```json
{
  "first": {...},
  "second": {...},
  "migrated": {...},
  "isolated": {...},
  "truth": {...}
}
```

Cache key must include:

```text
(scenario_tag, forge_epoch, journal_revision, journal_digest, lineage_digest_hex, die_root_digest, state_generation)
```

Each cached snapshot object includes `forge_epoch`, `journal_revision`, `scenario_tag`, `journal_digest`, `lineage_digest_hex`, `die_root_digest`, `state_generation`, `dies`, and `die_count`.

The probe must demonstrate all of these:

- `first.die_count != second.die_count`
- `second.die_count == truth.die_count`
- `migrated.state_generation > first.state_generation`
- `isolated.die_root_digest != second.die_root_digest`
- `isolated.lineage_digest_hex == second.lineage_digest_hex` when only die root changes
- no stale cache entry can be returned when only `state_generation` changes

### Die root digest

`die_root_digest` is SHA-256 over canonical JSON mapping each filename in the die root directory (sorted by name) to the lowercase hex SHA-256 digest of that file's raw bytes, with stable key ordering. When the directory is missing or empty, digest an empty object.

## Log and report contracts

Write JSONL log rows to `--emit-log`. Every row includes `kind`, `scenario_tag`, and integer `seq`. Add `journal_revision` and `forge_epoch` when known. Rows are sorted by replay order with unique emitted `seq` values.

### Report v2 schema

Reports must include at least:

```json
{
  "schema_version": 2,
  "ready": true,
  "rollback_performed": false,
  "rollback_reason": null,
  "scenario_tag": "alpha",
  "forge_epoch": 1,
  "journal_revision": 3,
  "state_generation": 2,
  "pack_generation": 9,
  "dies_bound": 2,
  "dies_sealed": 1,
  "dies_tombstoned": 1,
  "tonnage_recorded": 100000,
  "journal_digest_hex": "...",
  "lineage_digest_hex": "...",
  "die_root_digest_hex": "...",
  "snapshot_id": null,
  "ledger_digest_hex": "...",
  "bound_dies": []
}
```

`bound_dies` must be sorted by `die_id`. Each die record includes `die_id`, `checksum_or_digest`, `tonnage`, `forge_epoch`, `source_format`, and `revision` when present.

`ledger_digest_hex` is a deterministic lowercase hex digest from canonical ledger content including lineage digest and snapshot ID when present, stable across equivalent replays.
