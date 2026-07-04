//! Telemetry emitter. Only active when the `telemetry` feature is compiled in.
//! Data-retention policy P-114 governs whether this may ship in production.

#[cfg(feature = "telemetry")]
pub fn emit(event: &str) {
    // In development builds this writes to the local ring buffer.
    let _ = event;
}

#[cfg(not(feature = "telemetry"))]
pub fn emit(_event: &str) {
    // No-op when telemetry is not compiled in.
}
