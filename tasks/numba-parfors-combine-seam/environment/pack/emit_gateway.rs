use crate::pack_fold_r8::fold_r8;
use crate::pack_mix_r8::digest_lines;
use serde_json::{json, Value};
use std::fs;
use std::path::Path;

fn wal_physically_valid(state_dir: &Path) -> bool {
    crate::wal::wal_crc_chain_intact(state_dir)
}

pub fn emit_report(out: &Path) -> bool {
    let state_dir = Path::new("/app/replay-state");
    if !wal_physically_valid(state_dir) {
        return false;
    }
    if !crate::engine::checkpoint_ready(state_dir) {
        return false;
    }
    let (reduce_rows, live_rows, promote_rows) = load_epochs(state_dir);
    let mut merged = fold_r8(&reduce_rows, &promote_rows);
    if !live_rows.is_empty() {
        merged.extend(live_rows);
    }
    merged.sort_by(|a, b| {
        let sa = a.get("scenario").and_then(|v| v.as_i64()).unwrap_or(0);
        let sb = b.get("scenario").and_then(|v| v.as_i64()).unwrap_or(0);
        let va = a.get("view").and_then(|v| v.as_str()).unwrap_or("");
        let vb = b.get("view").and_then(|v| v.as_str()).unwrap_or("");
        let pa = a.get("principal").and_then(|v| v.as_str()).unwrap_or("");
        let pb = b.get("principal").and_then(|v| v.as_str()).unwrap_or("");
        (sa, va, pa).cmp(&(sb, vb, pb))
    });
    let bundle = json!({
        "epochs": merged,
        "body_digest": digest_lines(&merged),
    });
    if let Some(parent) = out.parent() {
        let _ = fs::create_dir_all(parent);
    }
    fs::write(out, serde_json::to_string_pretty(&bundle).unwrap() + "\n").is_ok()
}

fn load_epochs(state_dir: &Path) -> (Vec<Value>, Vec<Value>, Vec<Value>) {
    let mut reduce_rows = Vec::new();
    let mut live_rows = Vec::new();
    let mut promote_rows = Vec::new();
    let mut seq_ids: Vec<u32> = Vec::new();
    if let Ok(entries) = fs::read_dir(state_dir) {
        for ent in entries.flatten() {
            let name = ent.file_name().to_string_lossy().into_owned();
            if let Some(rest) = name.strip_prefix("epoch_") {
                if let Some(stem) = rest.strip_suffix(".json") {
                    if let Ok(n) = stem.parse::<u32>() {
                        seq_ids.push(n);
                    }
                }
            }
        }
    }
    seq_ids.sort();
    for seq_id in seq_ids {
        let cache = state_dir.join(format!("epoch_{seq_id}.json"));
        let chunk: Vec<Value> =
            serde_json::from_str(&fs::read_to_string(&cache).unwrap_or_default())
                .unwrap_or_default();
        for row in chunk {
            match row.get("view").and_then(|v| v.as_str()) {
                Some("reduce") => reduce_rows.push(row),
                Some("live") => live_rows.push(row),
                Some("promote") => promote_rows.push(row),
                _ => {}
            }
        }
    }
    (reduce_rows, live_rows, promote_rows)
}
