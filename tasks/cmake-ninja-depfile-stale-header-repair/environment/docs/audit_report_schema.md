# Build audit report schema

Command: `python3 /app/scripts/build_audit.py --fixture PATH --output PATH`

## Arguments

- `--fixture` and `--output` must be absolute paths; otherwise exit non-zero and print `absolute` on stderr.
- Each fixture `touch_entries[].path` must exist; missing paths exit non-zero.

## Fixture shape

Fixtures are JSON objects with:

| Field | Type | Description |
|-------|------|-------------|
| `schema_version` | int | Always `1` |
| `workload_id` | string | Copied into the report |
| `touch_entries` | array | Ordered touch list (see below) |

Each `touch_entries` item is an object with:

| Field | Type | Description |
|-------|------|-------------|
| `path` | string | Absolute header path to touch |
| `token` | string | Appended as `// depfix-touch-token=<token>` on its own line |

## Touch replay

For each `touch_entries` item in order:

1. Record the current byte size of `/app/build/.ninja_log` (zero if missing).
2. Append `// depfix-touch-token=<token>` on its own line to the header file (UTF-8).
3. Run `ninja -C /app/build`.

The saved offset is always at the end of a complete log line; read from that byte without skipping or discarding the first entry.

## Ninja log parsing

From the saved offset onward, each non-empty, non-comment line with at least four tab-separated fields counts as a rebuild when field 1 and field 2 differ. Copy field 4 verbatim into the working set (no path rewriting).

Merge entries from all touches, drop only exact duplicate strings, then sort the final list lexicographically.

## Output JSON

UTF-8 JSON written to `--output` with a trailing newline and exactly these keys:

| Key | Type | Description |
|-----|------|-------------|
| `schema_version` | int | Always `1` |
| `workload_id` | string | Copied from fixture |
| `touch_count` | int | Length of `touch_entries` |
| `rebuilt_targets` | string[] | Sorted rebuilt output paths |
