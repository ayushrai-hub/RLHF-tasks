//! Trace digest helpers for staged export (see /app/docs/replay-epoch.md).

pub fn digest_shot_export(replay_seq: u64, ids: &[u32]) -> String {
    let ids_body = ids
        .iter()
        .map(|id| id.to_string())
        .collect::<Vec<_>>()
        .join(",");
    hex_sha256(&format!("{replay_seq}|{ids_body}"))
}

fn hex_sha256(body: &str) -> String {
    use sha2::{Digest, Sha256};
    Sha256::digest(body.as_bytes())
        .iter()
        .map(|b| format!("{b:02x}"))
        .collect()
}
