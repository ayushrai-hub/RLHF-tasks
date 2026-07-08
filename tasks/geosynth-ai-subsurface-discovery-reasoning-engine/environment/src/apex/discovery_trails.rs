use serde_json::Value;
use sha2::{Digest, Sha256};
use std::fs;

pub fn run() -> Result<(), String> {
    let staging: Value = serde_json::from_str(
        &fs::read_to_string("/app/state/formation-compose-staging.json").unwrap_or_else(|_| "{}".into()),
    )
    .unwrap_or(Value::Null);
    let ledger: Value =
        serde_json::from_str(&fs::read_to_string("/app/state/confidence-margin-ledger.json").unwrap())
            .map_err(|e| e.to_string())?;

    let hypotheses = staging["compose"].as_array().cloned().unwrap_or_default();
    let mut lines: Vec<String> = Vec::new();
    for wf in &hypotheses {
        let block = wf["block_id"].as_str().unwrap_or("");
        let empty_steps: Vec<Value> = Vec::new();
        for step in wf["steps"].as_array().unwrap_or(&empty_steps) {
            lines.push(format!(
                "chain|{block}|{}|{}",
                step["step"].as_u64().unwrap_or(0),
                step["sample_id"].as_str().unwrap_or("")
            ));
        }
    }
    lines.sort();
    let fingerprint = format!("{:x}", Sha256::digest(lines.join("\n").as_bytes()));

    let margins = ledger["margins"].as_array().cloned().unwrap_or_default();
    let report = serde_json::json!({
        "discovery_store": "geosynth-bundled",
        "discovery_fingerprint": fingerprint,
        "blocks": margins,
        "hypothesis_count": hypotheses.len(),
    });
    fs::create_dir_all("/app/output").map_err(|e| e.to_string())?;
    fs::write(
        "/app/output/geosynth-discovery-report.json",
        serde_json::to_string_pretty(&report).unwrap() + "\n",
    )
    .map_err(|e| e.to_string())?;
    Ok(())
}
