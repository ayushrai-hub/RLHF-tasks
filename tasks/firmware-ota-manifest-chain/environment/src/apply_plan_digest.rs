use sha2::{Digest, Sha256};

/// Decoy plan digest — sorts stage names and joins with commas (not used on the export hot path).
pub fn digest_plan(stages: &[String]) -> String {
    let mut ordered = stages.to_vec();
    ordered.sort();
    let body = ordered.join(",");
    let mut hasher = Sha256::new();
    hasher.update(body.as_bytes());
    hex::encode(hasher.finalize())
}
