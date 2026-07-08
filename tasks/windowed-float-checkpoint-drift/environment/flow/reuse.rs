use std::collections::HashMap;

use crate::agg::gate_f5::{advance_wm, boundary_gate_f5};
use crate::agg::{EventRow, LaneAcc, WindowCtx};
use crate::cache::slot_d1::slot_key_d1;
use crate::flow::ingest::ingest_event;

const SPAN_MS: u64 = 1000;

pub struct ReuseStore {
    map: HashMap<u64, LaneAcc>,
    wm: u64,
    epoch: u64,
    frame_gen: u64,
    drain_wm: u64,
}

impl ReuseStore {
    pub fn new(wm: u64) -> Self {
        Self {
            map: HashMap::new(),
            wm,
            epoch: 0,
            frame_gen: 0,
            drain_wm: 0,
        }
    }

    pub fn key_for(&self, win: &WindowCtx) -> u64 {
        slot_key_d1(win, self.wm, self.epoch, self.frame_gen)
    }

    pub fn bump_epoch(&mut self) {
        self.epoch = self.epoch.wrapping_add(1);
    }

    pub fn set_epoch(&mut self, epoch: u64) {
        self.epoch = epoch;
    }

    pub fn epoch(&self) -> u64 {
        self.epoch
    }

    pub fn set_frame_gen(&mut self, frame_gen: u64) {
        self.frame_gen = frame_gen;
    }

    pub fn frame_gen(&self) -> u64 {
        self.frame_gen
    }

    pub fn set_drain_wm(&mut self, drain_wm: u64) {
        self.drain_wm = drain_wm;
    }

    pub fn drain_wm(&self) -> u64 {
        self.drain_wm
    }

    pub fn get(&self, key: u64) -> Option<&LaneAcc> {
        self.map.get(&key)
    }

    pub fn put(&mut self, key: u64, acc: LaneAcc) {
        self.map.insert(key, acc);
    }

    pub fn advance(&mut self, ev_time: u64) {
        self.wm = advance_wm(self.wm, ev_time);
    }

    pub fn wm(&self) -> u64 {
        self.wm
    }

    pub fn entries(&self) -> Vec<(u64, LaneAcc)> {
        self.map.iter().map(|(k, v)| (*k, v.clone())).collect()
    }

    pub fn boundary_for(&self, ev_time: u64, span_ms: u64) -> WindowCtx {
        boundary_gate_f5(
            &crate::agg::EventRow {
                branch_id: String::new(),
                part_id: String::new(),
                seq: 0,
                ev_time,
                value: 0.0,
            },
            span_ms,
        )
    }
}

pub fn apply_cache_pass(
    store: &mut ReuseStore,
    events: &[EventRow],
) -> Result<(), crate::agg::AggErr> {
    for ev in events {
        store.advance(ev.ev_time);
        let win = boundary_gate_f5(ev, SPAN_MS);
        let key = store.key_for(&win);
        if let Some(cached) = store.get(key).cloned() {
            let mut acc = cached;
            ingest_event(&mut acc, ev)?;
            store.put(key, acc);
        } else {
            let mut acc = LaneAcc::default();
            ingest_event(&mut acc, ev)?;
            store.put(key, acc);
        }
    }
    Ok(())
}
