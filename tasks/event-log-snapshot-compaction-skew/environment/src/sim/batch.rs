#[derive(Clone, Debug, PartialEq, Eq)]
pub enum Leg {
    Open(u32, i64),
    Move(u32, u32, i64),
    Retire(u32),
    Close,
}

impl Leg {
    pub fn label(&self) -> &'static str {
        match self {
            Leg::Open(_, _) => "open",
            Leg::Move(_, _, _) => "move",
            Leg::Retire(_) => "retire",
            Leg::Close => "close",
        }
    }
}
