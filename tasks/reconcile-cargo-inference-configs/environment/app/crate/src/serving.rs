//! Serving loop. Reads the effective config and drives batched inference.

use crate::config::CrateConfig;

pub struct Server {
    cfg: CrateConfig,
}

impl Server {
    pub fn new(cfg: CrateConfig) -> Self {
        Self { cfg }
    }

    pub fn effective_batch(&self) -> usize {
        self.cfg.max_batch_size
    }

    pub fn effective_concurrency(&self) -> usize {
        self.cfg.max_concurrency
    }

    pub fn effective_timeout_ms(&self) -> u64 {
        self.cfg.request_timeout_ms
    }
}
