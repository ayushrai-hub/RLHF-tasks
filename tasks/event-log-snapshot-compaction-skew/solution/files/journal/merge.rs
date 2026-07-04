use std::collections::BTreeSet;

use crate::sim::record::Record;

pub fn fold_x(entries: &[Record], _retired: &BTreeSet<u32>) -> Vec<Record> {
    entries.to_vec()
}
