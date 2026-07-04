//! Bounded evaluation cache for authorization decisions.
//!
//! The cache memoizes `has_permission` results keyed by
//! `(user, resource, action, time_bits)`. It is a fixed-capacity LRU: when it is
//! full, inserting a new key evicts the least-recently-used entry. A *read* of a
//! key counts as a use and must refresh that key's recency, so a repeatedly read
//! ("hot") entry is never evicted ahead of colder ones.
//!
//! Correctness contract for invalidation. An authorization decision for one
//! principal may depend on other principals: a delegatee's decision is derived
//! from its delegators' live authority, transitively along delegation chains.
//! Therefore [`EvaluationCache::invalidate_user`] must remove **every** cached
//! decision whose evaluation depended on the named principal — the principal's
//! own entries and any entry that reached the principal through a delegation
//! chain — while **preserving** every entry that did not depend on it. The cache
//! is performance-critical: invalidation must stay precise so the cache remains
//! effective under churn. Clearing the whole cache on every mutation, or
//! disabling caching, is not an acceptable way to achieve correctness.

use std::cell::RefCell;
use std::collections::{HashMap, VecDeque};

/// Maximum number of live entries. Inserting into a full cache evicts the
/// least-recently-used key first.
pub const CAPACITY: usize = 8;

/// Cache key: `(user_id, resource, action, current_time.to_bits())`.
pub type CacheKey = (String, String, String, u64);

#[derive(Default)]
pub struct EvaluationCache {
    entries: RefCell<HashMap<CacheKey, bool>>,
    order: RefCell<VecDeque<CacheKey>>,
    hits: RefCell<u64>,
    misses: RefCell<u64>,
}

impl EvaluationCache {
    pub fn new() -> Self {
        Self::default()
    }

    /// Look up a cached decision. On a hit the entry's recency must be refreshed
    /// so that it becomes the most-recently-used key; on a miss `None` is
    /// returned. Hit/miss counters back [`EvaluationCache::stats`].
    pub fn get(&self, key: &CacheKey) -> Option<bool> {
        let entries = self.entries.borrow();
        if let Some(&value) = entries.get(key) {
            *self.hits.borrow_mut() += 1;
            Some(value)
        } else {
            *self.misses.borrow_mut() += 1;
            None
        }
    }

    /// Insert or update a decision for `key`. When the cache is at capacity and
    /// `key` is new, the least-recently-used entry is evicted first.
    pub fn set(&self, key: CacheKey, value: bool) {
        let mut entries = self.entries.borrow_mut();
        let mut order = self.order.borrow_mut();

        if entries.contains_key(&key) {
            entries.insert(key.clone(), value);
            order.retain(|existing| existing != &key);
            order.push_back(key);
            return;
        }

        if entries.len() >= CAPACITY {
            if let Some(evicted) = order.pop_front() {
                entries.remove(&evicted);
            }
        }

        entries.insert(key.clone(), value);
        order.push_back(key);
    }

    /// Drop every cached decision.
    pub fn invalidate_all(&self) {
        self.entries.borrow_mut().clear();
        self.order.borrow_mut().clear();
    }

    /// Invalidate every cached decision that depended on `user_id` (see the
    /// module-level contract) while retaining all other entries.
    pub fn invalidate_user(&self, user_id: &str) {
        self.entries.borrow_mut().retain(|key, _| key.0 != user_id);
        self.order.borrow_mut().retain(|key| key.0 != user_id);
    }

    /// Returns `(hits, misses)` observed since construction.
    pub fn stats(&self) -> (u64, u64) {
        (*self.hits.borrow(), *self.misses.borrow())
    }
}
