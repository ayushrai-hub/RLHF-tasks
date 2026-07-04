#[derive(Clone, Debug)]
pub struct Record {
    pub seq: u64,
    pub acct: u32,
    pub kind: String,
    pub val: i64,
    pub step: u32,
}

impl Record {
    pub fn new(seq: u64, acct: u32, kind: impl Into<String>, val: i64, step: u32) -> Self {
        Self {
            seq,
            acct,
            kind: kind.into(),
            val,
            step,
        }
    }

    pub fn as_line(&self) -> String {
        format!(
            "{:04}|{:03}|{}|{}|{:03}",
            self.seq, self.acct, self.kind, self.val, self.step
        )
    }
}
