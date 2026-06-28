use sha2::{Digest, Sha256};
use std::collections::BTreeMap;
use std::fs;
use std::path::Path;

pub fn sha256_hex(data: &[u8]) -> String {
    let mut hasher = Sha256::new();
    hasher.update(data);
    format!("{:x}", hasher.finalize())
}

pub fn file_digest(path: &str) -> Result<String, String> {
    let data = fs::read(path).map_err(|e| e.to_string())?;
    Ok(sha256_hex(&data))
}

pub fn die_root_digest(root: &str) -> Result<String, String> {
    let root_path = Path::new(root);
    let mut parts: BTreeMap<String, String> = BTreeMap::new();
    if root_path.is_dir() {
        for entry in fs::read_dir(root_path).map_err(|e| e.to_string())? {
            let entry = entry.map_err(|e| e.to_string())?;
            if entry.file_type().map_err(|e| e.to_string())?.is_file() {
                let name = entry.file_name().to_string_lossy().to_string();
                let data = fs::read(entry.path()).map_err(|e| e.to_string())?;
                parts.insert(name, sha256_hex(&data));
            }
        }
    }
    let canonical = serde_json::to_string(&parts).map_err(|e| e.to_string())?;
    Ok(sha256_hex(canonical.as_bytes()))
}

pub fn journal_stream_digest(entries: &[crate::journal::OpEntry]) -> String {
    let mut rows = Vec::new();
    for entry in entries {
        rows.push(format!(
            "{}|{}|{}|{}|{}|{}",
            entry.scenario_tag,
            entry.seq,
            entry.journal_revision,
            entry.op,
            entry.die_id,
            entry.op_id
        ));
    }
    rows.sort();
    sha256_hex(rows.join("\n").as_bytes())
}

pub fn lineage_digest_hex(
    packs: &[crate::journal::LineagePackDigest],
    surviving_op_ids: &[String],
) -> String {
    use std::collections::BTreeMap;
    let pack_rows: Vec<BTreeMap<String, serde_json::Value>> = packs
        .iter()
        .map(|p| {
            let mut row: BTreeMap<String, serde_json::Value> = BTreeMap::new();
            row.insert("generation".into(), serde_json::json!(p.generation));
            row.insert("id".into(), serde_json::json!(p.id));
            row.insert("journal_digest".into(), serde_json::json!(p.journal_digest));
            row.insert(
                "parent".into(),
                match &p.parent {
                    Some(v) => serde_json::json!(v),
                    None => serde_json::Value::Null,
                },
            );
            row
        })
        .collect();
    let mut op_ids = surviving_op_ids.to_vec();
    op_ids.sort();
    let mut payload: BTreeMap<String, serde_json::Value> = BTreeMap::new();
    payload.insert("packs".into(), serde_json::to_value(&pack_rows).unwrap());
    payload.insert(
        "surviving_op_ids".into(),
        serde_json::Value::Array(
            op_ids
                .into_iter()
                .map(serde_json::Value::String)
                .collect(),
        ),
    );
    let canonical = serde_json::to_string(&payload).unwrap_or_default();
    sha256_hex(canonical.as_bytes())
}
