# Process-kettle element cycle ledger

`kettleheat` reads one JSON document from stdin (or from a file path given as the
first argument) and writes one JSON document to stdout. It reconstructs the
heating-element **ON intervals** that an anti-short-cycle immersion process-kettle
controller would produce while replaying a kettle-temperature/power-mode event
log.

This document is the single source of truth for the input format and for every
control and interval rule.

## Input

```
{
  "targetTemp": <int>,     // target kettle temperature, in tenths of a degree
  "deadband":   <int>,     // half-band width, in tenths of a degree, >= 0
  "minRun":     <int>,     // minimum element ON dwell time, >= 0
  "minRest":    <int>,     // minimum element OFF dwell time, >= 0
  "until":      <int>,     // horizon timestamp (hard ceiling)
  "events":     [ ... ]    // ordered event list (see below)
}
```

All five scalar fields are required and are integers. `temp`/`targetTemp`/
`deadband` are temperatures in tenths of a degree; `minRun`/`minRest`/`until`
and every event `at` are integer timestamps on one shared monotonic clock.
These field names are exact. The input schema uses `targetTemp`, `minRun`,
`minRest`, `type`, and `at`; it does not use alternate names such as
`setpoint`, `t`, or `mode`.

The controller starts at the implicit start time `t0 = 0` with the element
**OFF**, power mode `on`, no temperature sample yet, and no freeze active.

### Events

Every event is an object with a `type` and an integer `at` timestamp. Events
are given in non-decreasing `at` order; ties at the same `at` are processed in
array order. Event timestamps must satisfy `0 <= at <= until`.

- `{"type":"sample","temp":<int>,"at":<int>}` — a kettle-temperature sample. The
  measured temperature is a **step function**: it takes value `temp` from this
  event's `at` (inclusive) and **holds that value** until the next `sample`
  (or forever, if none follows). Before the first sample the temperature is
  unknown and demand cannot change (it stays at its latched value, which starts
  OFF).
- `{"type":"power","state":"on"|"off","at":<int>}` — sets the controller power
  mode. In `off` mode the element is forced **OFF immediately** (see Control
  law).
- `{"type":"freeze","at":<int>}` — opens a *freeze* window.
- `{"type":"endfreeze","at":<int>}` — closes the freeze window opened by the
  most recent `freeze`.

## Control law

### Demand

Demand is a latching signal driven by the current (step-function) temperature
relative to the band `[targetTemp - deadband, targetTemp + deadband]`:

- when `temp <= targetTemp - deadband` → demand becomes **ON**;
- when `temp >= targetTemp + deadband` → demand becomes **OFF**;
- when `targetTemp - deadband < temp < targetTemp + deadband` → demand is
  **unchanged** (it latches at its previous value).

Demand starts **OFF**. A demand transition can only occur at a `sample` (the
only thing that changes the temperature). Demand is evaluated **at** the
sample's `at` time, inclusively.

### Anti-short-cycle gating (the core rule)

The element's actual ON/OFF state is gated by minimum dwell times so it never
short-cycles. Let `lastOn` be the time the element most recently turned ON and
`lastOff` the time it most recently turned OFF (both initialised so that at
`t0 = 0` the element is freely allowed to turn on — i.e. `lastOff` is treated as
`-minRest`, so the first turn-on is never blocked).

In `on` power mode, with the element currently **OFF**:

- If demand becomes ON at time `d`:
  - if `d >= lastOff + minRest`, the element turns **ON at `d`**;
  - otherwise the turn-on is **DEFERRED** to the computed boundary
    `b = lastOff + minRest`. At time `b` the controller re-evaluates: the element
    turns ON at `b` **only if demand is still ON at `b`**. If demand has cleared
    (gone OFF) at or before `b`, no interval is opened.

In `on` power mode, with the element currently **ON**:

- If demand becomes OFF at time `d`:
  - if `d >= lastOn + minRun`, the element turns **OFF at `d`**;
  - otherwise the turn-off is **DEFERRED** to the computed boundary
    `b = lastOn + minRun`. At time `b` the controller re-evaluates: the element
    turns OFF at `b` **only if demand is still OFF at `b`**. If demand has gone
    back ON at or before `b`, the element **keeps running** (no interval is
    closed).

The deferral boundaries `lastOff + minRest` and `lastOn + minRun` are **computed
instants** that usually fall strictly between explicit events. They are
materialised into the timeline and evaluated exactly like events. Demand at a
computed boundary `b` is the latched demand produced by the most recent sample
whose `at <= b`. **The comparison at a boundary is inclusive**: a `sample` (or
the demand change it causes) landing exactly at `at == b` is considered to have
happened at `b`, so it counts when the boundary is re-evaluated.

There is at most one pending deferral at a time (the element is either OFF
waiting to turn on, or ON waiting to turn off). While a turn-off is deferred,
a later demand-ON simply cancels the pending turn-off (the element was running
the whole time and keeps running). While a turn-on is deferred, a later
demand-OFF cancels the pending turn-on (no interval is opened).

When the element turns ON at time `s`, an interval opens with `start = s` and
`lastOn = s`. When it turns OFF at time `e`, the open interval closes with
`end = e` and `lastOff = e`.

### `off` power mode

A `{"type":"power","state":"off"}` event at time `m`:

- forces the element **OFF immediately at `m`, overriding `minRun`** — if an
  interval is open it closes with `end = m` and `lastOff = m`;
- cancels any pending deferred turn-on;
- sets demand to OFF and keeps the element OFF for as long as the mode is `off`
  (samples still update the latched temperature/demand but cannot turn the
  element on while mode is `off`).

A later `{"type":"power","state":"on"}` event at time `h` re-enables heating.
It does **not** synthesize a new sample and does **not** re-derive demand from
the held temperature: demand keeps the latched value it currently holds. Since
the `off` event reset demand to OFF, demand is OFF at `h` unless an intervening
`sample` during the off period already drove it back ON. With no intervening
ON-demand sample, the element stays OFF until a later `sample` makes demand ON
again, even if the last held temperature is cold. If demand is ON at `h`, the
normal gating applies with the forced-off timestamp as `lastOff`, so the
turn-on still respects `minRest`.

### Freeze window

A `{"type":"freeze"}` at time `p` **freezes** the controller: the current
element state (ON or OFF) is preserved and **all switching transitions are
suppressed** until the matching `{"type":"endfreeze"}`. During a freeze:

- samples still update the latched temperature and demand, but **no interval
  opens or closes**, and any pending deferral is dropped (suppressed);
- an `off` power-mode event during a freeze is also suppressed (no forced-off
  while frozen); the mode value is still recorded and takes effect at
  `endfreeze`.

At the matching `{"type":"endfreeze"}` at time `q` the controller re-evaluates
from the current temperature and mode as if fresh:

- the minimum-dwell clocks **restart at `q`**: treat `lastOn = q` if the element
  is currently ON and `lastOff = q` if it is currently OFF. (So immediately
  after a freeze, a turn-off cannot happen until `q + minRun` and a turn-on
  cannot happen until `q + minRest`, even if the element had already been ON or
  OFF for long enough before the freeze.)
- demand is the latched demand at `q`; normal gating then resumes from `q`.

Nested freezes are not used; a `freeze` while already frozen, or an `endfreeze`
with no open freeze, is a malformed input (see Errors).

### Horizon

`until` is a hard ceiling. If an interval is still open at the horizon it is
closed with `end = until`. Computed deferral boundaries that fall after `until`
never fire. No timestamp in the output ever exceeds `until`.

## Output

```
{
  "intervals": [ {"start":<int>,"end":<int>}, ... ],
  "ontime":    <int>,
  "final":     { "state":"on"|"off", "since":<int> }
}
```

- `intervals` — the element-ON intervals, ordered by time and non-overlapping,
  each with `start < end`. Zero-length intervals (`start == end`) are **not**
  emitted. Boundaries are the **computed** switch times described above.
- `ontime` — the sum of `end - start` over all emitted intervals.
- `final` — the element state at the horizon: `state` is `"on"` if an interval
  is open at `until` else `"off"`; `since` is the timestamp at which the element
  last entered that state (the open interval's `start` when on; the last
  interval's `end`, or `0` if the element never produced an ON interval, when
  off). A `power` `off` event that does not close an interval because the
  element was already off does not by itself change this `0` value.

## Errors

On malformed input the program prints `error: <message>` to **stderr**, writes
**nothing** to stdout, and exits with a **nonzero** status. Malformed inputs
include: invalid JSON; a missing or non-integer required field; negative
`deadband`/`minRun`/`minRest`; an unknown event `type`; a missing/invalid event
field (`temp`, `state`, `at`); a `state` other than `on`/`off`; an event `at`
out of `[0, until]`; events not in non-decreasing `at` order; an `endfreeze`
with no open freeze or a `freeze` while a freeze is already open; a freeze left
open at the end of the event list.
