# Tracefold report contract

The trace fold cursor binary reads `TRACEFOLD_SEED` and writes a JSON object containing `tracefold_report` to `TRACEFOLD_OUT`.

## Canonical projection

Filter committed patches for the requested lane with `epoch >= base_epoch` and `seq > base_seq`. The active epoch is the maximum epoch among those eligible patches, or `base_epoch` when none exist. Only active-epoch patches continue.

For each sequence, choose the greatest `(revision, patch_id)` tuple. Apply winners by ascending sequence.

Start with the supplied base epoch, sequence, value, and flags; digest starts at `CURSOR_SEED`; both counts start at zero.

Every winner sets cursor epoch and sequence to the winner and contributes to the digest lineage.

For `update`, apply the delta to the value and the toggle mask to the flags using the exact codec rules in this document, then increment `applied_count`.

For `tombstone`, do not apply `delta` or `toggle_mask`; increment `tombstone_count`. Tombstone patches still contribute to the digest lineage with the tombstone tag. Tombstone digest folds use zero delta and zero toggle mask.


## Codec arithmetic

Constants CURSOR_SEED and TOMBSTONE_TAG for this task are fixed in the stock seed.

Applying an update delta to the value: value := value + rotate_left_u64(delta, (revision mod 31) + 1) using wrapping 64-bit addition. The rotation amount is (revision mod 31) + 1 (range 1..=31, never zero).

Applying an update toggle mask to the flags: flags := flags XOR rotate_left_u32(toggle_mask, seq mod 32). The rotation amount is seq mod 32 (range 0..=31).

Digest fold for every winner (tombstone uses zero delta and zero toggle mask in the fold call):

cursor_fold(acc, seq, revision, delta, toggle_mask) = rotate_left_u64(t, 17) then wrapping_mul 0x9e3779b185ebca87, where

t = acc XOR rotate_left_u64(seq, (revision mod 32) + 1) XOR rotate_right_u64(delta, seq mod 32) XOR rotate_left_u64(u64(toggle_mask), 23).

The seq term rotates by (revision mod 32) + 1 (range 1..=32, never zero). The toggle-mask term rotates by exactly 23.

cursor_fold_winner(...) first sets acc := acc XOR rotate_left_u64(patch_id, 11) XOR (tombstone ? TOMBSTONE_TAG : 0), then returns cursor_fold of that.

## Rows and probe

Direct and deferred rows contain:

- `verdict`
- `epoch`
- `seq`
- `value`
- `flags`
- `digest`
- `applied_count`
- `tombstone_count`

The probe matches only when the frame equals the complete live cursor, its epoch equals `required_epoch`, its applied count is at least `min_applied`, and `probe_matches` succeeds.

The parked trace worker must refresh every cursor field at execution time. The deferred path uses the same predicate as direct evaluation.
## Delivered audit digests

The report includes top-level `lineage_digest` and `discard_digest` strings next to `paths` and the boolean invariants.

`lineage_digest` summarizes every raw delivered patch in exact input order. `discard_digest` summarizes only raw delivered patches that are not selected as canonical winners after applying lane, commit, base-boundary, active-epoch, and `(revision, patch_id)` winner rules. Losing revisions for a selected sequence are discards.

Both digests initialize acc as:

DIGEST_SEED XOR rotate_left_u64(lane_id, 3) XOR rotate_left_u64(base_epoch, 9) XOR rotate_left_u64(base_seq, 17) XOR rotate_right_u64(base_value, 11) XOR rotate_left_u64(base_flags, 29).

For each included patch at zero-based original input index i, compute:

mixed = acc XOR rotate_left_u64(i + 1, 5) XOR rotate_left_u64(epoch, 7) XOR rotate_left_u64(seq, 13) XOR rotate_left_u64(revision, 19) XOR rotate_left_u64(patch_id, 31) XOR rotate_left_u64(patch.lane_id, 37) XOR rotate_right_u64(delta, seq mod 32) XOR rotate_left_u64(toggle_mask, revision mod 32) XOR (committed ? COMMITTED_TAG : REJECTED_TAG) XOR (kind == tombstone ? TOMBSTONE_AUDIT_TAG : UPDATE_AUDIT_TAG).

Then set acc := rotate_left_u64(mixed, 23) * 0x9e3779b97f4a7c15 using wrapping 64-bit multiplication. Emit each digest as sixteen lowercase hexadecimal digits.

Lineage constants: DIGEST_SEED = 0x3AC436F52B5D874C, COMMITTED_TAG = 0xBB589C9EE109634B, REJECTED_TAG = 0x6D06EEF0001D4E1D, TOMBSTONE_AUDIT_TAG = 0x4E4BA86B24A11805, and UPDATE_AUDIT_TAG = 0x59F45A2C5FBE7459.

Discard constants: DIGEST_SEED = 0x350E77B783BDBB19, COMMITTED_TAG = 0x79807B231990101E, REJECTED_TAG = 0x753ED9C978EF5FBE, TOMBSTONE_AUDIT_TAG = 0x1A0C4EEA92D866DD, and UPDATE_AUDIT_TAG = 0x1BF18C857F45647A.

Sorting, filtering, reversing, or deduplicating before these folds is incorrect unless the contract explicitly says the patch is excluded from discard_digest because it is a canonical winner.
## Invariants

- `projection_complete`: complete cursor equals the canonical reducer.
- `epoch_barrier`: only the highest eligible lane epoch contributes.
- `revision_tiebreak`: same-revision ties use greatest patch ID.
- `tombstone_suppression`: tombstone payload is not applied and counts are correct.
- `deferred_not_looser`: deferred cannot match when direct misses.
- `deferred_recheck`: both rows and verdicts are identical.
- `worker_reuse_safe`: recycled trace worker uses the new job label.
- `line_source.label`: equals `labels.deferred`.
- `line_source.ok`: true when the deferred execution line label equals both the executing worker run and `labels.deferred`.
- `restart_projection_parity`: reverse delivery from the original base converges identically.
