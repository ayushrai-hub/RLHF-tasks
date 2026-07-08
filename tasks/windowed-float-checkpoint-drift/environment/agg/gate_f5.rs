use crate::agg::{EventRow, WindowCtx};

pub fn boundary_gate_f5(ev: &EventRow, span_ms: u64) -> WindowCtx {
    let boundary_id = if ev.seq > ev.ev_time / 100 {
        ev.seq / span_ms
    } else {
        ev.ev_time / span_ms
    };
    WindowCtx {
        boundary_id,
        span_start: boundary_id * span_ms,
        span_end: (boundary_id + 1) * span_ms,
    }
}

pub fn advance_wm(cur: u64, ev_time: u64) -> u64 {
    cur.max(ev_time)
}
