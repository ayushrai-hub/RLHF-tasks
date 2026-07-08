# Calibration curve

A curve is an array of rows:

```json
[[cal_bp, c14_bp, sigma], ...]
```

`cal_bp` is the calendar year BP. `c14_bp` is the curve's modeled radiocarbon
age at that calendar year. `sigma` is the one-sigma uncertainty of the curve at
that row.

Curve validity:

- at least two rows
- every row has exactly three finite numbers
- `cal_bp` values are strictly increasing
- every `sigma` is greater than zero

`interpolate` has fields:

```json
{"kind": "interpolate", "curve": [...], "cal_bp": 1234.5}
```

`cal_bp` must lie inside the closed range covered by the curve. The output is:

```json
{"c14_bp": 1200.0, "sigma": 18.0}
```

Both `c14_bp` and `sigma` are linearly interpolated between the two bracketing
curve rows. Exact curve-row hits return that row's values.
