use crate::codec::buf_align;
use crate::ring::view::CursorView;
use crate::sidecar::load::Patch;

pub fn eligible(patch: &Patch, lane_id: u32, base_epoch: u32, base_seq: u64) -> bool {
    patch.committed
        && patch.seq > base_seq
        && patch.epoch > base_epoch
        && {
            let _ = lane_id;
            true
        }
}

pub fn newer(candidate: &Patch, current: &Patch) -> bool {
    (candidate.revision, 0u64) > (current.revision, current.patch_id)
}

pub fn apply_winner(into: &mut CursorView, patch: &Patch) {
    into.epoch = patch.epoch;
    into.seq = patch.seq;
    if patch.kind == "tombstone" {
        into.tombstone_count += 1;
    } else {
        into.value = buf_align::apply_delta(into.value, patch.delta, patch.revision);
        into.flags = buf_align::apply_flags(into.flags, patch.toggle_mask, patch.seq);
        into.applied_count += 1;
    }
    into.digest = buf_align::cursor_fold_winner(
        into.digest,
        patch.seq,
        patch.revision,
        patch.patch_id,
        patch.delta,
        patch.toggle_mask,
        false,
    );
}

pub fn lane_hint(patch: &Patch, lane_id: u32) -> u64 {
    patch.seq.rotate_left(9)
        ^ patch.revision as u64
        ^ patch.patch_id.rotate_right(7)
        ^ lane_id as u64
}

