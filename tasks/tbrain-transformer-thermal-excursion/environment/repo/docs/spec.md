# Transformer-thermal excursion ledger: contract

`thermalwatch` reads one JSON scenario describing per-asset temperature limits
and a stream of temperature readings, and prints a deterministic JSON ledger of
**confirmed temperature excursions**, cumulative confirmed over-time, a one-way
insulation-failure instant, and the asset's final state — per asset.

```
go build -o thermalwatch ./cmd/thermalwatch
./thermalwatch < scenario.json > ledger.json
```

The whole scenario is read from standard input and the ledger is written to
standard output. All quantities — timestamps, temperatures, and the `limit`,
`arm`, `clear`, and `budget` parameters — are integers. Time is measured in
seconds.

## Input

```json
{
  "until": 120,
  "assets": [
    { "name": "tx1", "limit": 8, "arm": 5, "clear": 10, "budget": 60 }
  ],
  "readings": [
    { "t": 0,  "asset": "tx1", "temp": 4 },
    { "t": 30, "asset": "tx1", "temp": 11 },
    { "t": 60, "asset": "tx1", "type": "service" },
    { "t": 80, "asset": "tx1", "type": "endservice" }
  ]
}
```

- Each asset has a unique non-empty `name`, an integer `limit` (the upper
  temperature threshold), and three non-negative integers `arm`, `clear`, and
  `budget` (all measured in seconds, except `limit`).
- The `readings` array is a single shared stream of timeline entries; each entry
  names a configured `asset` and an integer time `t >= 0`. An entry's `type`
  is `"reading"` (the default when `type` is absent), `"service"`, or
  `"endservice"`:
  - a `reading` entry additionally carries an integer `temp`;
  - a `service` / `endservice` entry carries no `temp` and opens / closes a
    *service window* for its asset (see below).
- `until` is optional.

Each asset's own timeline is the subsequence of `readings` naming it, taken in
array order. Entries are processed in non-decreasing `t`; entries sharing a `t`
are processed in array order.

## Piecewise-constant temperature

Consider one asset in isolation. A `reading` sets the asset's temperature to
its `temp` from its own `t` until the next `reading`'s `t`; the last `reading`
holds its temperature until the **horizon** `H`. Before a asset's first
`reading` it has no temperature and cannot be in an excursion. Service entries do
not change the temperature.

The horizon `H` is `until` when it is present, otherwise the largest `t` among
**all** entries in the scenario. Open excursions are truncated at `H`.

A asset is **over** at any instant where its temperature is strictly greater
than `limit`, and **ok** otherwise.

## Excursion lifecycle

An excursion is a maximal stretch of trouble for one asset. It is governed by
two dwell timers, `arm` and `clear`, each of which counts elapsed continuous
seconds and is **paused** by service windows (see below).

**Arming (confirmation).** When a asset becomes over at time `s` it begins
arming. The excursion is **confirmed** once the asset has stayed over
continuously for `arm` seconds; that confirmation is a computed instant. If the
asset returns to ok before the arm dwell completes, the over-stretch was a
transient and produces **no excursion at all**.

**Excursion start.** A confirmed excursion's interval starts at `s` — the
instant the asset first went over — not at the confirmation instant.

**Clearing (recovery).** Once an excursion is confirmed, the asset is in the
excursion while it is over. When it returns to ok at time `r`, `r` is the
excursion's tentative end. The excursion **clears** only after the asset then
stays ok continuously for `clear` seconds; that clearing is a computed instant.

- If the asset becomes over again before the clear dwell completes, the brief
  ok dip does not end the excursion: the same excursion continues (the dip
  becomes interior to it, and no re-arming is needed).
- If the asset is still ok when the clear dwell completes, the excursion has
  cleared and its end is `r`; a later over-stretch starts a brand-new excursion
  that must arm again from scratch.

The cleared excursion's end is always the return time `r`, never `r + clear`.

**Excursion end.** A confirmed excursion's interval ends at the return time that
leads to it clearing (or at the horizon `H` if it is still over there).

## Computed boundaries

The arm-confirmation instant and the clear-completion instant are **computed
boundaries** that generally fall strictly between two timeline entries. The
ledger materialises them: a confirmation or clearing takes effect at exactly its
computed instant, using the asset's temperature as it stands entering that
instant. When a computed boundary coincides with a timeline entry at the same
`t`, the boundary is resolved first and then the entry is applied.

## Service windows

A `service` entry at time `p` opens a service window for its asset that the
matching `endservice` entry at time `q` closes. A service window **pauses every
dwell and budget clock without clearing any state**:

- `reading` entries during the window still update the asset's temperature, so
  the temperature in force at `endservice` is whatever the last reading set.
- The arm and clear dwell clocks do not advance during `[p, q)`: they resume
  from exactly where they stood, so the window's duration `q - p` simply
  postpones the corresponding computed boundary.
- Confirmed over-seconds do not accrue during `[p, q)`.
- The asset holds its excursion phase while the window is open. A `reading`
  inside `[p, q)` updates the stored temperature but does not on its own begin
  arming, confirm or clear an excursion, return the asset to ok, or re-breach
  it. Any phase change the readings imply is evaluated only when the window
  closes, against the temperature in force at `endservice`, and takes effect at
  the `endservice` instant `q` (so an over→ok return that happens inside a window
  has return time `q`, and a stretch that first goes over inside a window begins
  arming at `q`).

A `service` while a window is already open, an `endservice` with no open window,
and a window still open at the end of a asset's timeline are all malformed
input.

## Over-seconds and the insulation-failure budget

`budget` bounds the cumulative confirmed over-time a asset may tolerate before
it fails.

- Over-seconds are counted **only while a confirmed excursion is over**, and only
  from the confirmation instant onward — the arming seconds, the ok seconds of a
  merged dip, and any seconds inside a service window are not counted.
- The running total accrues in real time as the asset stays over. The asset
  **fails** at the exact instant the cumulative confirmed over-seconds reaches
  `budget`, even when that instant is strictly between two readings.
- Insulation-failure is a one-way latch. At the insulation-failure instant the asset's currently
  open excursion (if any) is truncated to end there, no later excursions are
  reported for that asset, and `over_seconds` is reported as `budget`.
- `failed_at` is that instant, or `null` if the asset never fails. With
  `budget` equal to `0` a asset fails at its first confirmation instant.

## Output

```json
{
  "assets": [
    {
      "name": "tx1",
      "excursions": [ { "start": 30, "end": 115 } ],
      "over_seconds": 60,
      "failed_at": 115,
      "final": { "state": "failed", "since": 115 }
    }
  ]
}
```

- `assets` is ordered by `name` (ascending, byte order) and contains every
  configured asset, including ones with no readings or no excursions.
- `excursions` lists the asset's confirmed excursions in time order, each a
  half-open interval `[start, end)` with `start < end` (transients and any
  zero-length interval are omitted).
- `over_seconds` is the cumulative confirmed over-time defined above (capped at
  `budget` once failed).
- `failed_at` is the insulation-failure instant or `null`.
- `final` reports the asset's state at the horizon `H`:
  - `state` is `"failed"` if the asset failed, otherwise `"over"` if a
    confirmed excursion is in progress and over at `H`, otherwise `"ok"`;
  - `since` is the instant the asset entered that state — the insulation-failure instant
    when failed; the in-progress excursion's start when over; otherwise the
    instant the asset last became ok (the end of the last confirmed excursion,
    the tentative return time if a clear dwell is still pending at `H`, or `0` if
    the asset never had a confirmed excursion).

## Errors

If the input is not a JSON object, is missing `assets` or `readings`, names a
duplicate asset, omits a asset or reading field, carries a negative `arm`,
`clear`, `budget`, or reading `t`, gives two readings the same `t` for one
asset, references an unknown asset, carries an unknown entry `type`, attaches
a `temp` to a service entry, opens a service window while one is already open for
that asset, closes one that is not open, leaves a service window open at the
end of a asset's timeline, or sets `until` before the last reading, the program
writes a diagnostic to standard error and exits with a nonzero status without
printing a ledger.
