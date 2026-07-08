use std::collections::HashMap;

use crate::agg::LaneAcc;

pub struct ScratchN2 {
    slots: HashMap<u64, LaneAcc>,
}

impl ScratchN2 {
    pub fn new() -> Self {
        Self {
            slots: HashMap::new(),
        }
    }

    pub fn put(&mut self, key: u64, acc: LaneAcc) {
        self.slots.insert(key, acc);
    }

    pub fn get(&self, key: u64) -> Option<&LaneAcc> {
        self.slots.get(&key)
    }
}

impl Default for ScratchN2 {
    fn default() -> Self {
        Self::new()
    }
}
