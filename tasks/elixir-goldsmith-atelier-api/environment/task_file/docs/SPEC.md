# Atelier API notes

These are the route notes I kept while wiring the unfinished atelier service.
They are not meant to be a public API guide, but the response shapes and error
codes here are the ones the service should follow.

## General rules

- All bodies are `application/json`. All responses are JSON.
- Timestamps are ISO-8601 UTC, second resolution: `YYYY-MM-DDTHH:MM:SSZ`.
- Lexical compare on these ISO strings is enough for chronological compare.
- IDs are 64-bit integers; the JSON wire form is a plain number.
- Error responses are exactly `{"error": "<machine_code>", "detail": "<string>"}` (plus the additional `errors` array for bulk-hallmark validation_failed).
- Success response schemas below are exact unless the endpoint explicitly says
  it may include additional fields.
- The error precedence on every mutating endpoint is `404 > 409 > 422 > 400`.
  If a request is BOTH malformed AND targets a missing resource, return `404`,
  not `422`.

## State machine

```
ingot_selected → assayed → cast_active → cast_complete → chased → hallmarked → released
```

- `released` is terminal. Any mutation on a released piece returns `409 already_released`.
- The transition `hallmarked → released` is driven by `POST /pieces/:id/release`,
  not by `advance-stage`. `advance-stage` returns `409 wrong_stage` if called
  on a `hallmarked` piece.

Transition preconditions, all raised as `409` when they fail:

| From → To | Precondition | Code |
|---|---|---|
| ingot_selected → assayed | ≥ 1 row in `assays` for the piece | `missing_assay` |
| assayed → cast_active | none | — |
| cast_active → cast_complete | most recent casting window has `ends_at ≤ now` | `wrong_stage` |
| cast_complete → chased | none | — |
| chased → hallmarked | ≥ 1 row in `hallmarks` for the piece | `missing_hallmark` |

## Workload composite grade

For `GET /goldsmiths/:id/workload`:

```
composite_grade = letter_base × specialty_factor × (1 + streak_bonus)
```

- `letter_base`: mean of the most recent hallmark letter for each ACTIVE piece
  assigned to the goldsmith. `A=4, B=3, C=2, F=0` (see `config/letter_values.json`).
- `specialty_factor`: mean of the per-piece specialty multiplier across the
  same set of active hallmarked pieces. `1.10` if `piece.intent_kind == goldsmith.specialty`
  else `1.00`.
- `streak_bonus`: `0.10` iff the goldsmith's last 3 hallmark rows
  (sorted by `recorded_at` desc, across ALL their pieces — active OR released)
  are all letter `A`. Otherwise `0.0`.
- Round the final composite to 4 decimal places.
- "Active" means `stage != 'released'`.
- If the goldsmith has no active hallmarked piece, return `null` for the composite.

## Cast booking (POST /pieces/:id/cast)

Body:

```json
{"crucible_id": 1, "goldsmith_id": 3, "poured_mass_g": 24.5,
 "starts_at": "2026-02-01T08:00:00Z", "ends_at": "2026-02-01T09:00:00Z"}
```

- Stage of `:id` must be `cast_active`.
- `starts_at < ends_at` strictly, otherwise `422 invalid_window`.
- `poured_mass_g > 0`, otherwise `422 invalid_mass`.
- `piece.alloy_grade` must be in `crucible.permitted_alloys` (a JSON array column on `crucibles`). Otherwise `422 alloy_grade_incompatible`.
- `poured_mass_g <= crucible.capacity_g`, otherwise `422 capacity_exceeded`.
- If `piece.alloy_grade == "24K"` then `goldsmith.rank` must be `master`, otherwise `422 rank_insufficient`.
- Half-open overlap on the crucible: `existing.starts_at < new.ends_at AND existing.ends_at > new.starts_at` → `409 crucible_overlap`.
- Half-open overlap on the goldsmith (across all crucibles): `409 goldsmith_busy`.
- Adjacent windows (`existing.ends_at == new.starts_at`) do NOT overlap.
- On success: `201` with `{casting_id, piece_id, crucible_id, goldsmith_id, poured_mass_g, starts_at, ends_at}`.
- Append an `audit_entries` row AFTER the underlying transaction commits.

For `cast`, use this failure order:

```
404 piece_not_found
409 already_released
409 wrong_stage              (stage != cast_active)
404 goldsmith_not_found
404 crucible_not_found
422 missing_field            (crucible_id / goldsmith_id / poured_mass_g / starts_at / ends_at)
422 invalid_window           (starts_at >= ends_at)
422 invalid_mass             (poured_mass_g <= 0)
422 alloy_grade_incompatible (piece.alloy_grade ∉ crucible.permitted_alloys)
422 capacity_exceeded        (poured_mass_g > crucible.capacity_g)
422 rank_insufficient        (24K piece + non-master goldsmith)
409 crucible_overlap
409 goldsmith_busy
```

## Bulk cast booking (POST /pieces/bulk-cast)

Body: `{"casts": [{piece_id, crucible_id, goldsmith_id, poured_mass_g, starts_at, ends_at}, ...]}`.

Validation order:

1. Body unparseable or top-level not an object → `422 invalid_body`.
2. `casts` missing or empty → `422 empty_batch`.
3. Duplicate `piece_id` within the batch → `422 dup_in_batch`. No rows are inserted. This check precedes all per-row validation, even if the duplicate row also has bad IDs, bad mass, or a bad window.
4. Per-row validation collects all row errors and returns `422 validation_failed` with `errors: [{index, code, detail}, ...]` sorted by input index. For one row, emit only the first applicable code in this order:

```
missing_field (piece_id)
piece_not_found
already_released
wrong_stage
missing_field (goldsmith_id)
goldsmith_not_found
missing_field (crucible_id)
crucible_not_found
missing_field (poured_mass_g / starts_at / ends_at)
invalid_window
invalid_mass
alloy_grade_incompatible
capacity_exceeded
rank_insufficient
crucible_overlap_existing
goldsmith_busy_existing
crucible_overlap_batch
goldsmith_busy_batch
```

Existing overlap checks compare against rows already in `castings`. Batch overlap checks compare against earlier valid rows in the same request only; a later row cannot make an earlier row invalid. Both use the same half-open interval rule as single cast booking. On any error path, leave the `castings` table unchanged and append no audit entry.

All rows clean → insert in array order, return `201` with `{count, casting_ids}` where IDs are in array order, and append one audit entry with `action = "bulk_cast"` and payload `<count>|<first_casting_id>|<last_casting_id>`.

## Provenance chain (GET /pieces/:id/provenance)

Walks `pieces.parent_id` starting at `:id`. Returns:

```json
{"chain": [{"piece_id": 10, "serial": "AA-0010", "intent_kind": "brooch", "alloy_grade": "22K"}, ...]}
```

- Cycle protection: maintain a MapSet of visited piece IDs; if a piece is
  encountered twice, STOP walking and return the partial chain (do NOT error).
- `404 piece_not_found` if `:id` is missing.

## DAG contribution (GET /pieces/:id/contribution)

A piece may be a recast composite of others via `piece_components(piece_id, source_piece_id, fraction)`.
Fractions per parent sum to `1.0`. A piece with zero component rows is a **root**.

Walk semantics:

- Start at the queried piece with weight `1.0`.
- Empty components → accumulate `result[pid] += weight`, stop this branch.
- Otherwise recurse into each `source_piece_id` with `weight × fraction`.
- **Path-visited (NOT global)** — copy the visited set on each recursive call.
  A piece reached via two independent paths contributes additively from both.
  A piece reached twice within the same path is skipped (cycle guard).
- `parent_id` is IGNORED here — it is only for `/provenance`.

Response (sort by `root_piece_id` asc, round each `contribution` to 6 decimals):

```json
{"piece_id": 12,
 "root_contributions": [
   {"root_piece_id": 1, "serial": "AA-0001", "intent_kind": "ring",   "contribution": 0.700000},
   {"root_piece_id": 4, "serial": "AA-0004", "intent_kind": "ring",   "contribution": 0.300000}
 ]}
```

Sum is `1.0 ± 1e-6` on well-formed seed.

## Mentor cohort (GET /goldsmiths/:id/cohort)

Walk the mentor tree in the mentee direction. Sort by
`(depth asc, goldsmith_id asc)`. Root is depth 0.

`released_pieces` per member = number of `pieces` rows with `stage = 'released'`
AND at least one `hallmarks` row by that member.

`cohort_total_released` = sum across all members.

Return this shape:

```json
{
  "root_goldsmith_id": 1,
  "members": [
    {"goldsmith_id": 1, "name": "albrecht", "released_pieces": 2}
  ],
  "cohort_total_released": 3
}
```

The member array key is `members`, not `cohort`.

## Trend (GET /pieces/:id/trend)

- Group assay rows by `YYYY-MM` of `performed_at`. Bucket value = MEAN `fineness_per_mille`.
- Sort buckets ascending by month.
- `n` = bucket count.
- If `n < 3` → `slope`, `r2`, `mk_z`, `ts_slope`, `direction` all `null`, buckets populated.
- Otherwise: compute the four statistics below, all rounded to 6 decimals.
- Least-squares slope:

  ```
  slope = sum((x_i - x_mean) * (y_i - y_mean)) / sum((x_i - x_mean)^2)
  ```

- `r2 = 1 - SS_res / SS_tot`; if `SS_tot == 0`, use `r2 = 1.0`.
- Mann-Kendall `S = sum(sign(y_j - y_i))` over all `j > i`.
- Tie-corrected variance:

  ```
  Var(S) = (n(n-1)(2n+5) - sum_g T_g(T_g-1)(2T_g+5)) / 18
  ```

  Only tied groups with `T_g >= 2` contribute to the subtraction.
- Continuity-corrected `mk_z`: `(S - 1) / sqrt(Var(S))` if `S > 0`,
  `(S + 1) / sqrt(Var(S))` if `S < 0`, and `0.0` if `S == 0`.
- Theil-Sen slope: median of every pairwise slope `(y_j - y_i) / (x_j - x_i)`
  for `j > i`; for an even count, average the two middle values.
- Combined-gate direction (labels: `refining` / `degrading` / `stable`):

  ```
  refining   iff slope ≥  0.5  AND r2 ≥ 0.5 AND mk_z ≥  1.96 AND ts_slope > 0
  degrading  iff slope ≤ −0.5  AND r2 ≥ 0.5 AND mk_z ≤ −1.96 AND ts_slope < 0
  stable     otherwise
  ```

Return this shape:

```json
{
  "piece_id": 7,
  "n_buckets": 5,
  "buckets": [{"month": "2025-10", "mean_fineness": 945.0}],
  "slope": 8.0,
  "r2": 0.984615,
  "mk_z": 2.204541,
  "ts_slope": 7.916667,
  "direction": "refining"
}
```

For `n_buckets < 3`, keep `piece_id`, `n_buckets`, and `buckets`, and return
`null` for `slope`, `r2`, `mk_z`, `ts_slope`, and `direction`.

## Bulk hallmark (POST /pieces/bulk-hallmark)

Body: `{"hallmarks": [{piece_id, goldsmith_id, letter, notes?}, ...]}`.

Validation order:

1. Body unparseable → `422 invalid_body`.
2. `hallmarks` missing or empty → `422 empty_batch`.
3. Duplicate `(piece_id, goldsmith_id)` pair within the batch → `422 dup_in_batch`. NO inserts. Detail includes the index of the first duplicate. **This precedes per-row validation** — a row that is both a duplicate AND has bad fields returns `dup_in_batch`.
4. Per-row validation, collecting ALL errors. Per-row precedence: `missing_field (piece_id)` > `piece_not_found` > `already_released` > `wrong_stage` > `missing_field (goldsmith_id)` > `goldsmith_not_found` > `invalid_letter`. If any errors collected, return `422 validation_failed`:

   ```json
   {"error": "validation_failed", "detail": "...", "errors": [{"index": 0, "code": "...", "detail": "..."}]}
   ```
5. All rows clean → INSERT in array order with shared `recorded_at = now()`. Return `201` with `{count, hallmark_ids, recorded_at}` (IDs in array order). Append ONE audit entry: `action = "bulk_hallmark"`.

On any error path, leave the `hallmarks` table unchanged.

## Audit chain (GET /audit, GET /audit/verify)

Appending endpoints: `advance-stage`, `cast`, `bulk-cast`, `hallmark`, `release`, `bulk-hallmark`. NOT appending: `assign`, `assay`, the two creation endpoints.

For each appended entry:

```
prev_hash = previous row's entry_hash, OR "0"*64 for the genesis row
entry_hash = lower_hex(sha256(utf8(prev_hash + "|" + action + "|" + payload)))
```

Payload formats (pipe-delimited):

| action | payload |
|---|---|
| `advance_stage` | `<piece_id>|<new_stage>` |
| `cast` | `<piece_id>|<casting_id>|<crucible_id>|<goldsmith_id>|<poured_mass_g formatted with 6 decimals>` |
| `bulk_cast` | `<count>|<first_casting_id>|<last_casting_id>` |
| `hallmark` | `<piece_id>|<hallmark_id>|<goldsmith_id>|<letter>` |
| `release` | `<piece_id>|<released_at>` |
| `bulk_hallmark` | `<count>|<first_hallmark_id>|<recorded_at>` |

`GET /audit?since=<seq>&limit=<n>`:

- Defaults: `since=0`, `limit=50`, max `limit=200`.
- Returns `{entries: [{seq, action, payload, prev_hash, entry_hash, occurred_at}, ...]}` sorted by `seq` asc.
- Filter `seq > since`.

`GET /audit/verify`:

- Re-walks the entire chain top-to-bottom recomputing `entry_hash`.
- Success: `{verified: true, entries_checked: N}`.
- First mismatch: `{verified: false, entries_checked: K, first_broken_seq: <seq>}`
  where `K` = number of entries inspected up to and including the broken one.

## Search (GET /pieces/search)

Query params (all optional, AND together):

- `stage` — must be one of the seven stages, else `422 invalid_filter`.
- `intent_kind` — `ring|chalice|reliquary|crown|brooch`, else `422 invalid_filter`.
- `alloy_grade` — `14K|18K|22K|24K`, else `422 invalid_filter`.
- `goldsmith` — integer; non-integer → `422 invalid_goldsmith_id`. A goldsmith id that does not exist is NOT an error; returns empty.

Result: `{pieces: [{piece_id, serial, intent_kind, alloy_grade, stage, assigned_goldsmith, parent_id}, ...]}` sorted by `piece_id` asc.

## Lineage grade (GET /pieces/:id/lineage-grade)

Walk `pieces.parent_id` starting at the queried piece's *parent* (the queried
piece itself is NOT counted). For each ancestor that has at least one row in
`hallmarks`, compute:

```
mean_letter_i = mean over all hallmarks on ancestor i of letter_value(letter)
weight_i      = 1 / 2^depth_i        (depth_i = 1 for direct parent, 2 for grandparent, ...)
```

Where `letter_value(letter)` uses `config/letter_values.json` (`A=4, B=3, C=2, F=0`).

```
lineage_grade = Σ_i (weight_i × mean_letter_i) / Σ_i (weight_i)
```

Sum only over ancestors with ≥ 1 hallmark — skip the ones without. If fewer
than 2 hallmarked ancestors are reachable, return `422 empty_lineage`.

Cycle protection: maintain a visited MapSet of piece IDs. When walking would
revisit an already-seen piece, stop. This makes the 17↔18 cyclic pair safe.

Sort the `ancestors` payload by ascending `depth`. Round `lineage_grade`,
`mean_letter`, and `weight` to 6 decimals each.

`404 piece_not_found` if `:id` is missing.

## Mass attribution (GET /pieces/:id/mass-attribution)

Like the DAG contribution walk but accumulates **grams** instead of fractions.
Start at the queried piece with `mass = piece.target_mass_g`. At each
`piece_components` edge, multiply the inbound mass by the edge fraction and
recurse. Roots (no component rows) collect grams.

```
walk(pid, mass, path, acc):
  if pid in path: return acc
  rows = SELECT source_piece_id, fraction FROM piece_components WHERE piece_id = pid
  if rows == []:
    acc[pid] += mass        # root accumulator
  else:
    for (src, frac) in rows:
      walk(src, mass * frac, path ∪ {pid}, acc)
```

Sort by ascending `root_piece_id`. Round each `attribution_g` to 6 decimals.
Sum of all `attribution_g` equals `target_mass_g ± 1e-4`.

Return this shape:

```json
{
  "piece_id": 12,
  "target_mass_g": 300.0,
  "root_attributions": [
    {"root_piece_id": 1, "serial": "AA-0001", "intent_kind": "ring", "attribution_g": 210.0},
    {"root_piece_id": 4, "serial": "AA-0004", "intent_kind": "ring", "attribution_g": 90.0}
  ]
}
```

The root list key is `root_attributions`, not `attributions` or
`mass_attributions`.

`404 piece_not_found` if `:id` is missing.

## Hallmark monotonic constraint

Every successful `POST /pieces/:id/hallmark` must satisfy:

```
new_recorded_at > max(existing.recorded_at WHERE goldsmith_id = :gid)
```

If the goldsmith has no prior hallmark, the check is vacuous. Otherwise a
violating call returns `409 ts_not_monotonic`. The body may include
`recorded_at` to specify the value (any ISO-8601 Zulu string); when absent,
the server uses `now()`. The check fires AFTER the `wrong_stage` guard and
BEFORE the `goldsmith_not_found` guard.

This constraint applies to single-hallmark `POST /pieces/:id/hallmark` only.
`POST /pieces/bulk-hallmark` writes every row with the SAME shared
`recorded_at = now()`, which is monotonic by construction (it is the current
time, strictly greater than any historical max).

## Reference endpoint contracts

### POST /goldsmiths
Body: `{name, rank, specialty, mentor_id?}`. `201` with `{goldsmith_id, name, rank, specialty, mentor_id, joined_at}`.

### POST /pieces
Body: `{serial, intent_kind, alloy_grade, target_mass_g, parent_id?}`. `201` with the persisted record.

### GET /pieces/:id
`200` with `{piece_id, serial, intent_kind, alloy_grade, target_mass_g, stage, assigned_goldsmith, parent_id, released_at}`.

### POST /goldsmiths/:gid/assign
Body: `{piece_id}`. On success, update `pieces.assigned_goldsmith` and return exactly `{goldsmith_id, piece_id}`.

Validation order is fixed: missing or non-integer `:gid` returns `404 goldsmith_not_found`; if the goldsmith exists, a missing, non-integer, or absent `piece_id` returns `422 missing_field`; a missing `piece_id` resource returns `404 piece_not_found`; a piece that already has `assigned_goldsmith` set returns `409 already_assigned`.

This endpoint does not append an audit entry.

### POST /pieces/:id/assay
Body: `{goldsmith_id, fineness_per_mille}`. `201` with `{assay_id, piece_id, goldsmith_id, fineness_per_mille, performed_at}`.

### POST /pieces/:id/hallmark
Body: `{goldsmith_id, letter, notes?, recorded_at?}`. `201` with `{hallmark_id, piece_id, goldsmith_id, letter, notes, recorded_at}`.

### GET /health
`200 {"status": "ok"}`.
