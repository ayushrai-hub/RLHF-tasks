use crate::model::ScenarioRow;
use std::fs;

pub fn load_scenarios(path: &str) -> Vec<ScenarioRow> {
    serde_json::from_str(&fs::read_to_string(path).expect("read")).expect("parse")
}
