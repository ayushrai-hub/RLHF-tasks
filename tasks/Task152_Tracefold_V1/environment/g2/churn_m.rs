use crate::gate::dispatch;
use crate::gate::frame::ExecCtx;
use crate::path_txt::ResultX;
use crate::pool::slot::Slot;
use crate::ring::view::CursorView;
use crate::sidecar::load::Probe;
use crate::trace::voice_m::{p_evt, LineOut};

pub fn k_pull(s: &mut Slot, view: &CursorView, tag: u64, label: u32) -> ResultX<()> {
    let is_new = s.tag != tag;
    s.tag = tag;
    if is_new {
        s.cache_epoch = view.epoch;
        s.cache_seq = view.seq;
        s.cache_value = view.value;
        s.cache_flags = view.flags;
        s.cache_digest = view.digest;
        s.cache_applied_count = view.applied_count;
        s.cache_tombstone_count = view.tombstone_count;
        s.run = s.prior_run;
    } else {
        s.run = label;
    }
    s.sched = label;
    s.prior_run = label;
    Ok(())
}

pub fn n_exec(s: &mut Slot, v: &CursorView, probe: &Probe) -> (bool, LineOut) {
    let mut c = ExecCtx {
        epoch: s.cache_epoch,
        seq: s.cache_seq,
        value: s.cache_value,
        flags: s.cache_flags,
        digest: s.cache_digest,
        applied_count: s.cache_applied_count,
        tombstone_count: s.cache_tombstone_count,
        run: s.run,
        sched: s.sched,
    };
    let _ = dispatch::op_rebind(&mut c, s, v);
    let matched = dispatch::deferred_probe(v, &c, probe);
    let mut out = LineOut::default();
    p_evt(&c, s, v, &mut out);
    (matched, out)
}

