use serde::{Deserialize, Serialize};

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct EventRow {
    pub branch_id: String,
    pub part_id: String,
    pub seq: u64,
    pub ev_time: u64,
    pub value: f64,
}

#[derive(Clone, Debug, Default, Serialize, Deserialize)]
pub struct LaneAcc {
    pub count: u64,
    pub sum: f64,
    pub m2: f64,
    pub samples: Vec<f64>,
    pub tail_entries: Vec<crate::agg::pool_k8::TailEntry>,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct BranchAcc {
    pub branch_id: String,
    pub part_id: String,
    pub max_seq: u64,
    pub acc: LaneAcc,
}

impl BranchAcc {
    pub fn combine_rank(&self) -> u64 {
        let mut h: u64 = 0;
        for b in self.part_id.as_bytes() {
            h = h.wrapping_mul(131).wrapping_add(*b as u64);
        }
        h.wrapping_mul(1_000_000_000).wrapping_add(self.max_seq)
    }
}

#[derive(Clone, Debug, Default, Serialize, Deserialize)]
pub struct PartialFrame {
    pub seed: u64,
    pub processed: u64,
    pub wm: u64,
    pub frame_gen: u64,
    pub plan: Vec<String>,
    pub branches: Vec<BranchAcc>,
}

#[derive(Clone, Debug)]
pub struct WindowCtx {
    pub boundary_id: u64,
    pub span_start: u64,
    pub span_end: u64,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct MetricCell {
    pub value: f64,
    pub tol_class: String,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct BranchTotal {
    pub branch_id: String,
    pub total: f64,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct RunReport {
    pub seed: u64,
    pub profile: String,
    pub metrics: std::collections::BTreeMap<String, MetricCell>,
    pub global_total: f64,
    pub branch_totals: Vec<BranchTotal>,
    pub observed_merge_steps: u64,
    pub frame_gen: u64,
    pub plan_digest: String,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct TraceRow {
    pub step: u64,
    pub left_branch: String,
    pub right_branch: String,
    pub combine_rank: u64,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct MetricDelta {
    pub name: String,
    pub cold: f64,
    pub warm: f64,
    pub abs_delta: f64,
    pub rel_delta: f64,
    pub within_band: bool,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct DiffSummary {
    pub metric_deltas: Vec<MetricDelta>,
    pub ordering_violations: u64,
    pub max_combine_rank: u64,
    pub frame_gen: u64,
    pub seal_gen: u64,
    pub drain_wm: u64,
    pub plan_digest: String,
}

#[derive(Debug)]
pub enum AggErr {
    Io(String),
    Parse(String),
}

impl std::fmt::Display for AggErr {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            AggErr::Io(m) => write!(f, "io: {m}"),
            AggErr::Parse(m) => write!(f, "parse: {m}"),
        }
    }
}

impl std::error::Error for AggErr {}
