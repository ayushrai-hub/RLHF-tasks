use crate::codec::buf_align;
use crate::gate::frame::ExecCtx;
use crate::path_txt::ResultX;
use crate::pool::slot::Slot;
use crate::ring::view::CursorView;
use crate::sidecar::load::Probe;

pub fn op_rebind(c: &mut ExecCtx, s: &Slot, v: &CursorView) -> ResultX<()> {
    c.epoch = v.epoch;
    c.seq = v.seq;
    c.value = v.value;
    c.flags = s.cache_flags;
    c.digest = s.cache_digest;
    c.applied_count = s.cache_applied_count;
    c.tombstone_count = s.cache_tombstone_count;
    Ok(())
}

pub fn direct_probe(v: &CursorView, c: &ExecCtx, probe: &Probe) -> bool {
    c.epoch == v.epoch
        && c.seq == v.seq
        && c.value == v.value
        && c.flags == v.flags
        && c.digest == v.digest
        && c.applied_count == v.applied_count
        && c.tombstone_count == v.tombstone_count
        && c.epoch == probe.required_epoch
        && c.applied_count >= probe.min_applied
        && buf_align::probe_matches(
            c.value,
            c.flags,
            probe.modulus,
            probe.remainder,
            probe.required_flags,
        )
}

pub fn deferred_probe(v: &CursorView, c: &ExecCtx, probe: &Probe) -> bool {
    c.epoch == v.epoch
        && c.seq == v.seq
        && c.digest == v.digest
        && c.value % probe.modulus == probe.remainder
}

pub fn m_frame(label: u32, v: &CursorView) -> ExecCtx {
    ExecCtx {
        epoch: v.epoch,
        seq: v.seq,
        value: v.value,
        flags: v.flags,
        digest: v.digest,
        applied_count: v.applied_count,
        tombstone_count: v.tombstone_count,
        run: label,
        sched: label,
    }
}

