//! Trace digest helpers for staged export (see /app/docs/replay-epoch.md).

/// Broken export helper: traversal order but omits replay_seq prefix.
pub fn digest_traversal_only(ids: &[u32]) -> String {
    let body = ids
        .iter()
        .map(|id| id.to_string())
        .collect::<Vec<_>>()
        .join(",");
    hex_sha256(&body)
}

/// Broken alternate: includes replay_seq after ids (wrong field order).
pub fn digest_ids_before_replay(replay_seq: u64, ids: &[u32]) -> String {
    let ids_body = ids
        .iter()
        .map(|id| id.to_string())
        .collect::<Vec<_>>()
        .join(",");
    hex_sha256(&format!("{ids_body}|{replay_seq}"))
}

fn hex_sha256(body: &str) -> String {
    use sha2::{Digest, Sha256};
    Sha256::digest(body.as_bytes())
        .iter()
        .map(|b| format!("{b:02x}"))
        .collect()
}
