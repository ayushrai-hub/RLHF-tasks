# Scoring Contract

`/app/task_file/scripts/model.py` is the authoritative evaluator for a dispatch
plan. It loads `input_data/units.jsonl`, `input_data/config.json`, and
`output_data/dispatch.json`, then computes hard-constraint validity and quality
metrics.

## Hard Constraints

A dispatch with any hard-constraint violation receives `total_score = 0.0`.
The plan must:

- allocate every unit id exactly once
- keep `dispatch_fraction`, `reserve_share`, and `frequency_setpoint` in range
- meet `total_demand_kw` without exceeding the oversupply cap
- stay within `emission_budget`
- meet `renewable_min_fraction`
- meet every `per_bus_min_kw`
- meet `reserve_requirement_kw`
- keep every `mandatory_online_units` entry at or above its `min_stable`
- avoid dispatching both units in any `conflict_pairs` entry above `0.5`
- keep dispatched gas/diesel units within `max_committed_thermal`

## Base Score

The base evaluator reports:

- `total_score`
- `service_score`
- `efficiency_score`
- `stability_score`
- `settled_frequency`
- `freq_gap`
- `renewable_fraction`
- `degraded_output`
- `committed_thermal`

The dispatch target is:

- `total_score >= 0.99`
- `service_score >= 0.95`
- `efficiency_score >= 0.86`
- `stability_score >= 0.95`
- `renewable_fraction >= 0.60`
- `freq_gap <= 0.02`
- `degraded_output <= 800.0`

`service_score` rewards matching supply tightly to demand. `efficiency_score`
uses the non-linear emissions curve from `model.py`, so high dispatch fractions
on thermal units are more expensive than their linear output alone suggests.
`stability_score` rewards a frequency setpoint close to the settled frequency
computed from supply/demand imbalance, reserve ratio, near-conflict feeder
pairs, and synchronous inertia.

## Strict Score

The strict planning score is:

```text
score = total_score * 0.94
if freq_gap > 0.04: score *= 0.50
if efficiency_score < 0.82: score *= 0.55
if service_score < 0.92: score *= 0.85
if renewable_fraction < 0.55: score *= 0.90
if degraded_output > 800.0: score *= 0.85
total_score_strict = round(clamp(score, 0.0, 1.0), 4)
```

The dispatch target is `total_score_strict >= 0.92`.

## Dynamic Instance Gates

In addition to the public instance checks above, the verifier replaces both
input files with deterministic alternate instances. These dynamic checks use
the same schema and the same base and strict scoring functions; the binary must
read the current input files and recompute the dispatch.

### Capacity-Tight Renamed Profile

The verifier runs five renamed, capacity-tight alternate instances. The
alternate units are renamed, capacities and availabilities are perturbed, bus
and feeder assignments are shifted, `renewable_min_fraction` is raised into the
`0.59` to `0.63` range, and `total_demand_kw` may be fractional.

For every alternate instance, the dispatch must satisfy all hard constraints and
clear both quality gates:

- `total_score >= 0.985`
- `total_score_strict >= 0.91`

### Tight Commitment Profile

The verifier also runs one tighter commitment instance derived from the dynamic
profile. It raises `renewable_min_fraction` to `0.66`, increases the reserve
requirement, tightens the emissions budget, raises every per-bus minimum, and
reduces `max_committed_thermal`. This profile must satisfy all hard constraints
and clear these additional gates:

- `total_score >= 0.99`
- `total_score_strict >= 0.92`
- `renewable_fraction >= 0.70`
- `committed_thermal <= max_committed_thermal`

Because demand coverage is checked using floating-point arithmetic, do not stop
as soon as a rounded printed supply appears to meet demand. Target a small
positive supply buffer while keeping `service_score` high and staying below the
oversupply cap.
