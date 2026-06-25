use serde::Serialize;

#[derive(Serialize, Default, Clone, Debug, PartialEq)]
pub struct ProbeRow {
    pub verdict: String,
    pub epoch: u32,
    pub seq: u64,
    pub value: u64,
    pub flags: u32,
    pub digest: String,
    pub applied_count: u32,
    pub tombstone_count: u32,
}

#[derive(Serialize, Default, Clone, Debug)]
pub struct Paths {
    pub direct: ProbeRow,
    pub deferred: ProbeRow,
}

#[derive(Serialize, Default, Clone, Debug)]
pub struct LineSource {
    pub label: u32,
    pub ok: bool,
}

#[derive(Serialize, Default, Clone, Debug)]
pub struct CursorReport {
    pub paths: Paths,
    pub projection_complete: bool,
    pub epoch_barrier: bool,
    pub revision_tiebreak: bool,
    pub tombstone_suppression: bool,
    pub deferred_not_looser: bool,
    pub deferred_recheck: bool,
    pub worker_reuse_safe: bool,
    pub line_source: LineSource,
    pub restart_projection_parity: bool,
}

