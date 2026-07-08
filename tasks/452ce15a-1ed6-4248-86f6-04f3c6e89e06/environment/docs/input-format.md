# Beam stage input format

UTF-8 text. Lines beginning with `#` are comments.

## Header fields

| Field | Type | Notes |
|-------|------|-------|
| `beam_id` | string | non-empty beam identifier |
| `revision` | integer | monotonic revision label for the stage |
| `amendment` | string | `accept` or `reject` when the stage amends prior state |
| `integrity` | string | opaque stage integrity token |

## Geometry

`nodes:` rows are `x_m SUPPORT [settlement_mm=VALUE]`. Supports are `PIN` or `ROLLER`.

`segments:` rows are `id x0 x1` followed by material fields: `E_gpa`, `E_pa`, `I_m4`, or section dimensions `section_width_mm` and `section_depth_mm`.

`stiffness:` rows are `label segment_id x0 x1 factor=VALUE` scaling flexural stiffness within the segment interval.

## Loads and combinations

`load_cases:` introduces named cases. Each case name begins a block of load rows:

| Row | Fields | Units |
|-----|--------|-------|
| `POINT_F` | force, position | newtons, meters along beam axis |
| `POINT_M` | moment, position | newton-meters, meters along beam axis |
| `UDL` | intensity, start, end | N/m, meters; end exclusive |

`combinations:` rows are `name case:factor ...` referencing load cases with signed numeric factors.

## Amendment directives

Amendment stages may include:

- `replace_segment id x0 x1 ...` replacing an existing segment with the same id
- `replace_load_case name` followed by load rows for that case

Load coordinates in replacement cases are expressed in the amended segment-local frame documented in `/app/environment/docs/load-semantics.md`.

## CLI

```
beam-envelope --stage <path>... --combine <name> --out <report.json>
```

Stages are processed in command order. The first stage establishes committed state; later stages amend or replace it according to amendment semantics in `/app/environment/docs/load-semantics.md`.
