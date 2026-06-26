use std::collections::HashMap;
use std::fs::File;
use std::io::{BufRead, BufReader};
use std::path::Path;

use crate::h3::h3::probe_a;

#[path = "../../support/cp_load.rs"]
mod cp_load;

#[derive(Clone, Debug)]
pub struct SegmentData {
    pub epoch: i32,
    pub cells: HashMap<String, String>,
    pub branch: String,
}

pub fn read_segment(path: &Path) -> Result<SegmentData, String> {
    let file = File::open(path).map_err(|e| e.to_string())?;
    let reader = BufReader::new(file);
    let mut data = SegmentData {
        epoch: 0,
        cells: HashMap::new(),
        branch: String::new(),
    };
    for line in reader.lines() {
        let line = line.map_err(|e| e.to_string())?;
        let line = line.trim();
        if line.is_empty() || line.starts_with('#') {
            continue;
        }
        let Some((key, val)) = line.split_once('=') else {
            continue;
        };
        let key = key.trim();
        let val = val.trim();
        match key {
            "epoch" => {
                data.epoch = val.parse().unwrap_or(0);
            }
            "branch" => {
                data.branch = val.to_string();
            }
            _ if key.starts_with("ent_") => {
                let cell = probe_a::materialize_cell(data.epoch, val);
                data.cells.insert(key.to_string(), cell);
            }
            _ => {}
        }
    }
    Ok(data)
}

pub fn read_checkpoint_markers(path: &Path) -> Result<(HashMap<String, String>, String), String> {
    cp_load::read_checkpoint_markers(path)
}
