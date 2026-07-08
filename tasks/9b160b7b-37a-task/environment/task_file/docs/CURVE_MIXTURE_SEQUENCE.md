# Ordered sequence with curve-model uncertainty

`curve_mixture_sequence` dates an oldest-to-youngest sequence when the whole
sequence shares one uncertain calibration curve model. This is different from
calibrating each sample against a pre-mixed calendar marginal: one curve model
is chosen for the full sequence, and the sequence order evidence updates the
curve-model posterior.

The operation fields are:

```json
{
  "kind": "curve_mixture_sequence",
  "curves": [
    {"weight": 0.7, "curve": [[cal_bp, c14_bp, sigma], ...]},
    {"weight": 0.3, "curve": [[cal_bp, c14_bp, sigma], ...]}
  ],
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

There must be between 2 and 5 curve models. Each model weight must be finite and
greater than zero; weights are relative priors and are normalized internally.
Every model curve must satisfy `CURVE.md`. A model contributes likelihood only
at requested calendar grid points inside that model's curve range; different
models may cover different calendar domains. Every requested calendar grid point
must be covered by at least one model. The sample-count, sample uncertainty,
grid, adjacent gap, and HPD-level rules are the same as `SEQUENCE.md`.

For each curve model, calibrate every sample against that model on the requested
grid points covered by the model, assigning zero probability to grid points
outside that model's range, and normalize each sample's independent grid over
the model-covered points. Then condition those independent grids on the
oldest-to-youngest order and adjacent gap bounds exactly as in `SEQUENCE.md`.
This gives that model's `order_probability` and conditioned sample marginals.
A model whose covered support cannot satisfy the order and gap constraints has
`order_probability` zero and posterior zero, but it is still reported in
`model_order_probabilities`. The operation is an error only if every model has
zero or non-finite order evidence.

The shared-curve posterior for model `m` is:

```text
model_posterior_m = model_weight_m * order_probability_m / sum over models(model_weight * order_probability)
```

The reported top-level `order_probability` is prior-normalized:

```text
sum over models(model_weight * order_probability_m) / sum over models(model_weight)
```

Each reported sample marginal is the model-posterior-weighted mixture of that
sample's conditioned sequence marginal under each curve model. Means, modes, and
HPD intervals are computed from these mixed sample marginals.

The output is:

```json
{
  "order_probability": 0.42,
  "model_order_probabilities": [
    [curve_index, order_probability_under_curve, model_posterior]
  ],
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

`model_order_probabilities` contains one row for every input curve model, sorted
by curve index. `marginals` contains one row for every input sample, sorted by
sample index. Every marginal `points` array contains every requested calendar
grid point from `start_cal_bp` through `end_cal_bp`, sorted by increasing
calendar BP. Modes use the lowest `cal_bp` among tied maximum-probability
points. HPD intervals use the same rule as `HPD.md`.
