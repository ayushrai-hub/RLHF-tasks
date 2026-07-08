# Curve-mixture calibration

`curve_mixture_calibrate` calibrates one determination against several candidate
calibration curves when the correct curve model is uncertain. It returns the
joint posterior over calendar BP and curve model, plus the calendar and curve
marginals.

The operation fields are:

```json
{
  "kind": "curve_mixture_calibrate",
  "curves": [
    {"weight": 0.7, "curve": [[cal_bp, c14_bp, sigma], ...]},
    {"weight": 0.3, "curve": [[cal_bp, c14_bp, sigma], ...]}
  ],
  "lab_age_bp": 2110.0,
  "lab_sigma": 25.0,
  "reservoir_age": 20.0,
  "reservoir_sigma": 8.0,
  "start_cal_bp": 1800,
  "end_cal_bp": 2400,
  "step": 5,
  "levels": [0.6827, 0.9545]
}
```

There must be between 2 and 5 curve models. Each model weight must be finite and
greater than zero; weights are relative priors and are normalized internally.
Each model's curve must satisfy `CURVE.md`. The lab-age, reservoir, grid, and
HPD-level rules are the same as `calibrate` and `hpd`: `lab_sigma` must be
greater than zero, `reservoir_sigma` must be zero or greater, `start_cal_bp`
must be no greater than `end_cal_bp`, `step` must be a positive integer, and
each level must be greater than 0 and no greater than 1.

A curve model contributes to a grid point only if that grid point lies inside
that model's curve range. Every grid point in the requested calendar grid must
be covered by at least one curve model. For each covered pair
`[curve_index, cal_bp]`, interpolate that curve and use:

```text
corrected_age = lab_age_bp - reservoir_age
variance = lab_sigma^2 + curve_sigma^2 + reservoir_sigma^2
unnormalized_joint_weight = curve_prior_weight * normal_density(corrected_age - curve_c14_bp, variance)
```

The joint posterior over all covered `[curve_index, cal_bp]` pairs is normalized
to sum to one. If there are no covered pairs, or if all weights are zero or
non-finite, the operation is an error.

The output is:

```json
{
  "joint": [[curve_index, cal_bp, probability], ...],
  "points": [[cal_bp, probability], ...],
  "mean_cal_bp": 2101.2,
  "mode_cal_bp": 2095,
  "curve_posteriors": [[curve_index, probability], ...],
  "intervals": [
    {"level": 0.6827, "ranges": [[2055, 2130]], "mass": 0.6901}
  ]
}
```

`joint` is sorted by increasing `curve_index`, then increasing `cal_bp`, and
contains every covered curve/grid pair. `points` contains every requested
calendar grid point from `start_cal_bp` through `end_cal_bp`, sorted by
increasing calendar BP. `curve_posteriors` contains one row for every input curve
model, sorted by curve index. The mean, mode, and intervals are computed from
the calendar marginal; the mode is the lowest `cal_bp` among tied maximum
calendar-marginal probabilities. HPD intervals use the same rule as `HPD.md`.
