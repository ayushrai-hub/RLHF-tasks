//! Staging frame boundary helpers.

/// First-frame byte count for schedules longer than two chunk blocks.
pub fn long_frame_end(payload_len: usize, chunk_size: usize) -> usize {
    let block = chunk_size * 2;
    block.saturating_sub(1).min(payload_len)
}

/// Byte offset where the second short-frame feed begins.
pub fn short_remainder_start(chunk_size: usize, payload_len: usize) -> usize {
    chunk_size - usize::from(payload_len == chunk_size * 2)
}
