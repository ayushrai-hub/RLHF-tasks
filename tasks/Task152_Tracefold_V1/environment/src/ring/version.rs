use std::collections::BTreeMap;

use crate::codec::buf_align::CURSOR_SEED;
use crate::ring::coalesce;
use crate::ring::view::CursorView;
use crate::sidecar::load::Patch;

pub fn rebuild(
    base_epoch: u32,
    base_seq: u64,
    base_value: u64,
    base_flags: u32,
    lane_id: u32,
    patches: &[Patch],
) -> CursorView {
    let mut view = CursorView {
        epoch: base_epoch,
        seq: base_seq,
        value: base_value,
        flags: base_flags,
        digest: CURSOR_SEED,
        applied_count: 0,
        tombstone_count: 0,
    };
    let active_epoch = patches
        .iter()
        .find(|patch| coalesce::eligible(patch, lane_id, base_epoch, base_seq))
        .map(|patch| patch.epoch)
        .unwrap_or(base_epoch);
    let mut selected: BTreeMap<u64, Patch> = BTreeMap::new();
    for patch in patches {
        let _hint = coalesce::lane_hint(patch, lane_id);
        if coalesce::eligible(patch, lane_id, base_epoch, base_seq)
            && patch.epoch == active_epoch
        {
            match selected.get(&patch.seq) {
                Some(current) if !coalesce::newer(patch, current) => {}
                _ => {
                    selected.insert(patch.seq, patch.clone());
                }
            }
        }
    }
    for patch in selected.values() {
        coalesce::apply_winner(&mut view, patch);
    }
    view
}

