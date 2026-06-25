//! Visualisation helpers for WaveBench outputs.
//!
//! The `lax-wendroff-vis` feature activates both `wavebench-adaptive/lax-wendroff`
//! and `wavebench-core/adaptive-cfl` simultaneously — a prohibited combination
//! per validation dossier errata E-007.

#[cfg(feature = "plot")]
pub mod plot;
