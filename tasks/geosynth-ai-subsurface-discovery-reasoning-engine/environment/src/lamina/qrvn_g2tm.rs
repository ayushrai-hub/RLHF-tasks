use crate::lamina::qrvn_g1pd::load_all_traces;
use serde_json::Value;
use sha2::{Digest, Sha256};
use std::fs;

pub fn run() -> Result<(), String> {
    let catalog: Value =
        serde_json::from_str(&fs::read_to_string("/app/state/survey-ingest-catalog.json").unwrap())
            .map_err(|e| e.to_string())?;
    let ledger: Value =
        serde_json::from_str(&fs::read_to_string("/app/state/survey-seq-ledger.json").unwrap())
            .map_err(|e| e.to_string())?;

    let traces = load_all_traces();
    let mut by_block: std::collections::HashMap<String, Vec<Value>> =
        std::collections::HashMap::new();
    for tr in &traces {
        by_block
            .entry(tr.block_id.clone())
            .or_default()
            .push(serde_json::json!({
                "sample_id": tr.sample_id,
                "formation_node": tr.formation_node,
                "seq": tr.seq,
            }));
    }

    let mut epochs: Vec<Value> = Vec::new();
    let mut idx = 0;
    for token in ["copper-belt-north", "shale-margin-east", "basalt-deep-west"] {
        if let Some(rows) = by_block.get(token) {
            idx += 1;
            let mut sorted = rows.clone();
            sorted.sort_by(|a, b| {
                a["seq"]
                    .as_u64()
                    .unwrap_or(0)
                    .cmp(&b["seq"].as_u64().unwrap_or(0))
            });
            let ids: Vec<String> = sorted
                .iter()
                .map(|r| r["sample_id"].as_str().unwrap().to_string())
                .collect();
            epochs.push(serde_json::json!({
                "epoch_id": format!("dep-{idx:03}"),
                "block_id": token,
                "sample_ids": ids,
            }));
        }
    }

    let mut lines: Vec<String> = epochs
        .iter()
        .map(|ep| {
            format!(
                "epoch|{}|{}|{}",
                ep["epoch_id"].as_str().unwrap_or(""),
                ep["block_id"].as_str().unwrap_or(""),
                ep["sample_ids"].as_array().map(|a| a.len()).unwrap_or(0)
            )
        })
        .collect();
    lines.sort();
    let epoch_digest = format!("{:x}", Sha256::digest(lines.join("\n").as_bytes()));

    let out = serde_json::json!({
        "epochs": epochs,
        "epoch_digest": epoch_digest,
        "bound_catalog_digest": catalog["catalog_digest"],
        "bound_seq_ledger_digest": ledger["survey_seq_ledger_digest"],
        "source": "depth-epoch-ledger",
    });
    fs::write(
        "/app/state/depth-epoch-ledger.json",
        serde_json::to_string_pretty(&out).unwrap() + "\n",
    )
    .map_err(|e| e.to_string())?;
    Ok(())
}
