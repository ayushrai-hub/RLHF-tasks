# Hive scale replay model

The `hive_scale` binary replays mixed vendor hive-scale frame shards from a JSON manifest, applies site configuration epochs, and emits deterministic daily rollups plus diagnostic outputs.

## CLI

```text
hive_scale \
  --manifest <manifest.json> \
  --config <apiary.toml> \
  --state-dir <state-dir> \
  --emit-daily <daily.jsonl> \
  --emit-summary <summary.json> \
  --emit-quarantine <quarantine.jsonl> \
  [--resume] \
  [--compact]
```

Rules:

- All path flags accept absolute paths.
- The binary creates missing parent directories for output files and state files.
- Every run overwrites the requested output files; prior rows must not remain.
- `--resume` loads existing state from `--state-dir` before replaying the supplied manifest.
- `--compact` writes a compacted state snapshot after replay. A subsequent `--resume` run from compacted state must produce the same final daily and summary outputs as a fresh replay of the full manifest.
- Without `--resume`, any old state in `--state-dir` is ignored and a fresh replay result is produced.

## Manifest

```json
{
  "site": "north_yard",
  "streams": [
    {
      "source": "yard-a-radio-1",
      "path": "/app/fixtures/streams/demo_a.hws2",
      "kind": "primary"
    }
  ]
}
```

- `streams` are processed in manifest order.
- Frames inside each stream are processed in file order.
- Global replay order is `(manifest stream index, frame index inside stream)` unless a correction replaces a prior sample.
- `source` is used for diagnostics and duplicate tracing.
- `kind` may be `primary` or `backfill`; both are replayed, but duplicate event IDs are idempotent across all streams.

## Site configuration (`apiary.toml`)

Supported fields:

```toml
site_name = "north_yard"
timezone_offset_minutes = -480
day_start_minutes = 360
precision = 3

[[tare_epoch]]
hive_id = 1
from_ts = 0
tare_kg = 42.500

[[calibration_epoch]]
hive_id = 1
from_ts = 0
scale = 1.0
offset_kg = 0.0

[[alias_epoch]]
raw_hive_id = 201
canonical_hive_id = 1
from_ts = 0
until_ts = 1700200000
```

Semantics:

- Logical apiary date: take `UTC timestamp + timezone_offset_minutes - day_start_minutes` as a UTC instant, then take its calendar date (`YYYY-MM-DD`).
- For tare and calibration epochs, choose the last epoch with matching hive and `from_ts <= sample timestamp`.
- Apply alias mapping before tare/calibration. If no alias matches (`from_ts <= ts` and `ts < until_ts` when `until_ts` is present), the raw hive id is canonical.
- Calibration: `calibrated_kg = grams / 1000.0 * scale + offset_kg`.
- Net weight: `net_kg = calibrated_kg - tare_kg`.
- Summary and daily numeric fields round to `precision` decimal places (default `3`).

## Binary frames

### v2 `HWS2` (40 bytes)

| offset | size | field |
|---:|---:|---|
| 0 | 4 | magic `HWS2` |
| 4 | 1 | version, currently `2` |
| 5 | 1 | frame_type: `1=sample`, `2=correction`, `3=tombstone` |
| 6 | 2 | flags, little-endian `u16`, reserved bits ignored |
| 8 | 8 | event_id, little-endian `u64` |
| 16 | 8 | timestamp unix seconds, little-endian `u64` |
| 24 | 2 | raw_hive_id, little-endian `u16` |
| 26 | 4 | grams, little-endian signed `i32` |
| 30 | 4 | correction_target event_id low 32 bits, little-endian `u32`; zero for normal samples |
| 34 | 2 | source sequence, little-endian `u16` |
| 36 | 4 | checksum, little-endian `u32` |

Checksum: wrapping sum of bytes `0..36` modulo `2^32`.

- Checksum mismatch quarantines the frame and continues.
- Truncated final frame quarantines one `truncated_tail` record and ignores that incomplete frame only.
- Bad magic on a 40-byte read quarantines `bad_magic` and continues. **`bad_magic` rows must always use `event_id: null`.** Magic is validated before any v2 field decode; never read or emit event_id from bytes 8–16 even when those bytes look like a valid u64.
- Unsupported version or frame type quarantines with `unsupported_version` or `unsupported_frame_type`.

Frame semantics:

- **sample**: creates a live event unless `event_id` was already accepted. Duplicate accepted IDs are ignored idempotently and counted in `duplicate_events`.
- **correction**: if `correction_target` resolves to an accepted event (matching low 32 bits of the target event id), replace that event's grams/timestamp/raw hive while preserving the target event id for dedupe. Recompute canonical hive, net weight, and bucket membership. Missing target quarantines as `missing_correction_target`.
- **tombstone**: removes the target event from rollups if it exists. Missing target counts as duplicate/no-op in `duplicate_events`, not a fatal error.

### Legacy v1 `HWSC`

Legacy v1 `HWSC` frames (24 bytes) are unsupported. Each complete v1 frame is quarantined with reason `unsupported_version` and replay continues with the next frame boundary.

## Outputs

### Daily JSONL (`--emit-daily`)

One JSON object per `(date, canonical_hive_id)` sorted by `date`, then `hive_id` ascending:

```json
{
  "date": "2023-11-14",
  "hive_id": 1,
  "weight_delta_kg": 1.234,
  "samples": 4,
  "first_event_id": 1001,
  "last_event_id": 1009
}
```

- Within a bucket, first/last follow accepted replay order after corrections and tombstones.
- `weight_delta_kg = last_net_kg - first_net_kg`.
- Fewer than two live samples yields delta `0.0`.
- `samples` counts live sample events after corrections/tombstones.

### Summary JSON (`--emit-summary`)

```json
{
  "site": "north_yard",
  "total_delta_kg": 1.234,
  "days_processed": 2,
  "hives_seen": [1, 2],
  "accepted_frames": 12,
  "duplicate_events": 2,
  "quarantined_frames": 1,
  "tombstoned_events": 1,
  "state_frontier": {"stream_count": 3, "frame_count": 27},
  "audit_fingerprint": "a1b2c3d4e5f60718",
  "ready": true
}
```

- `hives_seen`: sorted canonical hive IDs with at least one live accepted sample.
- `accepted_frames`: sample/correction/tombstone frames that changed state or valid no-op tombstones on existing targets.
- `duplicate_events`: duplicate accepted event IDs plus duplicate/no-op tombstones on missing targets.
- `quarantined_frames` equals quarantine JSONL row count.
- `ready` is `true` when at least one daily row exists.
- `state_frontier` reports replay progress after the manifest walk completes:
  - `stream_count`: number of manifest streams fully walked, equal to `(last stream index + 1)`.
  - `frame_count`: count of frame slots walked in the **last processed stream only** — equal to the number of consumed slots (valid, quarantined, or truncated-tail) in that stream. If the last stream consumed slots `0..=4`, `frame_count` is `5`. It is **not** a cumulative total across all streams.
  - Example: after stream 0 yields five frame slots and stream 1 yields three, `stream_count` is `2` and `frame_count` is `3`.

### Quarantine JSONL (`--emit-quarantine`)

One object per rejected frame in replay order:

```json
{
  "source": "yard-a-radio-1",
  "stream_index": 0,
  "frame_index": 5,
  "reason": "checksum",
  "event_id": 1234
}
```

- `stream_index`: zero-based manifest stream index.
- `frame_index`: **zero-based** frame slot index within that stream. The first frame slot in each stream is `0`; increment after each consumed slot (valid, quarantined, or truncated-tail).
- Summary `state_frontier.frame_count` is the **count** of frame slots walked in the last processed stream (not a zero-based index). After walking slots `0..=4`, `frame_count` is `5`.

Allowed reasons: `checksum`, `bad_magic`, `truncated_tail`, `missing_correction_target`, `unsupported_version`, `unsupported_frame_type`, `state_recovery`, `stale_correction_target`.

`event_id` in quarantine rows:

| reason | `event_id` |
|---|---|
| `bad_magic` | always `null` (magic failed before field decode) |
| `truncated_tail` | always `null` |
| `unsupported_version` on legacy `HWSC` | always `null` |
| `unsupported_version` on `HWS2` with wrong version byte | decoded u64 at bytes 8–16 |
| `unsupported_frame_type` on valid `HWS2` v2 | decoded u64 at bytes 8–16 |
| `checksum`, `missing_correction_target`, `stale_correction_target` | decoded u64 at bytes 8–16 when available |
| `state_recovery` | always `null` |

### State files (`--state-dir`)

Written atomically via temp file plus rename:

- `rollup_state.json`: full replay state for resume.
- `rollup_state.compact.json`: compact snapshot when `--compact` is set.

State retains accepted live events, dedupe set, correction/tombstone effects, quarantine counters, replay frontier `{stream_count, frame_count}`, per-stream resume progress, and an embedded `state_epoch` using the same semantics as summary `state_frontier`.

## Replay identity and restart recovery

Each stream has a replay identity derived from `source`, `kind`, byte length, first eight bytes, last eight bytes, and a wrapping byte-sum fingerprint of the stream content. Persisted state records the identity and consumed frame-slot count for every completed stream. On `--resume`, if a stream identity exactly matches a persisted stream identity, replay starts at the first unconsumed frame slot for that stream. If the same `source` appears with a changed identity, the stream is treated as a new backfill shard and replay starts at slot 0; dedupe and lineage rules still prevent accepted event IDs from being applied twice.

If both `rollup_state.json` and `rollup_state.compact.json` exist, the engine must load the newest valid snapshot by embedded `state_epoch`, not by filename. If the newest snapshot is malformed JSON or fails schema validation, it must fall back to the older valid snapshot and emit a quarantine row with reason `state_recovery`. Temporary files ending in `.tmp` are never loaded as canonical state, but their presence is also reported once as `state_recovery` in the current run's quarantine output. If no valid state exists, `--resume` starts from an empty state.

## Lineage and target resolution

Corrections and tombstones target the low 32 bits of an accepted event ID. If multiple accepted event IDs share the same low 32 bits, choose the target with the highest accepted replay order that is strictly earlier than the correction/tombstone frame. If the selected target is no longer live, a correction is quarantined as `stale_correction_target`; a tombstone against an already-dead target is a duplicate/no-op and increments `duplicate_events`. A correction preserves the target event ID and original accepted replay order, but replaces timestamp, raw hive, grams, canonical hive, net weight, and bucket membership. A correction frame's own `event_id` is still added to dedupe so replaying the same correction frame is idempotent.

Correction chains are allowed: if event A is corrected by frame B and then frame C targets A's low 32 bits, C applies to A's current value, not to B as a new sample. Tombstones remove the current value of the target event from rollups after all prior corrections have been applied.

## Audit output

The summary JSON includes an `audit_fingerprint` string. It is a lowercase hexadecimal 64-bit FNV-1a digest over the canonical replay surface. The digest input is UTF-8 text made by concatenating these lines in order with `\n` separators and a final trailing `\n`:

1. `site=<site>`
2. One line for each daily row sorted exactly as emitted: `daily|<date>|<hive_id>|<weight_delta_kg>|<samples>|<first_event_id>|<last_event_id>` using the already-rounded JSON numeric representation.
3. One line for each quarantine row sorted by replay order: `quarantine|<source>|<stream_index>|<frame_index>|<reason>|<event_id-or-null>`.
4. One line for each live accepted event sorted by event ID: `event|<event_id>|<timestamp>|<raw_hive_id>|<canonical_hive_id>|<grams>|<rounded_net_kg>|<order>`.

Use FNV-1a offset basis `14695981039346656037` and prime `1099511628211`, wrapping modulo `2^64`. Format the final value as 16 lowercase hex digits.
