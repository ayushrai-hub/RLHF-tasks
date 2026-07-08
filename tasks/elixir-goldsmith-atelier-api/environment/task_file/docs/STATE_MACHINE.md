# State machine

```
ingot_selected ─► assayed ─► cast_active ─► cast_complete ─► chased ─► hallmarked ─► released
```

| Stage | Mutations allowed | Notes |
|---|---|---|
| `ingot_selected` | `assign`, `assay`, `advance-stage→assayed` (needs ≥1 assay) | Initial state for every new piece |
| `assayed` | `assign`, `assay`, `advance-stage→cast_active` | No additional preconditions |
| `cast_active` | `cast`, `advance-stage→cast_complete` (most recent casting `ends_at ≤ now`) | A piece can have multiple casting rows (rework); the most recent governs |
| `cast_complete` | `advance-stage→chased` | No preconditions |
| `chased` | `hallmark`, `advance-stage→hallmarked` (needs ≥1 hallmark) | Hallmarks may be recorded multiple times before transitioning |
| `hallmarked` | `release` | `advance-stage` returns `409 wrong_stage` here |
| `released` | none | Terminal. Any mutation returns `409 already_released` |

## Transition semantics

- `POST /pieces/:id/advance-stage` takes an empty body `{}` and infers the next
  stage from the current one. It cannot skip or reverse.
- On success, `advance-stage` returns exactly `{piece_id, stage}` with no
  serial, timestamp, or previous-stage field.
- `POST /pieces/:id/release` is the only path from `hallmarked → released`.
- Releasing stamps `released_at = now()`.
- On success, `release` returns `{piece_id, stage, released_at}`.
- Each successful transition (via `advance-stage` or `release`) appends one
  `audit_entries` row.

## Why `advance-stage` looks at "most recent" casting

A piece in `cast_active` may have been recast (rework). The handler should
look at the casting row with the maximum `ends_at` for that piece and only
permit the transition once that window has ended (`ends_at ≤ now()`).
