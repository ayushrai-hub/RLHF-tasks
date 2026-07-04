#[derive(Clone, Debug, PartialEq)]
pub struct StagingMove {
    pub from: u32,
    pub to: u32,
    pub amt: i64,
}
