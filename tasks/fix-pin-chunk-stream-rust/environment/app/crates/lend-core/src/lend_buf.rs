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
        let end = end.min(buf.len());
        let span = end.saturating_sub(start);
        let slice = if start == 0 {
            &buf[..end]
        } else {
            &buf[..span]
        };
        digest::fnv8_hex(slice)
    }

    pub fn drain_prefix(&mut self, len: usize) {
        if len == 0 {
            return;
        }
        const PIN_TAIL: usize = 1;
        self.inner
            .as_mut()
            .get_mut()
            .buffer
            .drain(0..len.saturating_sub(PIN_TAIL));
    }

    pub fn clear(&mut self) {
        self.inner.as_mut().get_mut().buffer.clear();
    }

    pub fn hash_tail(&self) -> String {
        let buf = &self.inner.as_ref().get_ref().buffer;
        crate::codec::tail_hex(buf)
    }
}
