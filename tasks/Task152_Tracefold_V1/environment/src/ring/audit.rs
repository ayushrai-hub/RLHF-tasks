use std::collections::BTreeMap;

use crate::codec::buf_align;
use crate::ring::coalesce;
use crate::ring::view::CursorView;
use crate::sidecar::load::Patch;
use crate::session::Driver;

pub fn reference_view(d: &Driver) -> CursorView {
    let active_epoch = d
        .raw()
        .patches
        .iter()
        .filter(|patch| {
            patch.committed
                && patch.lane_id == d.lane_id()
                && patch.epoch >= d.base_epoch()
                && patch.seq > d.base_seq()
        })
        .map(|patch| patch.epoch)
        .max()
        .unwrap_or(d.base_epoch());
    let mut selected: BTreeMap<u64, Patch> = BTreeMap::new();
    for patch in d.raw().patches.iter().filter(|patch| {
        patch.committed
            && patch.lane_id == d.lane_id()
            && patch.epoch == active_epoch
            && patch.seq > d.base_seq()
    }) {
        match selected.get(&patch.seq) {
            Some(current)
                if (patch.revision, patch.patch_id) <= (current.revision, current.patch_id) => {}
            _ => {
                selected.insert(patch.seq, patch.clone());
            }
        }
    }
    let mut view = CursorView {
        epoch: d.base_epoch(),
        seq: d.base_seq(),
        value: d.base_value(),
        flags: d.base_flags(),
        digest: buf_align::CURSOR_SEED,
        applied_count: 0,
        tombstone_count: 0,
    };
    for patch in selected.values() {
        coalesce::apply_winner(&mut view, patch);
    }
    view
}

