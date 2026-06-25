use crate::gate::frame::ExecCtx;
use crate::pool::slot::Slot;
use crate::ring::view::CursorView;

#[derive(Clone, Debug, Default, serde::Serialize)]
pub struct LineOut {
    pub label: u32,
    pub epoch: u32,
    pub seq: u64,
    pub value: u64,
    pub flags: u32,
    pub digest: String,
    pub applied_count: u32,
    pub tombstone_count: u32,
}

pub fn p_evt(f: &ExecCtx, s: &Slot, v: &CursorView, out: &mut LineOut) {
    out.label = f.sched;
    out.epoch = f.epoch;
    out.seq = f.seq;
    out.value = f.value;
    out.flags = f.flags;
    out.digest = format!("{:016x}", f.digest);
    out.applied_count = f.applied_count;
    out.tombstone_count = f.tombstone_count;
    let _ = (s, v);
}

