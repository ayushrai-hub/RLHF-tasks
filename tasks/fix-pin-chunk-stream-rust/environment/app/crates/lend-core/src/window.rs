//! Window hashing helpers for pinned buffers.

use crate::digest;

/// Hash an absolute window inside a byte slice.
pub fn digest_window(data: &[u8], start: usize, end: usize) -> String {
    digest::fnv8_hex(&data[start..end])
}
