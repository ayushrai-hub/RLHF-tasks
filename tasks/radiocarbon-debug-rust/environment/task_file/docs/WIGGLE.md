# Wiggle matching

`wiggle_match` dates a series of related radiocarbon determinations whose
calendar offsets are known, such as measurements along a tree-ring block or a
short-lived stratified series. It returns a posterior distribution over the
calendar BP of the anchor sample.

The operation fields are:

```json
{
  "kind": "wiggle_match",
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
  "levels": [0.6827, 0.9545]
}
```

There must be between 2 and 12 samples. Sample offsets are finite calendar-year
offsets from the anchor toward younger material, so a sample's calendar BP at a
candidate anchor is `anchor_bp - offset`. Offsets must be zero or greater,
strictly increasing in the order provided, and the first offset must be zero.
`anchor_step` must be a positive integer and `anchor_start_bp` must be no greater
than `anchor_end_bp`.

For each candidate anchor point `anchor_start_bp + n * anchor_step` not greater
than `anchor_end_bp`, place every sample at `anchor_bp - offset`. Candidates
that place any sample outside the curve range are excluded from the posterior.
For every remaining candidate, multiply the normal-density likelihoods for all
samples. Each sample uses the same correction and variance as `calibrate`:

```text
corrected_age = lab_age_bp - reservoir_age
variance = lab_sigma^2 + curve_sigma^2 + reservoir_sigma^2
```

The prior over valid anchor points is uniform. The posterior over valid anchor
points is normalized to sum to one. If there are no valid candidate anchors, or
if all valid candidates have zero or non-finite weight, the operation is an
error.

The output is:

```json
{
  "points": [[anchor_bp, probability], ...],
  "mean_anchor_bp": 2104.5,
  "mode_anchor_bp": 2110,
  "intervals": [
    {"level": 0.6827, "ranges": [[2075, 2145]], "mass": 0.69}
  ],
  "sample_calendar": [
    {"sample": 0, "mean_cal_bp": 2104.5, "mode_cal_bp": 2110}
  ]
}
```

The anchor mode is the lowest anchor BP among tied maximum-probability points.
For each sample-calendar summary, subtract that sample's offset from the anchor
mean and anchor mode. HPD intervals use the same rule as `HPD.md`.
