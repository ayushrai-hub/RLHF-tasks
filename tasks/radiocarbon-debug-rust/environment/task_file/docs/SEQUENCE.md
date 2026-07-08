# Stratigraphic sequence

`sequence` calibrates several determinations on the same calendar grid and
conditions them on a known oldest-to-youngest order. Calendar BP increases into
the past, so the first sample must have a calendar BP greater than or equal to
the second sample, the second greater than or equal to the third, and so on.

The operation fields are:

```json
{
  "kind": "sequence",
  "curve": [[cal_bp, c14_bp, sigma], ...],
  "samples": [
    {"lab_age_bp": 2110.0, "lab_sigma": 25.0, "reservoir_age": 20.0, "reservoir_sigma": 8.0}
  ],
  "start_cal_bp": 1800,
  "end_cal_bp": 2400,
  "step": 5,
  "min_gaps": [0],
  "max_gaps": [120],
  "levels": [0.6827, 0.9545]
}
```

There must be between 2 and 6 samples. Each sample uses the same calibration
likelihood definition as `calibrate`: reservoir correction is `lab_age_bp -
reservoir_age`, and the variance is `lab_sigma^2 + curve_sigma^2 +
reservoir_sigma^2`. `lab_sigma` must be greater than zero, `reservoir_sigma`
must be zero or greater, and every grid point must lie inside the curve range.
Every level must be greater than 0 and no greater than 1.

Adjacent sequence gaps may be bounded with `min_gaps` and `max_gaps`. Each array
is optional. When present, it must contain exactly one fewer entry than
`samples`. Entry `i` applies to the pair `samples[i]`, `samples[i + 1]`, and the
gap is:

```text
samples[i].calendar_bp - samples[i + 1].calendar_bp
```

Every minimum gap must be finite and zero or greater. Every maximum gap must be
finite and no smaller than the corresponding minimum. If `min_gaps` is omitted,
all minimum gaps are zero. If `max_gaps` is omitted, adjacent gaps have no upper
bound.

First form each sample's independent normalized calibration grid. The
`order_probability` is the total probability, under those independent grids,
that the oldest-to-youngest order and any adjacent gap bounds are satisfied. If
this probability is zero or non-finite, the operation is an error. Each reported
sample distribution is that sample's marginal grid after conditioning on the
order and gap bounds; every marginal grid must sum to one within normal
floating-point rounding.

The output is:

```json
{
  "order_probability": 0.42,
  "marginals": [
    {
      "sample": 0,
      "points": [[cal_bp, probability], ...],
      "mean_cal_bp": 2150.2,
      "mode_cal_bp": 2160,
      "intervals": [
        {"level": 0.6827, "ranges": [[2110, 2190]], "mass": 0.70}
      ]
    }
  ]
}
```

The HPD interval rule for each marginal is exactly the same as `HPD.md`.
