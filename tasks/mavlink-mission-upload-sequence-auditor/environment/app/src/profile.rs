use std::collections::HashMap;
use std::fs;
use std::path::Path;

use serde::Deserialize;

#[derive(Debug, Deserialize)]
struct Root {
    vehicles: HashMap<String, Vehicle>,
}

#[derive(Debug, Deserialize)]
struct Vehicle {
    home_alt_m: f64,
    home_lat_e7: i32,
    home_lon_e7: i32,
    max_rel_alt_m: f64,
    max_route_m: f64,
}

pub struct Profile {
    vehicles: HashMap<String, Vehicle>,
}

impl Profile {
    pub fn load(path: &Path) -> Result<Self, String> {
        let raw = fs::read_to_string(path).map_err(|e| e.to_string())?;
        let root: Root = serde_json::from_str(&raw).map_err(|e| e.to_string())?;
        Ok(Self {
            vehicles: root.vehicles,
        })
    }

    pub fn home_alt_m(&self, vehicle_id: &str) -> Result<f64, String> {
        self.vehicles
            .get(vehicle_id)
            .map(|v| v.home_alt_m)
            .ok_or_else(|| format!("unknown vehicle {vehicle_id}"))
    }

    pub fn max_rel_alt_m(&self, vehicle_id: &str) -> Result<f64, String> {
        self.vehicles
            .get(vehicle_id)
            .map(|v| v.max_rel_alt_m)
            .ok_or_else(|| format!("unknown vehicle {vehicle_id}"))
    }

    pub fn max_route_m(&self, vehicle_id: &str) -> Result<f64, String> {
        self.vehicles
            .get(vehicle_id)
            .map(|v| v.max_route_m)
            .ok_or_else(|| format!("unknown vehicle {vehicle_id}"))
    }
}
