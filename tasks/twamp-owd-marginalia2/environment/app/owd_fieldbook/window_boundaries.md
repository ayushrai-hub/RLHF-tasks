# Window boundary semantics

Two windows appear in the audit, and they have OPPOSITE boundary
styles. This is intentional — the two windows do not share semantics
and a uniform `[a, b)` or `(a, b]` rule is incorrect.

## Probe validity window — `[start, end)`

The validity window comes from `config.json`:

| field                       | role |
|-----------------------------|------|
| `validity_window_start_us`  | inclusive lower bound |
| `validity_window_end_us`    | exclusive upper bound |

A probe is in the validity window iff its canonicalized
`send_ts_us = T` satisfies:

    validity_window_start_us  <=  T  <   validity_window_end_us

Boundary check:

* `T == validity_window_start_us` — INSIDE the window.
* `T == validity_window_end_us` — OUTSIDE the window.

A probe outside the validity window is discarded silently before
classification — no verdict, no ledger entry, no count contribution.

## Marker scoping window — `(open, close]`

The marker window comes from the marker row itself:

| field             | role |
|-------------------|------|
| `window_open_us`  | EXCLUSIVE lower bound |
| `window_close_us` | INCLUSIVE upper bound |

A probe is in marker scope iff its canonicalized `send_ts_us = T`
satisfies:

    window_open_us  <  T  <=  window_close_us

Boundary check:

* `T == window_open_us` — OUTSIDE marker scope.
* `T == window_close_us` — INSIDE marker scope.

See `../cycle_journal/quiet_period_oneshot.md` for the one-shot
mute semantics.

## Why the asymmetry

The validity window is anchored to the run's start, so the start
instant participates. The marker window is anchored to operator
intent: ops wanted markers NOT to fire on a probe whose send_ts
exactly equals the marker's `window_open_us` (those edge fires were
almost always spurious), but DID want a marker to fire on a probe at
exactly `window_close_us`. The opposite-boundary choice is
deliberate.
