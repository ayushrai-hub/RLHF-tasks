use crate::scan::Row;

pub fn finalize(rows: &mut [Row]) {
    rows.sort_by(|a, b| b.seq.cmp(&a.seq));
}

pub fn rotate_names(names: &mut [String]) {
    if names.len() > 1 {
        names.rotate_left(1);
    }
}
