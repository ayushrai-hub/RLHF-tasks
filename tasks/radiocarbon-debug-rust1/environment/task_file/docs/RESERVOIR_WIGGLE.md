# Reservoir-shift wiggle matching

`reservoir_wiggle_match` dates a wiggle-matched sample series while estimating
one shared reservoir-age shift that applies to every sample in addition to each
sample's own `reservoir_age`.

The operation fields are:

```json
{
  "kind": "reservoir_wiggle_match",
  "curve": [[cal_bp, c14_bp, sigma], ...],
  "samples": [
    {
      "offset": 0,
      "lab_age_bp": 2110.0,
      "lab_sigma": 25.0,
      "reservoir_age": 20.0,
      "reservoir_sigma": 8.0
    }
  ],
  "anchor_start_bp": 1800,
  "anchor_end_bp": 2400,
  "anchor_step": 5,
  "shift_start": -40,
  "shift_end": 60,
  "shift_step": 5,
  "levels": [0.6827, 0.9545]
}
```

The curve, sample-count, offset, sample-uncertainty, anchor-grid, and HPD-level
rules are the same as `WIGGLE.md`. `shift_step` must be a positive integer and
`shift_start` must be no greater than `shift_end`.

For each candidate pair `[anchor_bp, reservoir_shift]`, place every sample at:

```text
sample_cal_bp = anchor_bp - offset
```

Candidates that place any sample outside the curve range are excluded. For every
remaining candidate, each sample uses:

```text
corrected_age = lab_age_bp - reservoir_age - reservoir_shift
variance = lab_sigma^2 + curve_sigma^2 + reservoir_sigma^2
```

For each valid pair, multiply the normal-density likelihoods for all samples,
including the normal-density constant factor. The prior over valid
`[anchor_bp, reservoir_shift]` pairs is uniform. The joint posterior over valid
pairs is normalized to sum to one. If there are no valid pairs, or if all valid
pairs have zero or non-finite weight, the operation is an error.

The output is:

```json
{
  "joint": [[anchor_bp, reservoir_shift, probability], ...],
  "anchor": {
    "points": [[anchor_bp, probability], ...],
    "mean_anchor_bp": 2104.5,
    "mode_anchor_bp": 2110,
    "intervals": [
      {"level": 0.6827, "ranges": [[2075, 2145]], "mass": 0.69}
    ]
  },
  "reservoir_shift": {
    "points": [[shift_years, probability], ...],
    "mean_years": 12.3,
    "mode_years": 10,
    "intervals": [
      {"level": 0.6827, "ranges": [[-5, 25]], "mass": 0.70}
    ]
  },
  "sample_calendar": [
    {"sample": 0, "mean_cal_bp": 2104.5, "mode_cal_bp": 2110}
  ]
}
```

`joint` is sorted by increasing `anchor_bp`, then increasing `reservoir_shift`.
The anchor marginal contains every valid anchor point. The reservoir-shift
marginal contains every shift-grid point. Modes use the lowest value among tied
maximum-probability points. For each sample-calendar summary, subtract that
sample's offset from the anchor mean and anchor mode. HPD intervals use the same
rule as `HPD.md`, with `anchor_step` for the anchor marginal and `shift_step`
for the reservoir-shift marginal.
