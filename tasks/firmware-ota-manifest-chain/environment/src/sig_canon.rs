use crate::types::Envelope;

/// Build the pipe-separated preimage for envelope signature hashing.
pub fn canonical_sig_input(env: &Envelope, epoch_key: &str) -> String {
    format!(
        "{}|{}|{}|{}|{}|{}",
        env.version, env.build_id, env.device, env.epoch, env.payload_sha256, epoch_key
    )
}
