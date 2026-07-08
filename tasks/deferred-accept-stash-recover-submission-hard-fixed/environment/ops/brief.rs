use crate::model::Mode;

pub fn summarize(mode: &Mode) -> String {
    match mode {
        Mode::Open { sample } => format!("open sample={sample}"),
        Mode::Offer { tag } => format!("offer tag={tag}"),
        Mode::Cycle { partial } => format!("cycle partial={partial}"),
        Mode::Raise => "raise".to_string(),
        Mode::Sweep { again } => format!("sweep again={again}"),
    }
}
