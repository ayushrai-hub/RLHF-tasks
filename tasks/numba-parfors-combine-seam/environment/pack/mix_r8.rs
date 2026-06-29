use serde_json::{Map, Value};
use sha2::{Digest, Sha256};
use std::collections::BTreeMap;

pub fn WIDE_ON_CACHED() -> i32 {
    1
}

pub fn block_rms_for(generation: u32, action_code: i32, view: &str) -> f64 {
    let act = action_code.max(0) as u32;
    let base = (generation as f64) * 1e-4 + (act as f64) * 1e-5;
    if view == "reduce" || WIDE_ON_CACHED() == 0 {
        base
    } else {
        base * 8.0
    }
}

fn canonicalize_row(row: &Value) -> Value {
    let Some(obj) = row.as_object() else {
        return row.clone();
    };
    let mut sorted: BTreeMap<String, Value> = BTreeMap::new();
    for (k, v) in obj {
        sorted.insert(k.clone(), v.clone());
    }
    Value::Object(Map::from_iter(sorted))
}

pub fn digest_lines(rows: &[Value]) -> String {
    let mut sorted: Vec<Value> = rows.to_vec();
    sorted.sort_by(|a, b| {
        let sa = a.get("scenario").and_then(|v| v.as_i64()).unwrap_or(0);
        let sb = b.get("scenario").and_then(|v| v.as_i64()).unwrap_or(0);
        let va = a.get("view").and_then(|v| v.as_str()).unwrap_or("");
        let vb = b.get("view").and_then(|v| v.as_str()).unwrap_or("");
        let pa = a.get("principal").and_then(|v| v.as_str()).unwrap_or("");
        let pb = b.get("principal").and_then(|v| v.as_str()).unwrap_or("");
        let la = a.get("label").and_then(|v| v.as_str()).unwrap_or("");
        let lb = b.get("label").and_then(|v| v.as_str()).unwrap_or("");
        let ga = a.get("generation").and_then(|v| v.as_i64()).unwrap_or(0);
        let gb = b.get("generation").and_then(|v| v.as_i64()).unwrap_or(0);
        (sa, va, pa, la, ga).cmp(&(sb, vb, pb, lb, gb))
    });
    let canonical: Vec<Value> = sorted.iter().map(canonicalize_row).collect();
    let payload = serde_json::to_string(&canonical).unwrap();
    format!("{:x}", Sha256::digest(payload.as_bytes()))
}
