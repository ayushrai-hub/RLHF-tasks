use std::collections::BTreeMap;

use serde_json::{Map, Value};

use crate::ingest::pipeline::MemoryRecord;

pub fn build_retrieval_index(records: &[MemoryRecord]) -> Value {
    let mut by_subject: BTreeMap<String, Vec<&MemoryRecord>> = BTreeMap::new();
    for rec in records {
        by_subject
            .entry(rec.subject.clone())
            .or_default()
            .push(rec);
    }

    let mut root = Map::new();
    for (subject, rows) in by_subject {
        let mut pred_map: BTreeMap<String, (u32, Vec<String>)> = BTreeMap::new();
        for rec in rows {
            let entry = pred_map
                .entry(rec.predicate.clone())
                .or_insert((rec.discovery_seq, Vec::new()));
            entry.0 = entry.0.min(rec.discovery_seq);
            entry.1.push(rec.memory_id.clone());
        }

        let mut ordered: Vec<(u32, String, Vec<String>)> = pred_map
            .into_iter()
            .map(|(pred, (min_seq, mut ids))| {
                ids.sort();
                (min_seq, pred, ids)
            })
            .collect();
        ordered.sort_by(|a, b| a.0.cmp(&b.0).then(a.1.cmp(&b.1)));

        let mut subject_map = Map::new();
        for (_seq, pred, ids) in ordered {
            subject_map.insert(pred, Value::Array(ids.into_iter().map(Value::String).collect()));
        }
        root.insert(subject, Value::Object(subject_map));
    }
    Value::Object(root)
}
