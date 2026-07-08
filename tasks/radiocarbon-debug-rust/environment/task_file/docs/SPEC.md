# radiocal contract

The binary is invoked as:

```text
radiocal <cases.json>
```

It reads exactly one positional argument, never reads stdin, and prints one JSON
array to stdout. Supplying zero or more than one positional argument is a
process-level error: the process must exit nonzero and must not print a JSON
result array. The input is an array of cases:

```json
[
  {"id": "case-id", "ops": [ ... operations ... ]}
]
```

The output is an array with the same number of cases in the same order. Each case
object is:

```json
{"id": "case-id", "results": [ ... results ... ]}
```

Each operation result is:

```json
{"kind": "<operation kind>", "output": <operation output or null>, "error": false}
```

If an operation is malformed or outside the domain described in these docs, the
result for that operation must be:

```json
{"kind": "<operation kind>", "output": null, "error": true}
```

The process should still exit successfully for per-operation errors. Unknown
operation kinds are operation errors. Numbers must be finite. Arrays must have
the documented lengths. Results must be deterministic. Numeric outputs are
checked against the documented formulas with absolute tolerance `2e-8` plus
relative tolerance `2e-8 * abs(expected)`; rounded display values may fail.

Supported operations:

- `interpolate`: see `CURVE.md`
- `calibrate`: see `CALIBRATE.md`
- `hpd`: see `HPD.md`
- `curve_mixture_calibrate`: see `CURVE_MIXTURE.md`
- `combine`: see `COMBINE.md`
- `sequence`: see `SEQUENCE.md`
- `curve_mixture_sequence`: see `CURVE_MIXTURE_SEQUENCE.md`
- `wiggle_match`: see `WIGGLE.md`
- `reservoir_wiggle_match`: see `RESERVOIR_WIGGLE.md`
- `phase_bounds`: see `PHASE.md`
- `phase_sequence`: see `PHASE_SEQUENCE.md`

The task uses calendar years BP, where 0 BP is CE 1950 and larger values are
older. Radiocarbon ages are also in BP.
