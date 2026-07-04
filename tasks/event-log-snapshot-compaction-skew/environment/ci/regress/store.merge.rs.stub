use std::collections::BTreeSet;

use crate::sim::record::Record;

pub fn fold_x(entries: &[Record], retired: &BTreeSet<u32>) -> Vec<Record> {
    let mut out = Vec::new();
    for record in entries {
        if retired.contains(&record.acct) && record.kind != "retire" {
            continue;
        }
        out.push(record.clone());
    }
    out.sort_by_key(|record| std::cmp::Reverse(record.seq));
    out
}
