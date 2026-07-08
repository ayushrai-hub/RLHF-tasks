#!/usr/bin/env bash
set -euo pipefail
export PATH="/usr/local/cargo/bin:/app/bin:${PATH}"
export PYTHONPATH=/app
python3 <<'PY'
from pathlib import Path

def _replace(path: Path, old: str, new: str) -> None:
    text = path.read_text()
    if old not in text:
        raise SystemExit(f"missing patch anchor in {path}: {old[:60]!r}")
    path.write_text(text.replace(old, new, 1))

DEPTH_EPOCH = r'''use crate::lamina::qrvn_g1pd::{self, load_all_traces, SurveyTrace};
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
'''

Path("/app/src/lamina/qrvn_g2tm.rs").write_text(DEPTH_EPOCH)

ingest_path = Path("/app/src/lamina/qrvn_g1pd.rs")
ingest_text = ingest_path.read_text()
ingest_text = ingest_text.replace(
    "all.sort_by(|a, b| b.recorded_at.cmp(&a.recorded_at));",
    "all.sort_by(|a, b| a.sample_id.cmp(&b.sample_id));",
    1,
)
ingest_text = ingest_text.replace(
    """    use std::collections::hash_map::DefaultHasher;
    use std::hash::{Hash, Hasher};
    let mut hasher = DefaultHasher::new();
    joined.hash(&mut hasher);
    format!("{:016x}", hasher.finish())""",
    '    format!("{:x}", Sha256::digest(joined.as_bytes()))',
    1,
)
Path("/app/src/lamina/qrvn_g1pd.rs").write_text(ingest_text)

ingest_text = Path("/app/src/lamina/qrvn_g1pd.rs").read_text()
ingest_text = ingest_text.replace(
    """            format!(
                "geo|{}|{}|{}|{}|{}|{}",
                t.sample_id,
                t.source,
                t.block_id,
                t.seq,
                t.recorded_at,
                t.formation_node
            )""",
    """            format!(
                "geo|{}|survey-ingest-catalog|{}|{}|{}|{}",
                t.sample_id,
                t.block_id,
                t.seq,
                t.recorded_at,
                t.formation_node
            )""",
    1,
)
Path("/app/src/lamina/qrvn_g1pd.rs").write_text(ingest_text)

fuse_text = Path("/app/src/weft/qrvn_g3lk.rs").read_text().replace(
    """        for i in 0..ids.len().saturating_sub(1) {
            let j = i + 1;
            let key = (ids[i].0.clone(), ids[j].0.clone());
            if !seen.insert(key.clone()) {
                continue;
            }
            let w = 1.0;
            edges.push(serde_json::json!({
                "from": ids[i].0,
                "to": ids[j].0,
                "block_id": block,
                "weight": w,
                "forward_span": j - i,
            }));
        }""",
    """        let bore_w = weights["borehole"].as_f64().unwrap_or(0.5);
        let seis_w = weights["seismic"].as_f64().unwrap_or(0.5);
        let grav_w = weights["gravity"].as_f64().unwrap_or(0.5);
        let mag_w = weights["magnetic"].as_f64().unwrap_or(0.5);
        for i in 0..ids.len() {
            for j in (i + 1)..ids.len() {
                let key = (ids[i].0.clone(), ids[j].0.clone());
                if !seen.insert(key.clone()) {
                    continue;
                }
                let w = if ids[i].1 == "borehole" || ids[j].1 == "borehole" {
                    bore_w
                } else if ids[i].1 == "seismic" || ids[j].1 == "seismic" {
                    seis_w
                } else if ids[i].1 == "gravity" || ids[j].1 == "gravity" {
                    grav_w
                } else {
                    mag_w
                };
                edges.push(serde_json::json!({
                    "from": ids[i].0,
                    "to": ids[j].0,
                    "block_id": block,
                    "weight": w,
                    "forward_span": j - i,
                }));
            }
        }""",
    1,
)
Path("/app/src/weft/qrvn_g3lk.rs").write_text(fuse_text)

guard_text = Path("/app/src/weft/qrvn_g4gd.rs").read_text()
guard_text = guard_text.replace(
    """            let mut is_blocked = false;
            let _ = &blocks;
            if !is_blocked {""",
    """            let mut is_blocked = false;
            for block in &blocks {
                let bl = block["left"].as_str().unwrap_or("");
                let br = block["right"].as_str().unwrap_or("");
                if (left == bl && right == br) || (left == br && right == bl) {
                    blocked.push(block.clone());
                    is_blocked = true;
                    break;
                }
            }
            if !is_blocked {""",
    1,
)
Path("/app/src/weft/qrvn_g4gd.rs").write_text(guard_text)

score_path = Path("/app/src/apex/qrvn_g5st.rs")
score_text = score_path.read_text()
if "confidence_floor" not in score_text:
    score_text = score_text.replace(
        "pub fn run() -> Result<(), String> {",
        """pub fn run() -> Result<(), String> {
    let policy: serde_json::Value = serde_json::from_str(
        &std::fs::read_to_string("/app/data/policies/formation-governance.json").unwrap(),
    )
    .map_err(|e| e.to_string())?;
    let floor = policy["confidence_floor"].as_f64().unwrap_or(0.0);""",
        1,
    )
    score_text = score_text.replace("let margin = 1.0 - mean;", "let margin = (1.0 - mean).max(floor);", 1)
Path("/app/src/apex/qrvn_g5st.rs").write_text(score_text)

branch_path = Path("/app/geokit/qrvn_f7br/splitter.py")
branch_text = branch_path.read_text().replace(
    'for block in reversed(policy["hypothesis_priority"]):',
    'for block in policy["hypothesis_priority"]:',
    1,
)
branch_path.write_text(branch_text)
PY
bash /app/scripts/rebuild-geosynth-engine.sh
test -x /app/bin/geosynth
/app/bin/geosynth discovery-run
