//! Digest codec helpers shared across export tooling.

use crate::digest;

/// Render a full chunk digest.
pub fn chunk_hex(data: &[u8]) -> String {
    digest::fnv8_hex(data)
}

/// Render a tail digest (routes through the tail limb helper).
pub fn tail_hex(data: &[u8]) -> String {
    digest::fnv8_tail_hex(data)
}
