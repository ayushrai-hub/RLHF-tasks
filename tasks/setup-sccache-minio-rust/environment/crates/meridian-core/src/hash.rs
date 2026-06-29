use sha2::{Digest, Sha256};
use thiserror::Error;

#[derive(Debug, Error)]
pub enum DigestError {
    #[error("empty input")]
    Empty,
}

pub fn digest_hex(input: &[u8]) -> Result<String, DigestError> {
    if input.is_empty() {
        return Err(DigestError::Empty);
    }
    let mut hasher = Sha256::new();
    hasher.update(input);
    Ok(hex::encode(hasher.finalize()))
}
