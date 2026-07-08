# Calibration

`calibrate` converts one laboratory radiocarbon determination into a normalized
calendar-year probability grid. The operation fields are:

```json
{
  "kind": "calibrate",
  "curve": [[cal_bp, c14_bp, sigma], ...],
  "lab_age_bp": 2110.0,
  "lab_sigma": 25.0,
  "reservoir_age": 20.0,
  "reservoir_sigma": 8.0,
  "start_cal_bp": 1900,
  "end_cal_bp": 2300,
  "step": 5
}
```

`lab_sigma` must be greater than zero. `reservoir_sigma` must be zero or greater.
`start_cal_bp` must be no greater than `end_cal_bp`. `step` must be a positive
integer. Every grid point `start_cal_bp + n * step` that is not greater than
`end_cal_bp` must be inside the curve range.

Before comparing with the curve, the lab age is corrected as:

```text
corrected_age = lab_age_bp - reservoir_age
```

At each grid point, interpolate the curve. The unnormalized likelihood is the
normal density for the difference between `corrected_age` and interpolated
`c14_bp`, using this variance:

```text
lab_sigma^2 + curve_sigma^2 + reservoir_sigma^2
```

The constant factor of the normal density is part of the likelihood. The
`points` probabilities are normalized so their sum is exactly one within normal
floating-point rounding.

The output is:

```json
{
  "points": [[cal_bp, probability], ...],
  "mean_cal_bp": 2101.2,
  "mode_cal_bp": 2095
}
```

The mean is the probability-weighted mean of the grid points. The mode is the
lowest `cal_bp` among grid points tied for the largest probability.
