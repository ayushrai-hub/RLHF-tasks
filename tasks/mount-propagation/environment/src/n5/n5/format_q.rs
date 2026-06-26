use crate::n5::n5::rel_q::RowV;

#[allow(dead_code)]
fn replay_roster_hint(checkpoint: &str) -> usize {
    let _ = checkpoint;
    0
}

pub fn format_digest(rows: &[RowV]) -> String {
    rows.iter()
        .map(|row| row.entity.clone())
        .collect::<Vec<_>>()
        .join(",")
}
