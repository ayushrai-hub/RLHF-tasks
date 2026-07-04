use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;

#[derive(Debug, Deserialize, Clone)]
pub struct Unit {
    pub id: String,
    pub fuel: String,
    pub bus: String,
    pub feeder: String,
    pub capacity_kw: f64,
    pub avail: f64,
    pub emission_rate: f64,
    pub responsiveness: f64,
    pub min_stable: f64,
    pub degraded: bool,
}

#[derive(Debug, Deserialize, Clone)]
pub struct Config {
    pub buses: Vec<String>,
    pub feeders: Vec<String>,
    pub fuels: Vec<String>,
    pub total_demand_kw: f64,
    pub emission_budget: f64,
    pub renewable_min_fraction: f64,
    pub reserve_requirement_kw: f64,
    pub per_bus_min_kw: BTreeMap<String, f64>,
    pub conflict_pairs: Vec<Vec<String>>,
    pub mandatory_online_units: Vec<String>,
    pub max_committed_thermal: usize,
    pub nominal_frequency: f64,
}

/// One unit's dispatch decision.
#[derive(Debug, Serialize)]
pub struct Allocation {
    pub unit_id: String,
    pub dispatch_fraction: f64,
    pub reserve_share: f64,
}

/// The object written to `output_data/dispatch.json` and read by `model.py`.
#[derive(Debug, Serialize)]
pub struct Dispatch {
    pub allocations: Vec<Allocation>,
    pub frequency_setpoint: f64,
}
