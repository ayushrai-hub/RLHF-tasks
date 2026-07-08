use serde_json::Value;
use sha2::{Digest, Sha256};

pub fn digest_lines(rows: &[Value]) -> String {
    let mut parts: Vec<String> = Vec::new();
    for row in rows {
        let scenario = row.get("scenario").and_then(|v| v.as_i64()).unwrap_or(0);
        let view = row.get("view").and_then(|v| v.as_str()).unwrap_or("");
        let principal = row.get("principal").and_then(|v| v.as_str()).unwrap_or("");
        let label = row.get("label").and_then(|v| v.as_str()).unwrap_or("");
        let generation = row.get("generation").and_then(|v| v.as_i64()).unwrap_or(0);
        parts.push(format!(
            "{scenario},{view},{principal},{label},{generation}"
        ));
    }
    parts.sort();
    let payload = parts.join("\n") + "\n";
    format!("{:x}", Sha256::digest(payload.as_bytes()))
}
