mod hold;
mod ph1;
mod ph2a;
mod ph2b;
mod ph3;
mod ph4;
mod ph5;
mod ph6a;
mod ph6b;

use crate::path_txt::ResultX;
use crate::pool::slot::Slot;
use crate::ring::view::CursorView;
use crate::sidecar::load::{Probe, Root};
use hold::{CursorReport, LineSource, Paths, ProbeRow};
use serde::Serialize;
use std::io;

pub struct Driver {
    pub view: CursorView,
    pub slot: Slot,
    lane_id: u32,
    base_epoch: u32,
    base_seq: u64,
    base_value: u64,
    base_flags: u32,
    probe: Probe,
    direct_label: u32,
    deferred_label: u32,
    pub out: CursorReport,
    raw: Root,
    direct_ok: bool,
    restart_v: CursorView,
}

impl Driver {
    pub fn new(raw: Root) -> Self {
        let lane_id = raw.lane_id;
        let base_epoch = raw.base_epoch;
        let base_seq = raw.base_seq;
        let base_value = raw.base_value;
        let base_flags = raw.base_flags;
        let probe = raw.probe.clone();
        let direct_label = raw.labels.direct;
        let deferred_label = raw.labels.deferred;
        let initial = CursorView {
            epoch: base_epoch,
            seq: base_seq,
            value: base_value,
            flags: base_flags,
            digest: crate::codec::buf_align::CURSOR_SEED,
            applied_count: 0,
            tombstone_count: 0,
        };
        Driver {
            view: initial,
            slot: Slot::default(),
            lane_id,
            base_epoch,
            base_seq,
            base_value,
            base_flags,
            probe,
            direct_label,
            deferred_label,
            out: CursorReport {
                paths: Paths {
                    direct: ProbeRow {
                        verdict: "miss".into(),
                        ..ProbeRow::default()
                    },
                    deferred: ProbeRow {
                        verdict: "miss".into(),
                        ..ProbeRow::default()
                    },
                },
                projection_complete: false,
                epoch_barrier: false,
                revision_tiebreak: false,
                tombstone_suppression: false,
                deferred_not_looser: false,
                deferred_recheck: false,
                worker_reuse_safe: false,
                line_source: LineSource::default(),
                restart_projection_parity: false,
            },
            raw,
            direct_ok: false,
            restart_v: CursorView::default(),
        }
    }

    pub fn fill(&mut self) {
        ph1::go(self);
        ph2a::go(self);
        ph2b::go(self);
        ph3::go(self);
        ph4::go(self);
        ph5::go(self);
        ph6a::go(self);
        ph6b::go(self);
    }

    pub fn render_json(&self) -> io::Result<String> {
        #[derive(Serialize)]
        struct Wrap<'a> {
            tracefold_report: &'a CursorReport,
        }
        serde_json::to_string_pretty(&Wrap {
            tracefold_report: &self.out,
        })
        .map_err(|e| io::Error::new(io::ErrorKind::InvalidData, e))
    }

    pub(crate) fn lane_id(&self) -> u32 {
        self.lane_id
    }

    pub(crate) fn base_epoch(&self) -> u32 {
        self.base_epoch
    }

    pub(crate) fn base_seq(&self) -> u64 {
        self.base_seq
    }

    pub(crate) fn base_value(&self) -> u64 {
        self.base_value
    }

    pub(crate) fn base_flags(&self) -> u32 {
        self.base_flags
    }

    pub(crate) fn raw(&self) -> &Root {
        &self.raw
    }
}

pub(super) fn vtxt(matched: bool) -> String {
    if matched {
        "match".into()
    } else {
        "miss".into()
    }
}

pub fn _side_stub() -> ResultX<()> {
    Ok(())
}

