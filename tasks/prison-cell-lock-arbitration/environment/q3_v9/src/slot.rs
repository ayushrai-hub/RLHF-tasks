use serde::{Deserialize, Serialize};

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct ScheduleSnapshot {
    pub generation: u64,
    pub wall_clock_generation: u64,
}

pub fn load_interval_snapshot(generation: u64, wall_ms: u64) -> ScheduleSnapshot {
    ScheduleSnapshot {
        generation,
        wall_clock_generation: wall_ms / 1000,
    }
}

pub fn current_interval_id(wall_ms: u64) -> u64 {
    wall_ms / 5000
}
