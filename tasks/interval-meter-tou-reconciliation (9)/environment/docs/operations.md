# Operations

The reconciler loads the run config passed with `--config`. That file names the tariff JSON and a list of fixture CSV paths. The binary should process every listed fixture set and write the report path passed with `--out`.

Each CSV row is normally `meter_id,timestamp,register_kwh`. Some exports add a fourth `quality` column. CSVs follow ordinary comma-separated rules, including quoted fields and doubled quotes inside quoted meter ids. Timestamps are ISO-8601 with numeric offsets and may include fractional seconds.

Rows are grouped by exact meter id and sorted by absolute timestamp. Fixture names and meter ids must be emitted as valid JSON strings without truncation, and the report includes every fixture set and every distinct meter in the input rather than stopping at a fixed prefix. When one meter has duplicate non-reset valid rows at the same absolute timestamp, the later CSV row is a correction and replaces the earlier reading without creating an interval, rollover, gap, or tier allocation. If an `actual` or `estimate` row at a timestamp is followed by a duplicate `reset` row at that same timestamp, the actual/estimate reading still closes the previous interval, and the reset row then establishes the baseline for all later intervals. The duplicate reset itself does not create a rollover or a zero-time interval.

## Row quality

A missing or blank quality value is treated as `actual`. `actual` rows are normal. `estimate` rows are included in interval totals and tiering, but any meter that uses an estimated row is not reconciled. `void` rows are ignored before sorting and grouping. `reset` rows are retained as a new baseline; there is no interval, rollover, gap, or tier allocation from the prior reading into the reset row, but the next valid row after the reset is compared against the reset register.

## Intervals, gaps, and proration

Adjacent valid readings define one observed interval for `interval_count`. If elapsed absolute time between those readings spans multiple configured interval slots, the register delta is spread evenly across all elapsed slots. For example, a 45-minute span under a 15-minute tariff has three slots, contributes two `gap_intervals`, and allocates one third of the delta to each generated slot start. Each generated slot starts from the previous reading's written local date and clock. If the slot crosses a season or TOU-window boundary, split the slot by exact overlap seconds and allocate each portion to the tier active during that portion.

## Demand

`demand_peak_kw` is the maximum prorated slot kW sample across the meter series. Each sample is `slot_kwh * 60 / interval_minutes`, where `interval_minutes` comes from the active tariff JSON.

## Seasons and windows

Summer applies to the inclusive `start_mmdd` through `end_mmdd` range in the active tariff JSON. Other local dates use winter windows. Window arrays come from the tariff JSON; window starts are inclusive and ends are exclusive, including windows that wrap midnight.

## Rollovers

When a register reading decreases, count one rollover and use `(register_max_kwh - previous_register) + current_register` as the observed interval delta before any slot proration.

Output lands at `/app/output/reconciliation_report.json` for the default run, or at the path passed with `--out`.
