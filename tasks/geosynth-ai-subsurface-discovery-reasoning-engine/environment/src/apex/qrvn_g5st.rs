use serde_json::Value;
use sha2::{Digest, Sha256};
use std::fs;

pub fn run() -> Result<(), String> {
    let epochs: Value =
        serde_json::from_str(&fs::read_to_string("/app/state/depth-epoch-ledger.json").unwrap())
            .map_err(|e| e.to_string())?;
    let catalog: Value =
        serde_json::from_str(&fs::read_to_string("/app/state/survey-ingest-catalog.json").unwrap())
            .map_err(|e| e.to_string())?;
    let guard: Value =
        serde_json::from_str(&fs::read_to_string("/app/state/hypothesis-guard-ledger.json").unwrap())
            .map_err(|e| e.to_string())?;

    let tr_by_id: std::collections::HashMap<String, f64> = catalog["traces"]
        .as_array()
        .unwrap_or(&vec![])
        .iter()
        .map(|t| {
            (
                t["sample_id"].as_str().unwrap().to_string(),
                t["prospect_index"].as_f64().unwrap_or(0.0),
            )
        })
        .collect();

    let mut margins: Vec<Value> = Vec::new();
    let mut lines: Vec<String> = Vec::new();
    for ep in epochs["epochs"].as_array().unwrap_or(&vec![]) {
        let block = ep["block_id"].as_str().unwrap_or("");
        let empty: Vec<Value> = Vec::new();
        let ids = ep["sample_ids"].as_array().unwrap_or(&empty);
        let prospects: Vec<f64> = ids
            .iter()
            .filter_map(|id| tr_by_id.get(id.as_str().unwrap_or("")).copied())
            .collect();
        let mean = if prospects.is_empty() {
            0.0
        } else {
            prospects.iter().sum::<f64>() / prospects.len() as f64
        };
        let margin = 1.0 - mean;
        margins.push(serde_json::json!({
            "block_id": block,
            "confidence_margin": margin,
        }));
        lines.push(format!("conf|{block}|{margin:.4}"));
    }
    lines.sort();
    let ledger_digest = format!("{:x}", Sha256::digest(lines.join("\n").as_bytes()));

    let ledger = serde_json::json!({
        "margins": margins,
        "margin_table_digest": ledger_digest,
        "bound_guard_digest": guard["guard_digest"],
        "confidence_source": "witness-margin",
    });
    fs::write(
        "/app/state/confidence-margin-ledger.json",
        serde_json::to_string_pretty(&ledger).unwrap() + "\n",
    )
    .map_err(|e| e.to_string())?;
    Ok(())
}
