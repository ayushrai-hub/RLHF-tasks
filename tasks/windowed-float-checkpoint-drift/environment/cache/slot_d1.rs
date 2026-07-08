use crate::agg::WindowCtx;

pub fn slot_key_d1(win: &WindowCtx, wm: u64, epoch: u64, frame_gen: u64) -> u64 {
    let _ = wm;
    let _ = epoch;
    let _ = frame_gen;
    win.boundary_id
}

pub fn slot_preview(win: &WindowCtx) -> u64 {
    win.boundary_id ^ win.span_end
}
