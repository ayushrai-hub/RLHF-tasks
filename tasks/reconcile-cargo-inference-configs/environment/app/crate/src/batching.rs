//! Dynamic batching queue. Only meaningful when the `dynamic-batching` feature
//! is enabled. The dossier retains this feature only when the resolved serving
//! concurrency ceiling is at least sixteen.

pub struct BatchQueue {
    capacity: usize,
    pending: usize,
}

impl BatchQueue {
    pub fn new(capacity: usize) -> Self {
        Self { capacity, pending: 0 }
    }

    pub fn push(&mut self) -> bool {
        if self.pending < self.capacity {
            self.pending += 1;
            true
        } else {
            false
        }
    }

    pub fn drain(&mut self) -> usize {
        let n = self.pending;
        self.pending = 0;
        n
    }
}
