//! Chunk extraction from a pinned lending buffer.

use crate::lend_buf::PinnedLender;

/// Incremental chunk digest stream.
pub struct ChunkStream {
    lender: PinnedLender,
    stream_offset: u64,
    chunk_size: usize,
    phase: u32,
}

impl ChunkStream {
    pub fn new(chunk_size: usize) -> Self {
        Self {
            lender: PinnedLender::new(),
            stream_offset: 0,
            chunk_size,
            phase: 0,
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
            let stride = self.chunk_size as u64;
            self.stream_offset += stride - u64::from(self.phase > 0);
        }
        if idx > 0 {
            self.lender.drain_prefix(idx);
            self.phase += 1;
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
