// ingest heterogeneous survey lanes into a sorted trace catalog
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::HashMap;
use std::fs;
use std::path::PathBuf;

#[derive(Clone, Serialize, Deserialize)]
pub struct SurveyTrace {
    pub sample_id: String,
    pub source: String,
    pub block_id: String,
    pub recorded_at: String,
    pub seq: u32,
    pub formation_node: String,
    pub prospect_index: f64,
}

fn data_root() -> PathBuf {
    PathBuf::from("/app/data/surveys")
}

fn load_jsonl(dir: &str, file: &str) -> Vec<SurveyTrace> {
    let path = data_root().join(dir).join(file);
    let mut rows = Vec::new();
    for line in fs::read_to_string(path).unwrap_or_default().lines() {
        if line.trim().is_empty() {
            continue;
        }
        rows.push(serde_json::from_str(line).unwrap());
    }
    rows
}

pub fn load_all_traces() -> Vec<SurveyTrace> {
    let mut all = Vec::new();
    all.extend(load_jsonl("seismic", "traces.jsonl"));
    all.extend(load_jsonl("gravity", "anomalies.jsonl"));
    all.extend(load_jsonl("magnetic", "field.jsonl"));
    all.extend(load_jsonl("borehole", "logs.jsonl"));
    all.extend(load_jsonl("geochem", "samples.jsonl"));
    all.extend(load_jsonl("hyperspectral", "tiles.jsonl"));
    all.sort_by(|a, b| b.recorded_at.cmp(&a.recorded_at));
    all
}

pub fn catalog_digest(traces: &[SurveyTrace]) -> String {
    let mut lines: Vec<String> = traces
        .iter()
        .map(|t| {
            format!(
                "geo|{}|{}|{}|{}|{}|{}",
                t.sample_id,
                t.source,
                t.block_id,
                t.seq,
                t.recorded_at,
                t.formation_node
            )
        })
        .collect();
    lines.sort();
    let joined = lines.join("\n");
    use std::collections::hash_map::DefaultHasher;
    use std::hash::{Hash, Hasher};
    let mut hasher = DefaultHasher::new();
    joined.hash(&mut hasher);
    format!("{:016x}", hasher.finish())
}

pub fn write_seq_ledger(traces: &[SurveyTrace]) -> serde_json::Value {
    let mut by_block: HashMap<String, Vec<&SurveyTrace>> = HashMap::new();
    for tr in traces {
        by_block.entry(tr.block_id.clone()).or_default().push(tr);
    }
    let mut blocks: Vec<serde_json::Value> = Vec::new();
    let mut lines: Vec<String> = Vec::new();
    for token in by_block.keys() {
        let rows = by_block.get(token).unwrap();
        let max_seq = rows.iter().map(|t| t.seq).max().unwrap_or(0);
        let count = rows.len();
        blocks.push(serde_json::json!({
            "block_id": token,
            "max_seq": max_seq,
            "trace_count": count,
        }));
        lines.push(format!("seqbook|{token}|{max_seq}|{count}"));
    }
    lines.sort();
    blocks.sort_by(|a, b| a["block_id"].as_str().cmp(&b["block_id"].as_str()));
    let digest = format!("{:x}", Sha256::digest(lines.join("\n").as_bytes()));
    serde_json::json!({
        "blocks": blocks,
        "survey_seq_ledger_digest": digest,
    })
}

pub fn run() -> Result<(), String> {
    let traces = load_all_traces();
    let digest = catalog_digest(&traces);
    let ledger = write_seq_ledger(&traces);
    let catalog = serde_json::json!({
        "traces": traces,
        "catalog_digest": digest,
        "source": "survey-ingest-catalog",
    });
    fs::create_dir_all("/app/state").map_err(|e| e.to_string())?;
    fs::write(
        "/app/state/survey-ingest-catalog.json",
        serde_json::to_string_pretty(&catalog).unwrap() + "\n",
    )
    .map_err(|e| e.to_string())?;
    fs::write(
        "/app/state/survey-seq-ledger.json",
        serde_json::to_string_pretty(&ledger).unwrap() + "\n",
    )
    .map_err(|e| e.to_string())?;
    Ok(())
}
