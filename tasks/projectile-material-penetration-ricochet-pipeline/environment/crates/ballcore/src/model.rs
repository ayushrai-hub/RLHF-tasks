use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq)]
pub struct Vec3 {
    pub x: f64,
    pub y: f64,
    pub z: f64,
}

impl Vec3 {
    pub fn dot(self, other: Self) -> f64 {
        self.x * other.x + self.y * other.y + self.z * other.z
    }

    pub fn scale(self, s: f64) -> Self {
        Self {
            x: self.x * s,
            y: self.y * s,
            z: self.z * s,
        }
    }

    pub fn sub(self, other: Self) -> Self {
        Self {
            x: self.x - other.x,
            y: self.y - other.y,
            z: self.z - other.z,
        }
    }

    pub fn magnitude(self) -> f64 {
        (self.x * self.x + self.y * self.y + self.z * self.z).sqrt()
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct MaterialSpec {
    pub physics_id: u32,
    pub asset_name: String,
    pub hardness: f64,
    pub falloff: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct LayerSpec {
    pub physics_id: u32,
    #[serde(default)]
    pub asset_label: Option<String>,
    pub thickness_m: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct StackSpec {
    pub name: String,
    pub normal: [f64; 3],
    pub layers: Vec<LayerSpec>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct LayerResult {
    pub physics_id: u32,
    pub depth_m: f64,
    pub fully_penetrated: bool,
    pub energy_after_j: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct RicochetResult {
    pub incident_angle_deg: f64,
    pub exit_angle_deg: f64,
    pub velocity_out: [f64; 3],
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct ShotSnapshot {
    pub staging_version: u32,
    pub stack: String,
    pub seed: u64,
    #[serde(default)]
    pub replay_seq: u64,
    pub path_ledger_m: f64,
    pub exit_energy_j: f64,
    pub penetrated: bool,
    pub layers: Vec<LayerResult>,
    pub ricochet: Option<RicochetResult>,
    pub trace_ids: Vec<u32>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct ShotResult {
    pub stack: String,
    pub seed: u64,
    pub path_ledger_m: f64,
    pub exit_energy_j: f64,
    pub penetrated: bool,
    pub layers: Vec<LayerResult>,
    pub ricochet: Option<RicochetResult>,
    pub trace_digest: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct ShotInput {
    pub stack: StackSpec,
    pub velocity: Vec3,
    pub energy_j: f64,
    pub seed: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct BatchEvent {
    pub sim_tick: u64,
    pub shot_id: u64,
    pub stack: String,
    pub velocity: [f64; 3],
    pub energy_j: f64,
    pub seed: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct BatchSpec {
    pub name: String,
    pub events: Vec<BatchEvent>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct BatchHit {
    pub sim_tick: u64,
    pub shot_id: u64,
    #[serde(flatten)]
    pub shot: ShotResult,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct BatchTick {
    pub sim_tick: u64,
    pub hits: Vec<BatchHit>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct BatchResult {
    pub batch: String,
    pub ticks: Vec<BatchTick>,
}
