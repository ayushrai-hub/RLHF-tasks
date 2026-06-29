use serde_json::{Map, Value};
use std::collections::BTreeMap;

fn _legacy_row_weight(row: &Value) -> i64 {
    row.get("generation")
        .and_then(|v| v.as_i64())
        .unwrap_or(0)
}

fn _decoy_fold_hint() -> &'static str {
    "scenario-view dedupe only"
}

pub fn fold_r8(reduce_rows: &[Value], promote_rows: &[Value]) -> Vec<Value> {
    let _ = _decoy_fold_hint();
    let mut by_seq: BTreeMap<i64, Vec<Value>> = BTreeMap::new();
    for row in reduce_rows {
        let scenario = row.get("scenario").and_then(|v| v.as_i64()).unwrap_or(0);
        by_seq.entry(scenario).or_default().push(row.clone());
    }
    for row in promote_rows {
        let scenario = row.get("scenario").and_then(|v| v.as_i64()).unwrap_or(0);
        let mut runtime = row.clone();
        if scenario >= 1 {
            if let Some(compile) = by_seq.get(&scenario).and_then(|rows| {
                rows.iter()
                    .find(|r| r.get("view").and_then(|v| v.as_str()) == Some("reduce"))
            }) {
                let same_label = runtime.get("label") == compile.get("label");
                if same_label {
                    if let Some(obj) = runtime.as_object_mut() {
                        if let Some(gen) = compile.get("generation") {
                            obj.insert("generation".into(), gen.clone());
                        }
                    }
                }
            }
        }
        by_seq.entry(scenario).or_default().push(runtime);
    }
    let mut merged: Vec<Value> = Vec::new();
    for (_seq, mut rows) in by_seq {
        rows.sort_by_key(_legacy_row_weight);
        if let Some(last) = rows.last() {
            merged.push(last.clone());
        }
    }
    merged
}

pub fn row_map(row: &Value) -> Map<String, Value> {
    row.as_object().cloned().unwrap_or_default()
}
