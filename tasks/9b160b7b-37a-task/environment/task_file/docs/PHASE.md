# Phase-boundary inference

`phase_bounds` estimates the older and younger boundaries of one unordered
archaeological phase. Samples are known to belong somewhere inside the phase, but
there is no internal order among them.

The operation fields are:

```json
{
  "kind": "phase_bounds",
  "curve": [[cal_bp, c14_bp, sigma], ...],
  "samples": [
    {"lab_age_bp": 2110.0, "lab_sigma": 25.0, "reservoir_age": 20.0, "reservoir_sigma": 8.0}
  ],
  "start_cal_bp": 1800,
  "end_cal_bp": 2400,
  "step": 5,
  "levels": [0.6827, 0.9545]
}
```

There must be between 2 and 10 samples. Each sample is calibrated independently
on the same grid using the same likelihood definition as `calibrate`. The grid
definition and sample uncertainty rules are the same as `calibrate`.

A candidate phase is a pair `[start_bp, end_bp]`, where `start_bp` is the older
boundary and `end_bp` is the younger boundary. Since calendar BP increases into
the past, valid candidates satisfy:

```text
start_bp >= end_bp
```

Both boundaries must be grid points. The candidate weight is:

```text
product over samples of P(end_bp <= sample_cal_bp <= start_bp)
```

where each probability is the sample's independent normalized grid mass inside
the candidate interval. The prior over valid boundary pairs is uniform. Keep
every candidate with positive finite weight, normalize those weights so the
`boundary_pairs` probabilities sum to one, and omit zero-weight pairs from
`boundary_pairs`. If no candidate has positive finite weight, the operation is
an error.

The output is:

```json
{
  "boundary_pairs": [[start_bp, end_bp, probability], ...],
  "start": {
    "points": [[cal_bp, probability], ...],
    "mean_cal_bp": 2310.4,
    "mode_cal_bp": 2320,
    "intervals": [{"level": 0.9545, "ranges": [[2250, 2380]], "mass": 0.96}]
  },
  "end": {
    "points": [[cal_bp, probability], ...],
    "mean_cal_bp": 2050.2,
    "mode_cal_bp": 2040,
    "intervals": [{"level": 0.9545, "ranges": [[1980, 2120]], "mass": 0.95}]
  },
  "span": {
    "points": [[duration_years, probability], ...],
    "mean_years": 260.2,
    "mode_years": 280,
    "intervals": [{"level": 0.9545, "ranges": [[160, 380]], "mass": 0.96}]
  }
}
```

`boundary_pairs` are sorted by increasing `start_bp`, then increasing `end_bp`.
Start and end marginal `points` include every boundary grid point from
`start_cal_bp` through `end_cal_bp`, including zero-probability points. Span
marginal `points` include every possible grid-aligned duration from zero through
the full grid width, including zero-probability durations. Start, end, and span
marginal `points` are sorted by increasing value. HPD intervals use the same
highest-probability selection rule as `HPD.md`.
