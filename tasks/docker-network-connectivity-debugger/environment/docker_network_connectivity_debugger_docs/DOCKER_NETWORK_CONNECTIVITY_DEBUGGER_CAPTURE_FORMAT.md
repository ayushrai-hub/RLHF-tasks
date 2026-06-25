# CNX1 bundled capture format (read-only)

Container connectivity probe events ship as little-endian binary under `/app/data/{scenario_id}/docker_network_connectivity_debugger_capture.cnx`. Scenario defaults live in `/app/data/{scenario_id}.json` (no `events` array).

## File header

| Offset | Field | Type | Rule |
|--------|-------|------|------|
| 0 | magic | 4 bytes | `CNX1` |
| 4 | `format_version` | uint32 **LE** | must be `1`; otherwise fatal (exit non-zero, no report) |

## Records (until EOF)

| Field | Type | Rule |
|-------|------|------|
| `record_seq` | uint32 LE | wire record identity for dedup (independent of JSON `seq`) |
| `flags` | uint16 LE | must be `0` for connectivity payloads |
| `reserved` | uint16 LE | must be `0` |
| `payload_len` | uint32 LE | byte length of JSON payload |
| `payload` | bytes | UTF-8 JSON object for one replay event |
| `checksum` | uint32 LE | CRC-32 (IEEE) over the 12-byte header (`record_seq`, `flags`, `reserved`, `payload_len`, each little-endian) concatenated with `payload` |

Process records in file order. Each record is **valid** or **rejected**:

| Reason | Rule |
|--------|------|
| `BAD_RESERVED` | `reserved != 0` |
| `BAD_FLAGS` | `flags != 0` |
| `LEN_OVERFLOW` | `payload_len > 4096`; see **LEN_OVERFLOW handling** below |

### LEN_OVERFLOW handling

When `payload_len > 4096` after a full 12-byte header was read:

1. The record counts toward `records_total`.
2. If at least `payload_len + 4` bytes remain after the header: increment `records_rejected` **once**, insert `record_seq` into the seen set, skip `payload` and `checksum` without CRC validation, and continue to the next record. Do **not** increment `dup_seq_rejects`.
3. If fewer than `payload_len + 4` bytes remain: increment `records_rejected` **once**, set `truncated_tail` to `1`, and stop.

Evaluate `LEN_OVERFLOW` before `DUP_SEQ`. A `record_seq` rejected for `LEN_OVERFLOW` and inserted into the seen set causes a later record with the same `record_seq` to be rejected as `DUP_SEQ` (incrementing `dup_seq_rejects`).

| Reason | Rule |
|--------|------|
| `DUP_SEQ` | `record_seq` already seen (valid or rejected earlier) |
| `BAD_CRC` | checksum mismatch |
| `TRUNCATED` (header) | fewer than 12 bytes remain for a header |
| `TRUNCATED` (body) | fewer than `payload_len + 4` bytes remain after a full header was read |

On header `TRUNCATED`: increment `records_rejected`, set `truncated_tail` to `1`, and stop. **Do not** increment `records_total`.

On body `TRUNCATED` after a full header: increment `records_total` and `records_rejected`, set `truncated_tail` to `1`, and stop.

`records_total` counts only records whose complete 12-byte header was read.

Track every `record_seq` in a set, including rejected records. `dup_seq_rejects` counts **only** rejected records whose reason is `DUP_SEQ` (not `LEN_OVERFLOW`, `BAD_CRC`, or other reasons).

`payload_bytes` sums `payload_len` for **valid** records only.

Only valid payloads are unmarshalled and passed to connectivity replay (then `DOCKER_NETWORK_CONNECTIVITY_DEBUGGER_RULES.md` event sort and `event_id` dedup apply).

## Per-scenario capture block in the report

Each scenario row includes a `capture` object (see `DOCKER_NETWORK_CONNECTIVITY_DEBUGGER_SCHEMA.md`) with: `format_version`, `records_total`, `records_valid`, `records_rejected`, `dup_seq_rejects`, `truncated_tail`, `payload_bytes`.

All bundled capture paths are absolute under `/app/data/{scenario_id}/docker_network_connectivity_debugger_capture.cnx`.

## Go decoder API

Implement `Decode` in package `docker_network_connectivity_debugger_capture` under `/app/internal/docker_network_connectivity_debugger_capture/decode.go`.

Required signature and return order:

```
func Decode(path string) ([]replay.Event, Stats, error)
```

Return the decoded event slice first, the `Stats` struct second, and the error last. Do not reorder return values. On permission denied or fatal format errors return a nil event slice with a non-nil error; populate `Stats` only as far as decoding progressed before the error.

The `Stats` struct must use **exported fields with `json` struct tags** whose names match the report `capture` object exactly (snake_case). Required tags:

| Field | JSON tag |
|-------|----------|
| `FormatVersion` | `json:"format_version"` |
| `RecordsTotal` | `json:"records_total"` |
| `RecordsValid` | `json:"records_valid"` |
| `RecordsRejected` | `json:"records_rejected"` |
| `DupSeqRejects` | `json:"dup_seq_rejects"` |
| `TruncatedTail` | `json:"truncated_tail"` |
| `PayloadBytes` | `json:"payload_bytes"` |

Do not rely on default Go field-name marshaling; tests compare `json.Marshal(stats)` keys to the schema.

`Decode` must reject any capture path not prefixed by `/app/data/` with `permission denied` (do not read `/etc`, `/tmp`, or relative paths).
