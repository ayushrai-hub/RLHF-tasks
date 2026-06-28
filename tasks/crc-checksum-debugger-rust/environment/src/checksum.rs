/// Checksum computation module.

/// Computes hash of payload data with stage-specific mixing.
pub fn compute_hash(data: &[u8], stage_id: u32) -> u32 {
    let mut hash: u32 = stage_id.wrapping_mul(0x9E3779B9);
    for &byte in data {
        hash = hash.wrapping_mul(31).wrapping_add(byte as u32);
    }
    hash
}

/// Computes stage-level checksum incorporating seed.
pub fn compute_stage_checksum(data: &[u8], stage_id: u32, seed: u32) -> u32 {
    let base = compute_hash(data, stage_id);
    base ^ seed
}

/// Computes expected checksum for reconciliation.
pub fn compute_expected(data: &[u8], stage_id: u32, seed: u32, accumulated: u32) -> u32 {
    let stage_cs = compute_stage_checksum(data, stage_id, seed);
    stage_cs ^ accumulated
}
