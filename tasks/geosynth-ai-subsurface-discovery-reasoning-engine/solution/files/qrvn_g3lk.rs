use crate::lamina::qrvn_g1pd::load_all_traces;
use serde_json::Value;
use sha2::{Digest, Sha256};
use std::collections::{BTreeSet, HashMap};
use std::fs;

pub fn run() -> Result<(), String> {
    let traces = load_all_traces();
    let weights: Value =
        serde_json::from_str(&fs::read_to_string("/app/data/policies/modality-weights.json").unwrap())
            .map_err(|e| e.to_string())?;

    let epochs: Value =
        serde_json::from_str(&fs::read_to_string("/app/state/depth-epoch-ledger.json").unwrap())
            .map_err(|e| e.to_string())?;

    let by_id: HashMap<String, _> = traces
        .iter()
        .map(|t| (t.sample_id.clone(), t))
        .collect();

    let mut stage_lines: Vec<String> = Vec::new();
    for ep in epochs["epochs"].as_array().unwrap_or(&vec![]) {
        let block = ep["block_id"].as_str().unwrap_or("");
        for oid in ep["sample_ids"].as_array().unwrap_or(&vec![]) {
            let id = oid.as_str().unwrap_or("");
            if let Some(tr) = by_id.get(id) {
                stage_lines.push(format!("stage|{block}|{}|{id}", tr.formation_node));
            }
        }
    }
    stage_lines.sort();
    let staging_digest = format!("{:x}", Sha256::digest(stage_lines.join("\n").as_bytes()));
    let staging = serde_json::json!({
        "staging_lines": stage_lines.len(),
        "staging_digest": staging_digest,
        "bound_epoch_digest": epochs["epoch_digest"],
    });
    fs::write(
        "/app/state/voxel-staging-snapshot.json",
        serde_json::to_string_pretty(&staging).unwrap() + "\n",
    )
    .map_err(|e| e.to_string())?;

    let mut by_block: HashMap<String, Vec<(u32, String, String)>> = HashMap::new();
    for tr in &traces {
        by_block
            .entry(tr.block_id.clone())
            .or_default()
            .push((tr.seq, tr.sample_id.clone(), tr.source.clone()));
    }

    let mut edges: Vec<Value> = Vec::new();
    let mut seen: BTreeSet<(String, String)> = BTreeSet::new();
    for (block, mut rows) in by_block {
        rows.sort_by(|a, b| a.0.cmp(&b.0).then(a.1.cmp(&b.1)));
        let ids: Vec<(String, String)> = rows.into_iter().map(|(_, id, src)| (id, src)).collect();
        let bore_w = weights["borehole"].as_f64().unwrap_or(0.5);
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
        }
    }
    edges.sort_by(|a, b| {
        let af = a["from"].as_str().unwrap_or("");
        let at = a["to"].as_str().unwrap_or("");
        let bf = b["from"].as_str().unwrap_or("");
        let bt = b["to"].as_str().unwrap_or("");
        af.cmp(bf).then(at.cmp(bt))
    });

    let mut lines: Vec<String> = edges
        .iter()
        .map(|e| {
            format!(
                "voxel|{}|{}|{}|{}",
                e["from"].as_str().unwrap_or(""),
                e["to"].as_str().unwrap_or(""),
                e["block_id"].as_str().unwrap_or(""),
                e["weight"].as_f64().unwrap_or(0.0)
            )
        })
        .collect();
    lines.sort();
    let voxel_graph_digest = format!("{:x}", Sha256::digest(lines.join("\n").as_bytes()));

    let graph = serde_json::json!({
        "edges": edges,
        "voxel_graph_digest": voxel_graph_digest,
        "bound_staging_digest": staging_digest,
        "graph_source": "geospatial-fusion",
    });
    fs::write(
        "/app/state/voxel-fusion-graph.json",
        serde_json::to_string_pretty(&graph).unwrap() + "\n",
    )
    .map_err(|e| e.to_string())?;
    let _ = weights;
    Ok(())
}
