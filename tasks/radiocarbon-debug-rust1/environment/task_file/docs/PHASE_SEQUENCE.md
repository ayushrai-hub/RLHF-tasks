# Ordered phase-boundary inference

`phase_sequence` estimates boundary marginals for several unordered
archaeological phases whose relative order is known. Samples inside one phase
have no internal order, but phase 0 is older than phase 1, phase 1 is older than
phase 2, and so on.

The operation fields are:

```json
{
  "kind": "phase_sequence",
  "curve": [[cal_bp, c14_bp, sigma], ...],
  "phases": [
    {
      "samples": [
        {"lab_age_bp": 2110.0, "lab_sigma": 25.0, "reservoir_age": 20.0, "reservoir_sigma": 8.0}
      ],
      "min_span": 60,
      "max_span": 240
    }
  ],
  "start_cal_bp": 1800,
  "end_cal_bp": 2600,
  "step": 5,
  "min_gaps": [0],
  "max_gaps": [180],
  "levels": [0.6827, 0.9545]
}
```

There must be between 2 and 4 phases. Each phase must contain between 1 and 8
samples. Every sample is calibrated independently on the same grid using the
same likelihood definition as `calibrate`: reservoir correction is
`lab_age_bp - reservoir_age`, and the variance is `lab_sigma^2 +
curve_sigma^2 + reservoir_sigma^2`. The grid definition, sample uncertainty
rules, and HPD-level rules are the same as `calibrate` and `hpd`.

Each phase candidate is a boundary pair `[start_bp, end_bp]`, where `start_bp`
is the older boundary and `end_bp` is the younger boundary. Calendar BP
increases into the past, so valid candidates satisfy:

```text
start_bp >= end_bp
```

Both boundaries must be grid points. The phase span is:

```text
start_bp - end_bp
```

`min_span` and `max_span` are optional per phase. If present, they must be
finite, zero or greater, and `max_span` must be no smaller than `min_span`. If
`min_span` is omitted, the minimum span is zero. If `max_span` is omitted, the
phase has no upper span bound.

Adjacent phase gaps may be bounded with `min_gaps` and `max_gaps`. Each array
is optional. When present, it must contain exactly one fewer entry than
`phases`. Entry `i` applies between `phases[i]` and `phases[i + 1]`. The gap is:

```text
phases[i].end_bp - phases[i + 1].start_bp
```

Every minimum gap must be finite and zero or greater. Every maximum gap must be
finite and no smaller than the corresponding minimum. If `min_gaps` is omitted,
all minimum gaps are zero. If `max_gaps` is omitted, adjacent phases have no
upper gap bound.

For one phase candidate, the unnormalized phase weight is:

```text
product over samples in that phase of P(end_bp <= sample_cal_bp <= start_bp)
```

where each probability is the sample's independent normalized grid mass inside
that candidate interval. The full configuration weight is the product of the
phase-candidate weights for all phases. The prior over valid full
configurations is uniform. Keep every full configuration that has positive
finite weight and satisfies the span and adjacent gap bounds, then normalize
over those configurations. If no valid full configuration has positive finite
weight, the operation is an error.

After normalizing over full configurations, report each phase's boundary and
span marginals. Also report one adjacent gap marginal for each pair of adjacent
phases. Gap marginal `i` is the posterior distribution of:

```text
phases[i].end_bp - phases[i + 1].start_bp
```

using the same normalized full configurations and the same gap bounds described
above.

The documented maximum input size is part of the contract: the operation must
handle up to 4 phases, up to 8 samples per phase, and dense grids of several
hundred calendar points within the verifier timeout while preserving the exact
posterior semantics above.

The output is:

```json
{
  "phases": [
    {
      "phase": 0,
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
  ],
  "gap_posteriors": [
    {
      "gap": 0,
      "points": [[duration_years, probability], ...],
      "mean_years": 75.4,
      "mode_years": 80,
      "intervals": [{"level": 0.9545, "ranges": [[30, 140]], "mass": 0.96}]
    }
  ]
}
```

The `phases` array is sorted by increasing phase index. The `gap_posteriors`
array is sorted by increasing adjacent gap index and contains exactly one fewer
entry than `phases`. Start and end marginal `points` include every boundary grid
point from `start_cal_bp` through `end_cal_bp`, including zero-probability
points. Span and gap marginal `points` include every possible grid-aligned
duration from zero through the full grid width, including zero-probability
durations. HPD intervals use the same highest-probability selection rule as
`HPD.md`.

The JSON schema is strict. A phase object must contain only `phase`, `start`,
`end`, and `span`; the top-level `phase_sequence` output must contain only
`phases` and `gap_posteriors`. Internal helper data such as raw boundary
candidate lists or `boundary_pairs` must not be serialized.
