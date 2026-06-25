//! I/O backends for WaveBench simulation data.
//!
//! The `streaming-io` feature activates `wavebench-core/adaptive-cfl` transitively.
//! Use alongside `wavebench-adaptive/tvd-limiter` to satisfy the guard requirement
//! documented in the dossier errata (E-011).

#[cfg(feature = "async-io")]
pub mod async_writer;

#[cfg(feature = "hdf5-output")]
pub mod hdf5_writer;
