# Contract

See the linked documents for the full specification:

- `input-format.md` — beam stage journal layout, amendment directives, and CLI
- `load-semantics.md` — sign conventions, amendment commit rules, discontinuity sides, and equilibrium invariants
- `report-format.md` — envelope report JSON schema and digest formation
- `failure-behavior.md` — fatal error exit semantics and output cleanup

## Report schema

Output path: `/app/output/envelope_report.json`

| Field | Type | Description |
|-------|------|-------------|
| `schema_version` | integer | Always **2** |
| `beam_id` | string | Committed beam identifier |
| `combination` | string | Selected load combination name |
| `provenance` | object | Committed revision counters for the envelope block in this file |
| `envelope` | object | Reaction and response extrema for the selected combination |
| `report_digest` | string | `sha256:` plus lowercase hex SHA-256 over the canonical digest string in `report-format.md` |

`provenance` fields: `committed_revision`, `amendment_generation`, `accepted_stages`, `rejected_stages`.

`envelope` fields: `left_reaction_n`, `right_reaction_n`, `max_moment_nm`, `min_moment_nm`, `max_shear_n`, `min_shear_n`, `max_deflection_mm`, `min_deflection_mm`.

Digest checks recompute `sha256:` digests with the Python standard-library `hashlib` module.
