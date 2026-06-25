# Reflector registry form

`/app/data/reflectors.json` is a JSON array. Every row carries:

| field          | type   | notes |
|----------------|--------|-------|
| `reflector_id` | string | unique across the registry |
| `station`      | string | human-readable site name |
| `class`        | string | one of `edge`, `core`, `pop` |

The registry is the authoritative list of reflectors for the run. Every
reflector named here appears in the report's `reflectors` array, sorted
by numeric suffix of `reflector_id` (so `R1`, `R2`, `R3`, `R10`, `R11`,
not the lexical `R1`, `R10`, `R11`, `R2`, `R3`).

A reflector with zero surviving probes anywhere in the run still gets
its row in the report; counts are zero, `offline_observed` is true,
and `jitter_share_permille` is zero.

## Per-reflector row in the output

The output `reflectors[]` row has the following key order pinned:

```
reflector_id
station
class
probe_count
anomaly_count
quiet_period_suppressed
offline_observed
jitter_share_permille
```

`probe_count` excludes synthetic REFLECTOR_OFFLINE rows; it is the
count of REAL surviving probes for this reflector after dedup,
canonicalization, and the strict-int gate.

`anomaly_count` is the count of probes whose FINAL verdict (after the
cascade, after the marker mute) is `OWD_ANOMALY`. A muted probe whose
final verdict is `QUIET_SUPPRESSED` does NOT contribute to this count.

`quiet_period_suppressed` is the count of probes for this reflector
whose final verdict is `QUIET_SUPPRESSED`.

See `offline_marking.md` for when `offline_observed` is true.
