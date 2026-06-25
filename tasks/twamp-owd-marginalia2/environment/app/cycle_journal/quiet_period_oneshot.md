# Quiet-period marker — one-shot suppression

A `quiet_period` marker mutes EXACTLY ONE `OWD_ANOMALY` emission
within its `(cycle_id, reflector_id)` scope and within its
`(window_open_us, window_close_us]` window. The mute consumes the
marker; subsequent anomalies in the same scope are emitted normally.

## Marker scoping window

The marker scoping window is `(open, close]` — LEFT-EXCLUSIVE,
RIGHT-INCLUSIVE.

A probe whose canonicalized `send_ts_us = T` falls in the window iff:

    window_open_us  <   T   <=  window_close_us

Boundary check:

* `T == window_open_us` — OUTSIDE the window (open boundary excludes).
* `T == window_close_us` — INSIDE the window (close boundary includes).

This DIFFERS from the probe validity window (`[start, end)`), which is
LEFT-INCLUSIVE and RIGHT-EXCLUSIVE. Opposite boundary style on
purpose. See `../owd_fieldbook/window_boundaries.md`.

## One-shot semantics

For each valid `(cycle, reflector)`-scoped marker:

1. Collect every OWD_ANOMALY probe whose `(cycle_id, reflector_id)`
   matches the marker AND whose canonicalized `send_ts_us` falls in
   `(window_open_us, window_close_us]`.
2. Sort the collected list by `send_ts_us` ascending, breaking ties
   by `probe_id` numeric suffix ascending.
3. Mute the FIRST item: its verdict becomes `QUIET_SUPPRESSED`, the
   reflector's `quiet_period_suppressed` count for the row increments
   by 1, and the marker is consumed.
4. Items 2..N remain `OWD_ANOMALY` (the marker is exhausted).

If two valid markers target the same `(cycle, reflector)` scope, they
each mute one anomaly in send-order; each marker consumes at most one
anomaly. If there are fewer qualifying anomalies than markers, the
extra markers are silently dropped — they emit no synthetic row.

## Seal reconciliation

The marker's `seal` field must equal the first 8 lowercase hex
characters of

    sha256("<marker_id>|<kind>|<cycle_id>|<reflector_id>|<secret>")

where `<secret>` is the run secret from `config.json`. A marker whose
seal does not match is silently dropped: no mute, no log, no entry.

See `../digest_workshop/seal_recipe.md` for the seal byte recipe.

## Common misimplementations

* "kill ALL anomalies for this `(cycle, reflector)` scope" — turns
  the one-shot mute into a blanket suppression, wrongly muting
  anomalies the marker should not touch.
* `<=` on the open boundary — pulls a probe at exactly
  `window_open_us` wrongly into scope.
* `<` on the close boundary — drops a probe at exactly
  `window_close_us` wrongly out of scope.
* Skipping the seal check — admits markers that were not meant to
  fire this run.
* Consuming the marker BEFORE finding a qualifying anomaly — silently
  drops markers whose window is empty even though no mute occurred.
* Muting before the cascade re-evaluation — turns a WITHIN_BOUNDS
  probe (incorrectly classified by the un-tightened threshold) into
  QUIET_SUPPRESSED. The mute must run AFTER the cascade has
  classified the probe as OWD_ANOMALY.

## Worked trace against the primary fixture

The primary fixture's only valid marker `M1` scopes cycle 2,
reflector R3, with window `(50000011500, 50000012500]`. After the
cascade brings cycle 2's threshold to 200, the probe `P12` has
`send_ts_us = 50000012000` and `owd_us = 250` — OWD_ANOMALY.

Boundary check for `P12`:

    50000011500 < 50000012000     -> TRUE  (open boundary cleared)
    50000012000 <= 50000012500    -> TRUE  (close boundary cleared)

`P12` is the first (and only) qualifying anomaly in scope, so M1
mutes it. `P12`'s final verdict is `QUIET_SUPPRESSED`. The reflector
row for R3 has `quiet_period_suppressed = 1`.
