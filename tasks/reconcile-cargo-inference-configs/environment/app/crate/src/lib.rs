//! sentiment-infer: CPU inference crate for the sentiment-transformer model.
//!
//! Configuration precedence at runtime is: serving.toml overrides the
//! compile-time fallbacks in this crate. Release-time reconciliation is a
//! separate process governed by the platform dossier and is NOT implemented
//! here.

pub mod batching;
pub mod config;
pub mod error;
pub mod features;
pub mod quantize;
pub mod serving;
pub mod telemetry;

pub use config::CrateConfig;
pub use error::InferError;

/// Crate package version string, injected by Cargo at build time.
pub const CRATE_VERSION: &str = env!("CARGO_PKG_VERSION");
