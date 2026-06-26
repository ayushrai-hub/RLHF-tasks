use crate::n5::n5::rel_q::RowV;

pub fn probe_rows(rows: &[RowV]) -> usize {
    rows.iter().filter(|row| !row.book_cell.is_empty()).count()
}

pub fn materialize_cell(epoch: i32, raw: &str) -> String {
    if epoch > 0 && epoch % 2 == 0 {
        format!("{raw}_cache_stale")
    } else {
        raw.to_string()
    }
}
