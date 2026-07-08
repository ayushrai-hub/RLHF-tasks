use serde::{Deserialize, Serialize};

pub const TAIL_CAP: usize = 12;

#[derive(Clone, Debug, Default, Serialize, Deserialize, PartialEq)]
pub struct TailEntry {
    pub ev_time: u64,
    pub seq: u64,
    pub value: f64,
}

pub fn insert_tail_k8(entries: &mut Vec<TailEntry>, ev_time: u64, seq: u64, value: f64) {
    entries.push(TailEntry {
        ev_time,
        seq,
        value,
    });
    entries.sort_by(|a, b| {
        a.ev_time
            .cmp(&b.ev_time)
            .then_with(|| a.seq.cmp(&b.seq))
    });
    if entries.len() > TAIL_CAP {
        let drop_n = entries.len() - TAIL_CAP;
        entries.drain(0..drop_n);
    }
}

pub fn fuse_pool_k8(left: Vec<TailEntry>, right: Vec<TailEntry>) -> Vec<TailEntry> {
    let mut out = left;
    out.extend(right);
    if out.len() > TAIL_CAP {
        out.truncate(TAIL_CAP);
    }
    out
}

pub fn quantile_from_pool(entries: &[TailEntry], q: f64) -> f64 {
    if entries.is_empty() {
        return 0.0;
    }
    let mut vals: Vec<f64> = entries.iter().map(|e| e.value).collect();
    vals.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
    let idx = ((vals.len() as f64 - 1.0) * q).round() as usize;
    vals[idx.min(vals.len() - 1)]
}

pub fn pool_byte_estimate(entries: &[TailEntry]) -> usize {
    entries.len() * 24
}
