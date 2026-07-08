# Output Format Specification

The results output file must be saved at `/app/output/results.json`.

## Top-level shape

- `scenarios`: array of scenario objects, sorted deterministically by flag name (alphabetical) and flag value (`false` < `true`).
- `summary`: aggregate counts and `signature_hash`.

## Per-scenario fields

Each scenario object contains:

- `flags`: object mapping flag names to booleans for that scenario.
- `cycle_nodes`: sorted list of task IDs on an active cycle (empty when acyclic).
- `ordering`: topological ordering with alphabetical tie-breaking when acyclic; empty array when cyclic.
- `implicit_edges`: array of `{from, to}` objects for resolved parallel resource conflicts, sorted by `from` then `to`.

## Summary fields

- `scenarios_checked`: total valid scenarios evaluated.
- `cyclic_count`: scenarios with non-empty `cycle_nodes`.
- `acyclic_count`: scenarios with empty `cycle_nodes`.
- `signature_hash`: lowercase hex SHA-256 digest of the canonical scenario serialization (acyclic scenarios contribute comma-joined `ordering`; cyclic scenarios contribute `cycle:` prefixed comma-joined `cycle_nodes`; scenarios joined with `;`).
