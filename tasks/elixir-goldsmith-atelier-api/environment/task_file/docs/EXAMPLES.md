# Worked examples

## Casting precedence walkthrough

A `POST /pieces/5/cast` (piece 5 is already `cast_complete`) returns
`409 wrong_stage`. A `POST /pieces/19/cast` succeeds:

```bash
curl -sS -X POST http://localhost:8080/pieces/19/cast \
  -H 'content-type: application/json' \
  -d '{"crucible_id": 1, "goldsmith_id": 7, "poured_mass_g": 30.0,
       "starts_at": "2026-02-10T08:00:00Z",
       "ends_at":   "2026-02-10T09:00:00Z"}'
```

→ `201 {"casting_id": 5, "piece_id": 19, "crucible_id": 1, "goldsmith_id": 7,
      "poured_mass_g": 30.0, "starts_at": "...", "ends_at": "..."}`.

Then a second cast for the same goldsmith overlapping the first:

```bash
curl -sS -X POST http://localhost:8080/pieces/11/cast \
  -H 'content-type: application/json' \
  -d '{"crucible_id": 2, "goldsmith_id": 7, "poured_mass_g": 15.0,
       "starts_at": "2026-02-10T08:30:00Z",
       "ends_at":   "2026-02-10T10:00:00Z"}'
```

Returns `409 wrong_stage` first (piece 11 is `ingot_selected`, not `cast_active`),
because the precedence is `404 piece_not_found > 409 already_released > 409 wrong_stage`.
The mass / overlap checks never even run.

## Bulk hallmark — duplicate beats invalid letter

```json
POST /pieces/bulk-hallmark
{"hallmarks": [
  {"piece_id": 13, "goldsmith_id": 1, "letter": "A"},
  {"piece_id": 13, "goldsmith_id": 1, "letter": "Q"}
]}
```

Both rows share `(piece_id=13, goldsmith_id=1)` → returns `422 dup_in_batch`,
detail mentions index 1. The second row's bad letter is NOT inspected.

## Bulk hallmark — collected per-row errors

```json
POST /pieces/bulk-hallmark
{"hallmarks": [
  {"piece_id": 13, "goldsmith_id": 1, "letter": "A"},
  {"piece_id": 9,  "goldsmith_id": 1, "letter": "B"},
  {"piece_id": 1,  "goldsmith_id": 1, "letter": "A"},
  {"piece_id": 14, "goldsmith_id": 1, "letter": "Q"}
]}
```

Index 1 → `already_released` (piece 9 is released).
Index 2 → `already_released` (piece 1 is released).
Index 3 → `invalid_letter`.

Return:

```json
{"error": "validation_failed",
 "detail": "see errors array",
 "errors": [
   {"index": 1, "code": "already_released", "detail": "..."},
   {"index": 2, "code": "already_released", "detail": "..."},
   {"index": 3, "code": "invalid_letter",   "detail": "..."}
 ]}
```

The `hallmarks` table is unchanged.

## Audit chain hash example

After a successful `POST /pieces/19/advance-stage`:

```
prev_hash  = "0"*64
action     = "advance_stage"
payload    = "19|cast_complete"
input      = prev_hash + "|" + action + "|" + payload
           = "00...00|advance_stage|19|cast_complete"
entry_hash = sha256_hex(input)
```

You can reproduce this in any Elixir shell:

```elixir
prev = String.duplicate("0", 64)
input = prev <> "|advance_stage|19|cast_complete"
:crypto.hash(:sha256, input) |> Base.encode16(case: :lower)
```
