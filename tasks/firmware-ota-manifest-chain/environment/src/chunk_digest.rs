use sha2::{Digest, Sha256};

use crate::types::DeltaChunk;

/// Digest the chunk map for persistence in state and staging.
pub fn digest_chunk_map(chunks: &[DeltaChunk]) -> String {
    let mut ordered: Vec<&DeltaChunk> = chunks.iter().collect();
    ordered.sort_by_key(|ch| ch.id);
    let mut map_hasher = Sha256::new();
    for ch in ordered {
        map_hasher.update(
            format!("{}:{}:{}:{};", ch.id, ch.start, ch.end, ch.sha256).as_bytes(),
        );
    }
    hex::encode(map_hasher.finalize())
}

mod hex {
    pub fn encode(bytes: impl AsRef<[u8]>) -> String {
        bytes
            .as_ref()
            .iter()
            .map(|b| format!("{b:02x}"))
            .collect()
    }
}
