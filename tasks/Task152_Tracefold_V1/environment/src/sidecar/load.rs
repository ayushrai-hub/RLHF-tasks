use serde::Deserialize;

#[derive(Clone, Debug, Deserialize)]
pub struct Patch {
    pub epoch: u32,
    pub seq: u64,
    pub revision: u32,
    pub patch_id: u64,
    pub lane_id: u32,
    pub committed: bool,
    pub kind: String,
    pub delta: u64,
    pub toggle_mask: u32,
}

#[derive(Clone, Debug, Deserialize)]
pub struct Root {
    pub lane_id: u32,
    pub base_epoch: u32,
    pub base_seq: u64,
    pub base_value: u64,
    pub base_flags: u32,
    pub probe: Probe,
    pub labels: LabelMap,
    pub patches: Vec<Patch>,
}

#[derive(Clone, Debug, Deserialize)]
pub struct Probe {
    pub modulus: u64,
    pub remainder: u64,
    pub required_flags: u32,
    pub required_epoch: u32,
    pub min_applied: u32,
}

#[derive(Clone, Debug, Deserialize)]
pub struct LabelMap {
    pub direct: u32,
    pub deferred: u32,
}

