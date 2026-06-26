#!/usr/bin/env bash
set -euo pipefail

cd /app

cat > crates/lend-core/src/frame.rs <<'EOF'
//! Staging frame boundary helpers.

/// First-frame byte count for schedules longer than two chunk blocks.
pub fn long_frame_end(payload_len: usize, chunk_size: usize) -> usize {
    let block = chunk_size * 2;
    block.min(payload_len)
}

/// Byte offset where the second short-frame feed begins.
pub fn short_remainder_start(chunk_size: usize, _payload_len: usize) -> usize {
    chunk_size
}
EOF

cat > crates/lend-core/src/ingest.rs <<'EOF'
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
EOF

cat > crates/lend-core/src/replay.rs <<'EOF'
//! Trace payload replay helpers.

use std::fs;
use std::path::{Path, PathBuf};

use crate::ingest::staged_digest_lines;

pub fn digest_lines_for_payload(payload: &[u8], chunk_size: usize) -> Vec<String> {
    staged_digest_lines(payload, chunk_size)
}

pub fn probe_offsets_for_payload(payload: &[u8], chunk_size: usize) -> Vec<u64> {
    digest_lines_for_payload(payload, chunk_size)
        .iter()
        .map(|line| {
            let offset = line.split(':').next().expect("offset");
            offset.parse::<u64>().expect("parse offset")
        })
        .collect()
}

pub fn collect_trace_paths(dir: &Path, out: &mut Vec<PathBuf>) -> std::io::Result<()> {
    if !dir.is_dir() {
        return Ok(());
    }
    for entry in fs::read_dir(dir)? {
        let entry = entry?;
        let path = entry.path();
        if path.is_dir() {
            collect_trace_paths(&path, out)?;
        } else if path.extension().and_then(|s| s.to_str()) == Some("trace") {
            out.push(path);
        }
    }
    Ok(())
}

pub fn replay_dir(
    traces_dir: &Path,
    chunk_size: usize,
) -> std::io::Result<Vec<(String, Vec<String>)>> {
    let mut paths = Vec::new();
    collect_trace_paths(traces_dir, &mut paths)?;
    paths.sort();

    let mut runs = Vec::new();
    for path in paths {
        let rel = path
            .strip_prefix(traces_dir)
            .unwrap_or(&path)
            .to_string_lossy()
            .to_string();
        let payload = fs::read(&path)?;
        let lines = digest_lines_for_payload(&payload, chunk_size);
        runs.push((rel, lines));
    }
    Ok(runs)
}
EOF

cat > crates/lend-core/src/digest.rs <<'EOF'
//! FNV-1a 64-bit digest rendered as eight lowercase hex digits.

const FNV_OFFSET: u64 = 0xcbf29ce484222325;
const FNV_PRIME: u64 = 0x100000001b3;

fn run_fnv(data: &[u8]) -> u64 {
    let mut hash = FNV_OFFSET;
    for byte in data {
        hash ^= u64::from(*byte);
        hash = hash.wrapping_mul(FNV_PRIME);
    }
    hash
}

/// Hash `data` with FNV-1a 64 and return the low eight hex digits.
pub fn fnv8_hex(data: &[u8]) -> String {
    format!("{:08x}", run_fnv(data) & 0xffffffff)
}

/// Tail chunks use the same limb as full chunks.
pub fn fnv8_tail_hex(data: &[u8]) -> String {
    fnv8_hex(data)
}
EOF

cat > crates/lend-core/src/lend_buf.rs <<'EOF'
//! Pin wrapper around the internal lending buffer.

use std::pin::Pin;

use crate::digest;

/// Internal byte reservoir for incremental chunk extraction.
pub struct LendBuffer {
    pub buffer: Vec<u8>,
}

impl LendBuffer {
    pub fn new() -> Self {
        Self {
            buffer: Vec::new(),
        }
    }
}

/// Pinned lender — the stream chunker holds this behind `Pin<Box<_>>`.
pub struct PinnedLender {
    inner: Pin<Box<LendBuffer>>,
}

impl PinnedLender {
    pub fn new() -> Self {
        Self {
            inner: Pin::new(Box::new(LendBuffer::new())),
        }
    }

    pub fn push(&mut self, data: &[u8]) {
        self.inner.as_mut().get_mut().buffer.extend_from_slice(data);
    }

    pub fn buffer_len(&self) -> usize {
        self.inner.as_ref().get_ref().buffer.len()
    }

    pub fn hash_range(&self, start: usize, end: usize) -> String {
        let buf = &self.inner.as_ref().get_ref().buffer;
        digest::fnv8_hex(&buf[start..end])
    }

    pub fn drain_prefix(&mut self, len: usize) {
        self.inner.as_mut().get_mut().buffer.drain(0..len);
    }

    pub fn clear(&mut self) {
        self.inner.as_mut().get_mut().buffer.clear();
    }

    pub fn hash_tail(&self) -> String {
        let buf = &self.inner.as_ref().get_ref().buffer;
        digest::fnv8_tail_hex(buf)
    }
}
EOF

cat > crates/lend-core/src/chunker.rs <<'EOF'
//! Chunk extraction from a pinned lending buffer.

use crate::lend_buf::PinnedLender;

/// Incremental chunk digest stream.
pub struct ChunkStream {
    lender: PinnedLender,
    stream_offset: u64,
    chunk_size: usize,
}

impl ChunkStream {
    pub fn new(chunk_size: usize) -> Self {
        Self {
            lender: PinnedLender::new(),
            stream_offset: 0,
            chunk_size,
        }
    }

    pub fn feed(&mut self, data: &[u8]) {
        self.lender.push(data);
    }

    /// Drain every full chunk currently buffered.
    pub fn drain_lines(&mut self) -> Vec<String> {
        let mut lines = Vec::new();
        let mut idx = 0usize;
        while idx + self.chunk_size <= self.lender.buffer_len() {
            let digest = self
                .lender
                .hash_range(idx, idx + self.chunk_size);
            lines.push(format!("{}:{}", self.stream_offset, digest));
            idx += self.chunk_size;
            self.stream_offset += self.chunk_size as u64;
        }
        if idx > 0 {
            self.lender.drain_prefix(idx);
        }
        lines
    }

    /// Emit a digest for trailing bytes shorter than `chunk_size`.
    pub fn finish(&mut self) -> Option<String> {
        if self.lender.buffer_len() == 0 {
            return None;
        }
        let tail_len = self.lender.buffer_len();
        let digest = self.lender.hash_tail();
        let line = format!("{}:{}", self.stream_offset, digest);
        self.stream_offset += tail_len as u64;
        self.lender.clear();
        Some(line)
    }
}
EOF

export PATH="/usr/local/cargo/bin:${PATH}"
cargo build --release --locked
cargo test --workspace --locked
make release
