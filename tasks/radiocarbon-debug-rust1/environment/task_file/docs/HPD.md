# Highest-posterior-density ranges

`hpd` uses the same fields as `calibrate` and adds:

```json
"levels": [0.6827, 0.9545]
```

Every level must be greater than 0 and no greater than 1. The output keeps the
calibration summary and adds interval reports:

```json
{
  "points": [[cal_bp, probability], ...],
  "mean_cal_bp": 2101.2,
  "mode_cal_bp": 2095,
  "intervals": [
    {"level": 0.6827, "ranges": [[2055, 2130]], "mass": 0.6901}
  ]
}
```

For each level, select grid points in descending probability order until the
selected mass is at least the requested level. Ties are resolved by lower
`cal_bp`. Convert the selected grid points into closed ranges. Consecutive
points whose `cal_bp` values differ by exactly `step` are part of the same
range; gaps start a new range. Ranges are sorted by increasing calendar BP.

`mass` is the actual selected probability mass, not the requested level.
