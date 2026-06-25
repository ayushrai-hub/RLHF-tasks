/// Cursor reconstructed from the canonical patch winners.
#[derive(Clone, Debug, Default, PartialEq)]
pub struct CursorView {
    pub epoch: u32,
    pub seq: u64,
    pub value: u64,
    pub flags: u32,
    pub digest: u64,
    pub applied_count: u32,
    pub tombstone_count: u32,
}

