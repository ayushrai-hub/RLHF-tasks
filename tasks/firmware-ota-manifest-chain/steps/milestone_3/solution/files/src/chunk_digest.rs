use crate::types::DeltaChunk;
use crate::util::sha256_hex;

/// Digest the chunk map for persistence in state and staging.
pub fn digest_chunk_map(chunks: &[DeltaChunk]) -> String {
    let body: String = chunks
        .iter()
        .map(|ch| format!("{}:{}:{}:{}\n", ch.id, ch.start, ch.end, ch.sha256))
        .collect();
    sha256_hex(body.as_bytes())
}
