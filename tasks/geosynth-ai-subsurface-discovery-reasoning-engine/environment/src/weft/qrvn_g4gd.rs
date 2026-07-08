use serde_json::Value;
use sha2::{Digest, Sha256};
use std::fs;

fn guard_digest(accepted: &[Value], blocked: &[Value]) -> String {
    let mut lines: Vec<String> = Vec::new();
    for row in accepted {
        lines.push(format!(
            "accept|{}|{}",
            row["left"].as_str().unwrap_or(""),
            row["right"].as_str().unwrap_or("")
        ));
    }
    for row in blocked {
        lines.push(format!(
            "block|{}|{}|{}",
            row["left"].as_str().unwrap_or(""),
            row["right"].as_str().unwrap_or(""),
            row["reason"].as_str().unwrap_or("")
        ));
    }
    lines.sort();
    format!("{:x}", Sha256::digest(lines.join("\n").as_bytes()))
}

pub fn run() -> Result<(), String> {
    let policy: Value = serde_json::from_str(
        &fs::read_to_string("/app/data/policies/formation-governance.json").unwrap(),
    )
    .map_err(|e| e.to_string())?;
    let graph: Value =
        serde_json::from_str(&fs::read_to_string("/app/state/voxel-fusion-graph.json").unwrap())
            .map_err(|e| e.to_string())?;

    let blocks = policy["block_guard_pairs"]
        .as_array()
        .cloned()
        .unwrap_or_default();
    let mut blocked: Vec<Value> = Vec::new();
    let mut accepted: Vec<Value> = Vec::new();

    let epochs: Value =
        serde_json::from_str(&fs::read_to_string("/app/state/depth-epoch-ledger.json").unwrap())
            .map_err(|e| e.to_string())?;
    let block_ids: Vec<String> = epochs["epochs"]
        .as_array()
        .unwrap_or(&vec![])
        .iter()
        .map(|e| e["block_id"].as_str().unwrap_or("").to_string())
        .collect::<std::collections::BTreeSet<_>>()
        .into_iter()
        .collect();

    for i in 0..block_ids.len() {
        for j in (i + 1)..block_ids.len() {
            let left = &block_ids[i];
            let right = &block_ids[j];
            let mut is_blocked = false;
            let _ = &blocks;
            if !is_blocked {
                accepted.push(serde_json::json!({"left": left, "right": right}));
            }
        }
    }

    let digest = guard_digest(&accepted, &blocked);
    let ledger = serde_json::json!({
        "guard_source": "formation-block-guard",
        "block_count": block_ids.len(),
        "blocked_count": blocked.len(),
        "guard_digest": digest,
        "bound_voxel_graph_digest": graph["voxel_graph_digest"],
        "accepted_pairs": accepted,
        "blocked_pairs": blocked,
    });
    fs::write(
        "/app/state/hypothesis-guard-ledger.json",
        serde_json::to_string_pretty(&ledger).unwrap() + "\n",
    )
    .map_err(|e| e.to_string())?;
    Ok(())
}
