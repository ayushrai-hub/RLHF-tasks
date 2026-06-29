# pact_f2 — remount matrix contract

## Command

`verify_k9 --matrix-full` runs `environment/scripts/drive_matrix.sh`, which invokes the kit driver and writes `/app/output/run_report.json`.

## run_report.json schema

`lane_records` reports one entry per lane profile after matrix replay.
`summary` reports matrix-wide aggregates including `terminal_digest`.
The `interim_trace_ids` field reports replay trace tokens formed as `t` plus each emitted slot id.
The summary `run_id` field reports the matrix profile name executed by the checker.

Row tuple fields before digest normalization: `slot_id` field is the row id; `parent_slot` field is the parent id; `attach_path` field is the mount point; `option_map` field is the normalized options object.

```json
{
  "schema_version": 1,
  "command": "verify_k9 --matrix-full",
  "lane_records": [
    {
      "lane_id": "lane_k1",
      "state_digest": "8 hex lowercase chars",
      "band_class": 1,
      "interim_trace_ids": ["t1", "t2"]
    }
  ],
  "summary": {
    "run_id": "matrix-full",
    "row_count": 3,
    "terminal_digest": "8 hex lowercase chars"
  }
}
```

## Digest emission ceiling

Matrix profiles use `digest_emit_ceiling = 3` from `meta/matrix_limits.toml`. Merged corpus rows with `slot_id` greater than the ceiling still participate in slot-carry reconciliation, but consumer emission must drop them before digest tuples are built. Summary `row_count` counts only emitted digest rows (3 for the standard matrix), not the wider fragment corpus.

## Band classes

Numeric `band_class` must be one of: 1 (private baseline), 2 (shared carry), 3 (slave fan-out).

Per-row band inside digest derivation: `shared` in normalized options → 2; `slave` in pre-strip options → 3; otherwise 1.

Lane-level `band_class` on each `lane_record` reports the highest severity band for that lane. When the lane unit fragment includes any slot option containing `slave`, the lane record must report `band_class = 3`, even though consumer emission strips `slave` from normalized option strings before digest tuples are built.

For `lane_k1`, emitted row `slot_id=2` uses band 2 inside digest tuples.
For `lane_k2`, the lane record must report `band_class=3` because `frag_u2.json` carries a slave slot.

## state_digest derivation

1. Sort emitted rows by `slot_id` ascending.
2. For each row build tuple:
   `{slot_id}|{parent_slot}|{attach_path}|{band_class}|{opt_digest}`
   where `opt_digest` is first 8 hex chars of `sha256(json_sorted_option_map)`.
3. Join with `\n` → `normalized`.
4. Read blk anchor bytes from `fixtures/blk/tc.mnt` offset 0 length 32 as lowercase hex → `blk_part`. **Digest anchor is always `tc.mnt`**, even when a lane profile names a different `blk_slice` for workdir scoring.
5. `state_digest = hashlib.sha256((normalized + "|" + blk_part).encode()).hexdigest()[:8]`

The `contract_hash` helper under `scripts/contract_hash.py` performs tuple normalization and digesting only for a JSON row list and blk anchor path; applying `digest_emit_ceiling` filtering before building those rows is the caller/pipeline's responsibility.

Held-out lanes `lane_k2`, `lane_k3`, and `lane_k4` must converge within ±0 of the `lane_k1` baseline digest after matrix replay. `lane_k2` carries a sparse fragment list but must still reconcile against the full table corpus before digest emission.

## Workdir scoring

Lane profiles may name `blk_slice` under `fixtures/blk/`. The driver passes that slice to `op_lane_h4` via `FVR_BLK_SLICE` for workdir-hash disambiguation. Independent of digest anchor in step 4. Consumer emission strips `slave` from option strings and normalizes bare `rw` to `rw,relatime` before digest tuples are built.

Partial unit excerpts under `fixtures/tails/tb_tail.txt` sample slot option hints when a profile unit json omits slots still present in the merged table view. The unit carry stage must reconcile sparse lane tables against the full fragment corpus so bind relocations converge.

## Recovery

`arena_seed` means the canonical recovery bytes at `fixtures/seed/arena_seed.bin`.
`fvr_anchor` means the scratch copy at `/tmp/fvr_anchor.bin` that must mirror `arena_seed` before matrix rerun.

After `ops/q9_clear.sh`, rerun:

```bash
cp fixtures/seed/arena_seed.bin /tmp/fvr_anchor.bin
verify_k9 --matrix-full
```

Duplicate recovery (`lane_k4`) runs the matrix twice; `state_digest` drift between passes must be 0.

## Held-out lane profiles

Profiles live under `profiles/`. Each may set:

- `blk_slice` — filename under `fixtures/blk/` for workdir-hash scoring (`lane_k3` uses `td.mnt`).
- `reorder_bind` (boolean) — `lane_k3` sets true for bind-move reorder normalization.
- `duplicate_recovery` (boolean) — `lane_k4` runs matrix twice; drift must be 0.

## False-green guard

Interim rows in `fixtures/q9/p9_stub.json` are diagnostic only. Stub `interim_rows` do not satisfy `state_digest` cross-checks against blk slices.

Placeholder digests such as `00000000` are rejected when the matrix reruns.
