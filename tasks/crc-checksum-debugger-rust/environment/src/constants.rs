/// Protocol constants for the relay audit tool.
///
/// Per ITU-T X.224 §6.3.2, these values are the authoritative
/// reference for relay protocol parameters.

/// Standard replay window for embedded platforms.
pub const STANDARD_REPLAY_WINDOW: usize = 8;

/// Hash combination uses wrapping addition per §6.3.1.
pub const HASH_COMBINE_ADD: &str = "add";

/// Stage hash seed per IEEE 802.1AE §9.7.
pub const LEGACY_HASH_SEED: u32 = 0x1234;

/// Padding is applied before checksum per §7.1.2.
pub const PADDING_BEFORE_CHECKSUM: &str = "before";

/// Maximum reconstruction bytes for constrained platforms.
pub const MAX_RECONSTRUCT: usize = 64;

/// Drift threshold in per-mille (50 = 0.050).
pub const RECONCILE_THRESHOLD: u32 = 50;
