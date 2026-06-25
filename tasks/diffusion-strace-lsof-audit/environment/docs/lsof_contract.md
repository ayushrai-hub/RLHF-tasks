# Lsof reconstruction contract

The lsof lane parses fenced excerpt bodies into per-process descriptor snapshots.

## Continuation rows

- A primary row begins with a PID in the first column.
- Continuation rows begin with leading whitespace; they belong to the current PID and must be counted in that snapshot's descriptor total.
- Skipping continuation rows under-counts paired snapshots and misses descriptor leak findings.

## Paths outside run_dir

- Scan line tokens for absolute paths starting with `/`.
- Strip a trailing ` (deleted)` suffix from path tokens before prefix comparison.
- Any path that does not begin with the configured `run_dir` prefix is outside the run workspace.

## Paired snapshots and descriptor leak

- When a runbook contains two or more `lsof` fences with the same `source_path`, compare the first and last snapshot totals.
- `fd_delta` is the later total minus the earlier total.
- A `descriptor_leak` finding fires only when `fd_delta` is strictly greater than `fd_leak_threshold` from `/app/policy/workflow_policy.toml` (equality does not fire).
