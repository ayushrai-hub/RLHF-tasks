# Pump-station overflow trip ledger: contract

`overflow` reads one JSON scenario describing per-line flow limits and a
stream of line-flow samples, and prints a deterministic JSON ledger of
**confirmed overflow trips**, cumulative confirmed trip-time, a one-way lockout
instant, and the line's final state — per line.

```
go build -o overflow ./cmd/overflow
./overflow < scenario.json > ledger.json
```

The whole scenario is read from standard input and the ledger is written to
standard output. All quantities — timestamps, flows, and the `limit`, `arm`,
`reset`, and `budget` parameters — are integers. Time is measured in seconds and
flows in lps.

## Input

```json
{
  "until": 120,
  "lines": [
    { "name": "s1", "limit": 8, "arm": 5, "reset": 10, "budget": 60 }
  ],
  "samples": [
    { "t": 0,  "line": "s1", "lps": 4 },
    { "t": 30, "line": "s1", "lps": 11 },
    { "t": 60, "line": "s1", "type": "maint" },
    { "t": 80, "line": "s1", "type": "endmaint" }
  ]
}
```

- Each line has a unique non-empty `name`, an integer `limit` (the overflow
  flow ceiling, in lps), and three non-negative integers `arm`, `reset`, and `budget`
  (all measured in seconds, except `limit`).
- The `samples` array is a single shared stream of timeline entries; each entry
  names a configured `line` and an integer time `t >= 0`. An entry's `type` is
  `"sample"` (the default when `type` is absent), `"maint"`, or `"endmaint"`:
  - a `sample` entry additionally carries an integer `lps`;
  - a `maint` / `endmaint` entry carries no `lps` and opens / closes a
    *maintenance window* for its line (see below).
- `until` is optional.

Each line's own timeline is the subsequence of `samples` naming it, taken in
array order. Entries are processed in non-decreasing `t`; entries sharing a `t`
are processed in array order.

## Piecewise-constant flow

Consider one line in isolation. A `sample` sets the line's flow to its `lps`
from its own `t` until the next `sample`'s `t`; the last `sample` holds its flow
until the **horizon** `H`. Before a line's first `sample` it has no flow and
cannot be in overflow. Maintenance entries do not change the flow.

The horizon `H` is `until` when it is present, otherwise the largest `t` among
**all** entries in the scenario. Open trips are truncated at `H`.

A line is **over** at any instant where its flow is strictly greater than
`limit`, and **under** otherwise.

## Trip lifecycle

A trip is a maximal stretch of overflow for one line. It is governed by two
dwell timers, `arm` and `reset`, each of which counts elapsed continuous seconds
and is **paused** by maintenance windows (see below).

**Arming (confirmation).** When a line becomes over at time `s` it begins
arming. The trip is **confirmed** once the line has stayed over continuously for
`arm` seconds; that confirmation is a computed instant. If the line returns
under the flow ceiling before the arm dwell completes, the over-stretch was a
transient and produces **no trip at all**.

**Trip start.** A confirmed trip's interval starts at `s` — the instant the
line first went over — not at the confirmation instant.

**Reset (recovery).** Once a trip is confirmed, the line is in the trip while it
is over. When it returns under the flow ceiling at time `r`, `r` is the trip's
tentative end. The trip **resets** only after the line then stays under
continuously for `reset` seconds; that reset is a computed instant.

- If the line becomes over again before the reset dwell completes, the brief
  under-flow ceiling dip does not end the trip: the same trip continues (the dip
  becomes interior to it, and no re-arming is needed).
- If the line is still under when the reset dwell completes, the trip has reset
  and its end is `r`; a later over-stretch starts a brand-new trip that must arm
  again from scratch.

The reset trip's end is always the return time `r`, never `r + reset`.

**Trip end.** A confirmed trip's interval ends at the return time that leads to
it resetting (or at the horizon `H` if it is still over there).

## Computed boundaries

The arm-confirmation instant and the reset-completion instant are **computed
boundaries** that generally fall strictly between two timeline entries. The
ledger materialises them: a confirmation or reset takes effect at exactly its
computed instant, using the line's flow as it stands entering that instant.
When a computed boundary coincides with a timeline entry at the same `t`, the
boundary is resolved first and then the entry is applied.

## Maintenance windows

A `maint` entry at time `p` opens a maintenance window for its line that the
matching `endmaint` entry at time `q` closes. A maintenance window **pauses every
dwell and budget clock without clearing any state**:

- `sample` entries during the window still update the line's flow, so the flow
  in force at `endmaint` is whatever the last sample set.
- The arm and reset dwell clocks do not advance during `[p, q)`: they resume from
  exactly where they stood, so the window's duration `q - p` simply postpones the
  corresponding computed boundary.
- Confirmed trip-seconds do not accrue during `[p, q)`.
- The line holds its trip phase while the window is open. A `sample` inside
  `[p, q)` updates the stored flow but does not on its own begin arming, confirm
  or reset a trip, return the line under the flow ceiling, or re-breach it. Any phase
  change the samples imply is evaluated only when the window closes, against the
  flow in force at `endmaint`, and takes effect at the `endmaint` instant `q`
  (so an over→under return that happens inside a window has return time `q`, and a
  stretch that first goes over inside a window begins arming at `q`).

A `maint` while a window is already open, an `endmaint` with no open window, and
a window still open at the end of a line's timeline are all malformed input.

## Trip-seconds and the lockout budget

`budget` bounds the cumulative confirmed trip-time a line may accrue before it
locks out.

- Trip-seconds are counted **only while a confirmed trip is over**, and only from
  the confirmation instant onward — the arming seconds, the under-flow ceiling seconds
  of a merged dip, and any seconds inside a maintenance window are not counted.
- The running total accrues in real time as the line stays over. The line
  **locks out** at the exact instant the cumulative confirmed trip-seconds reaches
  `budget`, even when that instant is strictly between two samples.
- A lockout is a one-way latch. At the lockout instant the line's currently open
  trip (if any) is truncated to end there, no later trips are reported for that
  line, and `trip_seconds` is reported as `budget`.
- `locked_at` is that instant, or `null` if the line never locks out. With
  `budget` equal to `0` a line locks out at its first confirmation instant.

## Output

```json
{
  "lines": [
    {
      "name": "s1",
      "trips": [ { "start": 30, "end": 115 } ],
      "trip_seconds": 60,
      "locked_at": 115,
      "final": { "state": "locked", "since": 115 }
    }
  ]
}
```

- `lines` is ordered by `name` (ascending, byte order) and contains every
  configured line, including ones with no samples or no trips.
- `trips` lists the line's confirmed trips in time order, each a half-open
  interval `[start, end)` with `start < end` (transients and any zero-length
  interval are omitted).
- `trip_seconds` is the cumulative confirmed trip-time defined above (capped at
  `budget` once locked out).
- `locked_at` is the lockout instant or `null`.
- `final` reports the line's state at the horizon `H`:
  - `state` is `"locked"` if the line locked out, otherwise `"tripped"` if a
    confirmed trip is in progress and over at `H`, otherwise `"ok"`;
  - `since` is the instant the line entered that state — the lockout instant when
    locked; the in-progress trip's start when tripped; otherwise the instant the
    line last became ok (the end of the last confirmed trip, the tentative return
    time if a reset dwell is still pending at `H`, or `0` if the line never had a
    confirmed trip).

## Errors

If the input is not a JSON object, is missing `lines` or `samples`, names a
duplicate line, omits a line or sample field, carries a negative `arm`,
`reset`, `budget`, or sample `t`, gives two samples the same `t` for one line,
references an unknown line, carries an unknown entry `type`, attaches a `lps` to
a maintenance entry, opens a maintenance window while one is already open for that
line, closes one that is not open, leaves a maintenance window open at the end of
a line's timeline, or sets `until` before the last sample, the program writes a
diagnostic to standard error and exits with a nonzero status without printing a
ledger.
