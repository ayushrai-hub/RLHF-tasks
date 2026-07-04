//! Runtime configuration loading. Values here are compile-time fallbacks and are
//! superseded by serving.toml at runtime. They are not release-plan values.

use crate::error::InferError;

/// Compile-time fallback batch size. Superseded by serving.toml. NOT a release
/// value; the release plan derives batch size from the dossier rules.
pub const FALLBACK_MAX_BATCH: usize = 64;

/// Compile-time fallback concurrency. Superseded by serving.toml.
pub const FALLBACK_MAX_CONCURRENCY: usize = 4;

/// Compile-time fallback request timeout in milliseconds. Superseded by
/// serving.toml.
pub const FALLBACK_REQUEST_TIMEOUT_MS: u64 = 3000;

#[derive(Debug, Clone)]
pub struct CrateConfig {
    pub max_batch_size: usize,
    pub max_concurrency: usize,
    pub request_timeout_ms: u64,
}

impl CrateConfig {
    pub fn from_toml(text: &str) -> Result<Self, InferError> {
        let value: toml::Value = text.parse().map_err(|_| InferError::Parse)?;
        let serving = value.get("serving").ok_or(InferError::Missing)?;
        Ok(Self {
            max_batch_size: read_usize(serving, "max_batch_size", FALLBACK_MAX_BATCH),
            max_concurrency: read_usize(serving, "max_concurrency", FALLBACK_MAX_CONCURRENCY),
            request_timeout_ms: read_u64(serving, "request_timeout_ms", FALLBACK_REQUEST_TIMEOUT_MS),
        })
    }
}

fn read_usize(v: &toml::Value, key: &str, default: usize) -> usize {
    v.get(key).and_then(|x| x.as_integer()).map(|x| x as usize).unwrap_or(default)
}

fn read_u64(v: &toml::Value, key: &str, default: u64) -> u64 {
    v.get(key).and_then(|x| x.as_integer()).map(|x| x as u64).unwrap_or(default)
}
