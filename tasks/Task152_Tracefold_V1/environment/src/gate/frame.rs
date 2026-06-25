#[derive(Clone, Debug, Default)]
pub struct ExecCtx {
    pub epoch: u32,
    pub seq: u64,
    pub value: u64,
    pub flags: u32,
    pub digest: u64,
    pub applied_count: u32,
    pub tombstone_count: u32,
    pub run: u32,
    pub sched: u32,
}

