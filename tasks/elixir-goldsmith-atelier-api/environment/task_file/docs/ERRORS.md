# Error codes

Every non-2xx response body should look like this:

```json
{"error": "<machine_code>", "detail": "<human string>"}
```

Keep `detail` readable for callers. The machine code goes in `error`.

| Code | HTTP | When |
|---|---|---|
| `route_not_found` | 404 | Unknown path |
| `piece_not_found` | 404 | URL `:id` does not exist in `pieces` |
| `goldsmith_not_found` | 404 | URL `:gid`, `mentor_id`, or `goldsmith_id` body field does not exist |
| `crucible_not_found` | 404 | `crucible_id` body field does not exist |
| `already_assigned` | 409 | Piece is already owned by some goldsmith |
| `already_released` | 409 | Mutating call against a piece whose stage is `released` |
| `wrong_stage` | 409 | Stage doesn't permit the transition or operation |
| `missing_assay` | 409 | `ingot_selected → assayed` attempted with zero assays |
| `missing_hallmark` | 409 | `chased → hallmarked` attempted with zero hallmarks |
| `crucible_overlap` | 409 | New casting overlaps an existing window on the same crucible |
| `goldsmith_busy` | 409 | New casting overlaps any window for the same goldsmith |
| `duplicate_name` | 409 | Goldsmith `name` already exists |
| `duplicate_serial` | 409 | Piece `serial` already exists |
| `ts_not_monotonic` | 409 | New hallmark would land at or before this goldsmith's most recent existing hallmark |
| `alloy_grade_incompatible` | 422 | `piece.alloy_grade` is not in the crucible's `permitted_alloys` |
| `rank_insufficient` | 422 | Goldsmith rank is below the floor required for the piece's alloy grade (only masters can pour 24K) |
| `empty_lineage` | 422 | `/lineage-grade` found fewer than 2 hallmarked ancestors |
| `invalid_body` | 422 | JSON malformed or top-level not an object |
| `missing_field` | 422 | Required field absent / wrong type / out-of-enum |
| `invalid_letter` | 422 | Hallmark `letter` not in `{A,B,C,F}` |
| `invalid_fineness` | 422 | `fineness_per_mille` not in 0..1000 |
| `invalid_window` | 422 | `starts_at >= ends_at` |
| `invalid_mass` | 422 | `poured_mass_g <= 0` |
| `capacity_exceeded` | 422 | `poured_mass_g > crucible.capacity_g` |
| `crucible_overlap_existing` | 422 | A bulk-cast row overlaps an existing casting on the same crucible |
| `goldsmith_busy_existing` | 422 | A bulk-cast row overlaps an existing casting for the same goldsmith |
| `crucible_overlap_batch` | 422 | A bulk-cast row overlaps an earlier valid row in the same batch on the same crucible |
| `goldsmith_busy_batch` | 422 | A bulk-cast row overlaps an earlier valid row in the same batch for the same goldsmith |
| `invalid_filter` | 422 | `stage`, `intent_kind`, or `alloy_grade` not in whitelist |
| `invalid_goldsmith_id` | 422 | search param `goldsmith` is not an integer |
| `dup_in_batch` | 422 | Duplicate row identity inside `bulk-hallmark` or `bulk-cast` |
| `empty_batch` | 422 | `hallmarks` or `casts` missing or empty |
| `validation_failed` | 422 | One or more rows failed per-row validation (see `errors` array) |
| `not_implemented` | 501 | Placeholder response from an unfinished handler |

## Precedence

Every mutating endpoint enforces `404 > 409 > 422 > 400`. A request that
targets a missing resource AND has a malformed body returns `404`, not `422`.

Some routes have extra local ordering rules in `SPEC.md`. One easy case I kept
missing during wiring: `assign` reports a missing `:gid` before checking whether
the body is empty.
