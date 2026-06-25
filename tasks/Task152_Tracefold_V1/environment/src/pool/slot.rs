#[derive(Debug, Default)]
pub struct Slot {
    pub tag: u64,
    pub cache_epoch: u32,
    pub cache_seq: u64,
    pub cache_value: u64,
    pub cache_flags: u32,
    pub cache_digest: u64,
    pub cache_applied_count: u32,
    pub cache_tombstone_count: u32,
    pub run: u32,
    pub sched: u32,
    pub prior_run: u32,
}

