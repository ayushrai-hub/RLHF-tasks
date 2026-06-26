//! Staged payload ingest for chunk replay.

use crate::chunker::ChunkStream;
use crate::frame::{long_frame_end, short_remainder_start};

pub fn staged_digest_lines(payload: &[u8], chunk_size: usize) -> Vec<String> {
    let mut stream = ChunkStream::new(chunk_size);
    let mut lines = Vec::new();
    if payload.is_empty() {
        return lines;
    }
    if payload.len() <= chunk_size {
        stream.feed(payload);
        lines.extend(stream.drain_lines());
        if let Some(tail) = stream.finish() {
            lines.push(tail);
        }
        return lines;
    }
    if payload.len() <= chunk_size * 2 {
        let second = short_remainder_start(chunk_size, payload.len());
        stream.feed(&payload[..chunk_size]);
        lines.extend(stream.drain_lines());
        stream.feed(&payload[second..]);
        lines.extend(stream.drain_lines());
        if let Some(tail) = stream.finish() {
            lines.push(tail);
        }
        return lines;
    }
    let split = long_frame_end(payload.len(), chunk_size);
    stream.feed(&payload[..split]);
    lines.extend(stream.drain_lines());
    stream.feed(&payload[split..]);
    lines.extend(stream.drain_lines());
    if let Some(tail) = stream.finish() {
        lines.push(tail);
    }
    lines
}
