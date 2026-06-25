# Strict integer gate — accept/reject table

The integer fields `cycle_id`, `send_ts`, `recv_ts`, `tx_ts`, and
`seq_no` accept ONLY strict integer encodings. Every other JSON shape
discards the row at load time.

Accept iff the JSON value is one of:

* a bare JSON integer (`42`, `-3`, `0`)
* a JSON string containing optional surrounding whitespace, an
  optional leading minus sign, and one or more digits (`"42"`,
  `"  42  "`, `"-3"`)

| Field value     | Decision | Reason |
|-----------------|----------|--------|
| `42`            | ACCEPT   | bare JSON integer |
| `-3`            | ACCEPT   | bare signed JSON integer |
| `0`             | ACCEPT   | bare zero |
| `"42"`          | ACCEPT   | quoted integer string |
| `"-3"`          | ACCEPT   | quoted signed integer string |
| `"  42  "`      | ACCEPT   | whitespace tolerated inside the string |
| `42.0`          | REJECT   | JSON number with fractional part (even if zero) |
| `42.5`          | REJECT   | JSON fractional number |
| `"42.0"`        | REJECT   | quoted fractional string |
| `"42.5"`        | REJECT   | quoted fractional string |
| `1e2`           | REJECT   | scientific notation |
| `true`          | REJECT   | JSON boolean (no coercion to 1/0) |
| `false`         | REJECT   | JSON boolean |
| `null`          | REJECT   | JSON null |
| missing key     | REJECT   | key not present in the object |
| `""`            | REJECT   | empty string |
| `"forty-two"`   | REJECT   | non-numeric quoted string |

## Implementation note

A naive implementation that falls back to `strconv.ParseFloat`,
`Number.parseFloat`, or `int(float(...))` for any of these fields is
incorrect. The fallback silently accepts `42.0`, `42.5`, scientific
notation, and other shapes the spec REJECTS. The loader gate MUST
NOT contain a floating-point fallback for these fields.

## Fixture pin

The shipped primary fixture row `PR1` carries `seq_no: 42.5`. A
passing implementation drops it silently at load time:

* `PR1` does NOT appear in the probe ledger.
* `PR1` does NOT contribute to any verdict count.
* `PR1` does NOT contribute to allocator weight.
* `summary.total_probes` is one lower than the raw shard line count.

Any implementation that admits `PR1` to the probe ledger has a
permissive integer gate and must be corrected.
