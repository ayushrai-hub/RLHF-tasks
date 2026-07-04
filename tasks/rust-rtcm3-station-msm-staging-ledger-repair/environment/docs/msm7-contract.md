# MSM7 synthetic contract (message type 1077)

Payload layout after the 2-byte message number (`1077` big-endian):

| Field | Type | Notes |
|-------|------|-------|
| `station_id` | `u16` BE | Caster station id |
| `mp_len` | `u8` | Mountpoint byte length (1–32) |
| `mountpoint` | bytes | UTF-8, not NUL-terminated |
| `sequence` | `u32` BE | Per-mount sequence |
| `epoch_ms` | `u64` BE | Observation epoch milliseconds |
| `obs_count` | `u8` | Number of observables (0–8) |
| observables | repeat | See below |

Each observable:

| Field | Type |
|-------|------|
| `sv_id` | `u8` |
| `scale_exp` | `i8` signed |
| `range_raw` | `u32` BE |
| `phase_raw` | `u32` BE |

Decoded values (all observables):

```
divisor = 10^max(scale_exp, 0)
range_m = range_raw / divisor
phase_cycles = phase_raw / divisor
```

`observable_sum` for a frame is the sum of `range_m` across observables.

All multi-byte integers in the MSM block use **big-endian** byte order.
