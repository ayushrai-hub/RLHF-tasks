# Data flow

## Inputs

`units.jsonl` — one candidate dispatch unit per line:

```json
{"id": "u_0001", "fuel": "gas", "bus": "bus_03", "feeder": "f_07",
 "capacity_kw": 140, "avail": 0.96, "emission_rate": 0.42,
 "responsiveness": 0.6, "min_stable": 0.2, "degraded": false}
```

`config.json` — the dispatch configuration:

```json
{
  "buses": ["bus_00", "..."],
  "feeders": ["f_00", "..."],
  "fuels": ["solar", "wind", "battery", "gas", "diesel"],
  "total_demand_kw": 22376,
  "emission_budget": 3813.7,
  "renewable_min_fraction": 0.35,
  "reserve_requirement_kw": 2685,
  "per_bus_min_kw": {"bus_00": 700, "...": 0},
  "conflict_pairs": [["u_0003", "u_0044"], ["...", "..."]],
  "mandatory_online_units": ["u_0123", "..."],
  "max_committed_thermal": 40,
  "nominal_frequency": 50.0
}
```

`max_committed_thermal` caps how many synchronous (gas/diesel) generators may be
brought online and dispatched (`dispatch_fraction > 0`) in the period; units left
at `dispatch_fraction == 0` but carrying `reserve_share` do not count against it.

## Output

`dispatch.json` — a single object:

```json
{
  "allocations": [
    {"unit_id": "u_0001", "dispatch_fraction": 0.34, "reserve_share": 0.0}
  ],
  "frequency_setpoint": 49.66
}
```

`allocations` carries one entry per unit (each unit id exactly once);
`dispatch_fraction` and `reserve_share` are in [0, 1]. `frequency_setpoint` is a
single network-wide number in [49.0, 51.0].

The quality metrics, strict score formula, and target thresholds are documented
in `scoring.md`. The implementation should treat `scripts/model.py` as the
authoritative calculation for service balance, emissions, reserve response, and
settled frequency.

## Dynamic robustness

The verifier reruns the compiled binary after replacing both input files with
renamed, capacity-tight alternate instances and a tighter high-renewable,
low-thermal-commitment instance. These instances use the same schema and scoring
model, but may raise `renewable_min_fraction` into the `0.59` to `0.66` range,
tighten reserve/emissions/per-bus/commitment limits, and set fractional
`total_demand_kw` values. A solution must recompute dispatch from the current
files rather than relying on public ids or fixed capacities. See `scoring.md`
for the raw, strict, renewable, and commitment gates for each dynamic profile.

Demand coverage is an exact floating-point hard constraint in `model.py`.
Diagnostic messages round supply for readability, so a message such as
`supply 19318 < demand 19317.88` can still mean the computed supply is a small
fraction below demand. Robust implementations should target a small positive
supply buffer while staying under the oversupply cap.
