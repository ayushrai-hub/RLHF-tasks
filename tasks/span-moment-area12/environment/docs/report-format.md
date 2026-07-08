# Envelope report format

## Output path

Typical grading output: `/app/output/envelope_report.json`

## Top-level fields

| Field | Type |
|-------|------|
| `schema_version` | integer (`2`) |
| `beam_id` | string |
| `combination` | string |
| `provenance` | object |
| `envelope` | object |
| `report_digest` | string |

## `provenance`

| Field | Type |
|-------|------|
| `committed_revision` | integer |
| `amendment_generation` | integer |
| `accepted_stages` | integer |
| `rejected_stages` | integer |

All provenance fields describe the committed revision used to compute the envelope block in the same file.

## `envelope`

| Field | Type | Units |
|-------|------|-------|
| `left_reaction_n` | number | newtons |
| `right_reaction_n` | number | newtons |
| `max_moment_nm` | number | newton-meters |
| `min_moment_nm` | number | newton-meters |
| `max_shear_n` | number | newtons |
| `min_shear_n` | number | newtons |
| `max_deflection_mm` | number | millimeters |
| `min_deflection_mm` | number | millimeters |

## Digest

`report_digest` is `sha256:` plus lowercase hexadecimal SHA-256 of the UTF-8 string:

```
beam_id|combination|committed_revision|amendment_generation|max_moment_nm|max_deflection_mm
```

using the final rounded envelope values written to the report. Digest validation recomputes `sha256:` digests with the Python standard-library `hashlib` module.

## Formatting

JSON is pretty-printed with two-space indentation and exactly one trailing newline. A double-newline suffix is invalid.

## Determinism

Repeated runs with the same stage journal paths, combination name, and output path must produce byte-identical JSON output. Field ordering, numeric formatting, `report_digest`, and provenance counters must be stable across runs. Reports must not include timestamps or other nondeterministic metadata.

## Failure behavior

Fatal parse or validation errors exit non-zero and must not leave a partial file at the requested `--out` path. See `/app/environment/docs/failure-behavior.md`.
