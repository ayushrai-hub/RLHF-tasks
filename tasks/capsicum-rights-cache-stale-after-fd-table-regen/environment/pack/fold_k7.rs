use serde_json::{Map, Value};

pub fn fold_k(mint_rows: &[Value], live_rows: &[Value]) -> Vec<Value> {
    let mut out: Vec<Value> = Vec::new();
    let mut by_key: std::collections::BTreeMap<(i64, String), Value> =
        std::collections::BTreeMap::new();
    let allowed = ["spool", "live", "drift"];
    for row in mint_rows.iter().chain(live_rows.iter()) {
        let view = row.get("view").and_then(|v| v.as_str()).unwrap_or("");
        if !allowed.contains(&view) {
            continue;
        }
        let scenario = row.get("scenario").and_then(|v| v.as_i64()).unwrap_or(0);
        by_key.insert((scenario, view.to_string()), row.clone());
    }
    for (_key, row) in by_key {
        let required = ["scenario", "view", "principal", "label", "generation", "action_code"];
        if required.iter().all(|f| row.get(*f).is_some()) {
            out.push(row);
        }
    }
    out
}

pub fn row_map(row: &Value) -> Map<String, Value> {
    row.as_object().cloned().unwrap_or_default()
}
