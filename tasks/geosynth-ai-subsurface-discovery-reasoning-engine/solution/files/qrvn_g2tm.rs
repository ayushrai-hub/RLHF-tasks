use crate::lamina::qrvn_g1pd::{self, load_all_traces, SurveyTrace};
use serde_json::Value;
use sha2::{Digest, Sha256};
use std::fs;

fn epoch_digest(episodes: &[Value]) -> String {
    let mut lines: Vec<String> = episodes
        .iter()
        .map(|ep| {
            let id = ep["epoch_id"].as_str().unwrap_or("");
            let token = ep["block_id"].as_str().unwrap_or("");
            let count = ep["sample_ids"].as_array().map(|a| a.len()).unwrap_or(0);
            format!("epoch|{id}|{token}|{count}")
        })
        .collect();
    lines.sort();
    format!("{:x}", Sha256::digest(lines.join("\n").as_bytes()))
}

pub fn run() -> Result<(), String> {
    let observations = load_all_traces();
    let ledger_path = "/app/state/survey-seq-ledger.json";
    let ledger_file: Value = serde_json::from_str(&fs::read_to_string(ledger_path).map_err(|e| e.to_string())?)
        .map_err(|e| e.to_string())?;
    let recomputed = qrvn_g1pd::write_seq_ledger(&observations);
    if ledger_file["survey_seq_ledger_digest"] != recomputed["survey_seq_ledger_digest"] {
        return Err("survey seq ledger digest mismatch".into());
    }

    let mut episodes: Vec<Value> = Vec::new();
    let mut current_token = String::new();
    let mut bucket: Vec<&SurveyTrace> = Vec::new();
    let mut episode_idx = 0;

    let sorted_by_time: Vec<&SurveyTrace> = {
        let mut v: Vec<&SurveyTrace> = observations.iter().collect();
        v.sort_by(|a, b| {
            a.recorded_at
                .cmp(&b.recorded_at)
                .then(a.sample_id.cmp(&b.sample_id))
        });
        v
    };

    for obs in sorted_by_time {
        if bucket.is_empty() {
            current_token = obs.block_id.clone();
            bucket.push(obs);
            continue;
        }
        if obs.block_id != current_token {
            episode_idx += 1;
            episodes.push(serde_json::json!({
                "epoch_id": format!("dep-{episode_idx:03}"),
                "block_id": current_token,
                "sample_ids": bucket.iter().map(|o| &o.sample_id).collect::<Vec<_>>(),
            }));
            current_token = obs.block_id.clone();
            bucket = vec![obs];
        } else {
            bucket.push(obs);
        }
    }
    if !bucket.is_empty() {
        episode_idx += 1;
        episodes.push(serde_json::json!({
            "epoch_id": format!("dep-{episode_idx:03}"),
            "block_id": current_token,
            "sample_ids": bucket.iter().map(|o| &o.sample_id).collect::<Vec<_>>(),
        }));
    }

    let digest = epoch_digest(&episodes);
    let catalog_digest = fs::read_to_string("/app/state/survey-ingest-catalog.json")
        .ok()
        .and_then(|s| serde_json::from_str::<Value>(&s).ok())
        .and_then(|v| v["catalog_digest"].as_str().map(str::to_string))
        .unwrap_or_default();

    let out = serde_json::json!({
        "epochs": episodes,
        "epoch_digest": digest,
        "bound_catalog_digest": catalog_digest,
        "bound_seq_ledger_digest": recomputed["survey_seq_ledger_digest"],
        "source": "depth-epoch-ledger",
    });
    fs::write(
        "/app/state/depth-epoch-ledger.json",
        serde_json::to_string_pretty(&out).unwrap() + "\n",
    )
    .map_err(|e| e.to_string())?;
    Ok(())
}
