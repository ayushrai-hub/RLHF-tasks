# NDJSON probe row shape

Each line of `probes_shard_a.ndjson` and `probes_shard_b.ndjson` is
one JSON object. Empty lines and lines starting with `#` are skipped
silently and do not affect counts. Each object carries:

| field              | type        | required | notes |
|--------------------|-------------|----------|-------|
| `probe_id`         | string      | yes      | unique across both shards after dedup |
| `session_id`       | string      | yes      | sorted by numeric suffix in output |
| `cycle_id`         | strict int  | yes      | see `strict_int_table.md` |
| `reflector_id`     | string      | yes      | must exist in `reflectors.json` |
| `send_ts`          | strict int  | yes      | magnitude-routed; see `canonicalize.txt` |
| `recv_ts`          | strict int  | yes      | always microseconds |
| `tx_ts`            | strict int  | yes      | microseconds, reflector turnaround |
| `seq_no`           | strict int  | yes      | monotonic per session, no gap check |
| `recv_minus_send`  | int         | no       | INFORMATIONAL — not the OWD policy key |
| `loss_flag`        | bool        | yes      | real JSON true/false, never 0/1 |
| `kind`             | string      | yes      | always `"probe"` |

A row that fails the strict-int gate on any of `cycle_id`, `send_ts`,
`recv_ts`, `tx_ts`, or `seq_no` is silently discarded — no verdict
emitted, no ledger entry, no count contribution.

`loss_flag` must be a JSON boolean. A row whose `loss_flag` is `0`,
`1`, `"true"`, or `"false"` is also discarded.

The `recv_minus_send` field is an aggregate some upstream collectors
record for convenience. It does NOT participate in the canonical OWD
formula. See `../owd_fieldbook/formula.md`.

## Markers file

`markers.ndjson` has the same line convention (empty / `#` skipped).
Each row:

| field              | type        | notes |
|--------------------|-------------|-------|
| `marker_id`        | string      | unique within a run |
| `kind`             | string      | `quiet_period` or `void` (void is ignored) |
| `cycle_id`         | strict int  | scoping cycle |
| `reflector_id`     | string      | scoping reflector |
| `window_open_us`   | strict int  | left-exclusive endpoint |
| `window_close_us`  | strict int  | right-inclusive endpoint |
| `seal`             | string      | first 8 hex of keyed SHA-256 (see digest_workshop) |

A marker whose seal does not reconcile is silently dropped — no
mute, no log, no entry.
