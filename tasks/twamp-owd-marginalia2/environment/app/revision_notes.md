# Revision notes

## v1.4.0 — 2026-04-12

* Marker scoping window split from probe validity window: marker
  scope is now LEFT-EXCLUSIVE (was inclusive). The intent is to keep
  markers from firing on a probe whose send_ts exactly equals the
  marker's `window_open_us`; ops complained those edge fires were
  almost always spurious. Probe validity window remains
  LEFT-INCLUSIVE.

## v1.3.0 — 2026-03-04

* Cross-cycle cascade: half-the-next-threshold-on-loss-spike replaces
  the earlier flat-threshold model. The cascade is RELATIVE (not
  relative to the default), so two consecutive loss-heavy cycles
  produce a one-quarter threshold in the third cycle.

## v1.2.0 — 2026-02-08

* OWD canonical form now subtracts `tx_ts` explicitly. Earlier
  collectors set `tx_ts == 0` for most reflectors and we used
  `recv_minus_send` as a shortcut. Two of the new reflectors record
  non-trivial `tx_ts` values (the new firmware does the
  reflector-side queue tick differently). The shortcut became
  incorrect. The `recv_minus_send` field is retained on the probe
  record because some downstream dashboards still read it.

## v1.1.0 — 2026-01-14

* Magnitude routing of `send_ts` introduced. Newer firmware records
  `send_ts` in picoseconds; legacy reflectors record microseconds.
  The auditor canonicalizes by magnitude (threshold 2e12) at ingest.

## v1.0.0 — 2025-12-02

* Initial release.
* Closed verdict enum (7 entries) finalised. Removed the open
  `OTHER` bucket.
* Numeric-suffix sort on all identifier arrays.
* Largest-remainder allocation for `jitter_share_permille`.
  Tiebreak direction depends on whether any reflector observed
  offline.
* `report_digest` self-binding (emitted both in summary and at top
  level).
