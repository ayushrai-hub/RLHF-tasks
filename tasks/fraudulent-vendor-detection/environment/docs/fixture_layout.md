# Fixture layout

## Related vendor groups

North-panel vendors `vendor-acme` and `vendor-beta` share the same remittance rail in the corporate vendor master (separate legal entities, one treasury route). South-panel vendors `vendor-delta` and `gamma-pallet` share a second rail. Fraud signals only appear when **vendor_graph** batches multi-stage exposure per period; **line_item** flushes each stage before the next bind.

## North panel (`corpus_north.json`)

Vendors:

- `vendor-acme` — vendor spend cap 1000 weight points
- `vendor-beta` — vendor spend cap 500 weight points

Invoice ids `u001`–`u018` span periods 0–7. Period 0 schedules three funnel stages for `vendor-acme` at 400 weight points each. Period 1 schedules three stages for `vendor-beta` at 200 weight points each.

North period-0 triple: `u001`, `u002`, `u003` (third invoice rejected on a correct run).

North period-1 triple: `u004`, `u005`, `u006` (third invoice rejected on a correct run).

On `burst.json` with `stage_width: 3` and default flags, a correct vendor_graph run rejects exactly these nine invoice ids: `u003`, `u006`, `u009`, `u010`, `u012`, `u015`, `u016`, `u017`, `u018`. The remaining north manifest rows are accepted with zero phantom tallies.

North burst `vendor_graph` committed trajectory (`committed_pts` / `pending_pts` at each `period_index`, pending always `0` after settlement):

| period_index | vendor-acme | vendor-beta |
| --- | ---: | ---: |
| 0 | 800 | 0 |
| 1 | 800 | 400 |
| 2 | 950 | 450 |
| 3 | 950 | 450 |
| 4 | 1000 | 450 |
| 5 | 1000 | 500 |
| 6 | 1000 | 500 |
| 7 | 1000 | 500 |

Periods 0 and 1 reject the stage-2 triple invoice (`u003`, `u006`) — the rejected row always has `stage` of `2` on those periods. Later rejections are cap-saturation once `vendor-acme` reaches 1000 or `vendor-beta` reaches 500.

Period 4 north burst cap window: `u011` is **accepted** (50 weight points, stage 0) and brings `vendor-acme` to 1000 committed points; `u012` is **rejected** (stage 1) because the vendor cap is already saturated. Periods 6–7 reject `u015`, `u016`, `u017`, and `u018` for the same cap-saturation reason on the respective vendors.

Profiles with `stage_width` below a manifest stage index omit those rows from the run while still requiring view parity on the remaining manifest rows.

## Period failover profile (`period_failover.json`)

Uses `run_mode` `period_failover` with `failover_period` `4` on the north panel. The simulator captures a period snapshot at the end of period `3` and restores it when period `4` begins.

On a correct **vendor_graph** run:

- `restore_applied_count` is `1`
- `replay_scheduled_count` is `1` (failover boundary minus the snapshot `settled_period`, which must be `3` when period frontiers advance correctly)
- `replay_periods_count` equals `replay_scheduled_count` (both `1` when period frontiers track the processed period index through the snapshot at period `3`)
- The failover audit matches an uninterrupted **vendor_graph** run on the same profile geometry (same `lines`, `ticks`, and summary tallies)

If period frontiers lag behind the processed period index, `replay_scheduled_count` can exceed the periods actually replayed and the failover audit diverges from the continuous run.

## Delay window profile (`delay_ticks.json`)

Uses `stage_width: 2` on the north panel. Period-zero invoice `u003` is omitted from the run; `u002` remains and must be **accepted** with full line_item/vendor_graph parity on the remaining rows.

## South panel (`corpus_south.json`)

Vendors:

- `vendor-delta` — vendor spend cap 800 weight points
- `gamma-pallet` — vendor spend cap 350 weight points

Invoice ids `s001`–`s010`. Period 0 schedules three stages for `vendor-delta` at 300 weight points each. Period 1 schedules three stages for `gamma-pallet` at 150 weight points each.

South period-0 triple: `s001`, `s002`, `s003` (third invoice rejected on a correct run).

South period-1 triple: `s004`, `s005`, `s006` (third invoice rejected on a correct run).

On `mixed_fleet.json` with default flags, a correct vendor_graph run rejects `s003`, `s006`, and `s010` (1120 accepted weight points total). South mixed committed trajectory:

| period_index | vendor-delta | gamma-pallet |
| --- | ---: | ---: |
| 0 | 600 | 0 |
| 1 | 600 | 300 |
| 2 | 700 | 340 |
| 3 | 780 | 340 |

`s010` is rejected at period 3 because `gamma-pallet` is already at its 350-point cap after `s008`; `vendor-delta` still accepts `s009`.
