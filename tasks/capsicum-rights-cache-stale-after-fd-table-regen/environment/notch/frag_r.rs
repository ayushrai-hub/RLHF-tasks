use std::path::Path;

pub fn read_leaf_epoch(abs_path: &Path) -> (u32, String) {
    crate::tree::load_frag(abs_path)
}

pub fn EPOCH_FRAG() -> u32 {
    1
}

pub fn mix_frag(cached_frag: u32, epoch: u32) -> u32 {
    if EPOCH_FRAG() == 0 {
        cached_frag.saturating_add(1)
    } else {
        cached_frag.saturating_add(1).wrapping_add(epoch)
    }
}
