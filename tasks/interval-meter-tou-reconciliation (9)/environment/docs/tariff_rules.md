# Tariff rules

The active tariff is the JSON file named by the run config's `tariff_path`. The bundled file is only the production default; tests and operators may point the binary at another tariff file with the same shape.

`timezone` is a label and is copied to the report as written. Timestamp tiering uses the local date and clock fields written in each interval slot start timestamp; the numeric offset is used for absolute ordering and elapsed-time gap math.

`register_max_kwh` supplies the rollover wrap value. `interval_minutes` controls demand extrapolation, missing-slot counts, and the size of the generated slots used when an observed register span must be prorated.

`seasons.summer.start_mmdd` and `seasons.summer.end_mmdd` are inclusive local month/day bounds. Dates outside that inclusive range use the winter table. If a configured summer range wraps the end of the calendar year, dates on either side of the wrap are summer.

`windows.summer` and `windows.winter` each define `off_peak`, `mid_peak`, and `on_peak` arrays of `["HH:MM", "HH:MM"]` clock windows. A window includes its start boundary and excludes its end boundary. Overnight windows wrap midnight using the same rule. A generated interval slot that straddles two windows or a season boundary is prorated by exact overlap seconds instead of being assigned wholly to the tier at the slot start.

Demand peak is the maximum prorated slot kW sample (`slot_kwh * 60 / interval_minutes`). Gap intervals are counted from full elapsed absolute time between consecutive valid readings. Register rollover adds `(register_max_kwh - previous_register) + current_register` for the observed interval delta before proration. Optional CSV quality values, duplicate timestamp corrections, and duplicate reset baselines are interpreted as described in `/app/environment/docs/operations.md`.
