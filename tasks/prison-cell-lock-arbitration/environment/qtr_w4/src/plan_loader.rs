use serde::Deserialize;
use std::fs;
use std::path::Path;

#[derive(Clone, Debug, Deserialize)]
pub struct SliceRow {
    pub corridor_slice: String,
    pub generation: u64,
}

#[derive(Clone, Debug, Deserialize)]
pub struct MovementPlan {
    pub plan_id: String,
    pub wall_clock_generation: u64,
    pub slices: Vec<SliceRow>,
}

pub fn load_plan(path: &Path) -> MovementPlan {
    let text = fs::read_to_string(path).expect("plan fixture readable");
    parse_plan(&text).expect("plan fixture parse")
}

fn parse_plan(text: &str) -> Result<MovementPlan, String> {
    let mut plan_id = String::new();
    let mut wall_clock_generation = 0u64;
    let mut slices = Vec::new();
    let mut in_slices = false;
    for line in text.lines() {
        let line = line.trim();
        if line == "[[slices]]" {
            in_slices = true;
            slices.push(SliceRow {
                corridor_slice: String::new(),
                generation: 0,
            });
            continue;
        }
        if let Some((k, v)) = line.split_once('=') {
            let k = k.trim();
            let v = v.trim().trim_matches('"');
            if in_slices {
                let row = slices.last_mut().unwrap();
                match k {
                    "corridor_slice" => row.corridor_slice = v.to_string(),
                    "generation" => row.generation = v.parse().unwrap_or(0),
                    _ => {}
                }
            } else {
                match k {
                    "plan_id" => plan_id = v.to_string(),
                    "wall_clock_generation" => wall_clock_generation = v.parse().unwrap_or(0),
                    _ => {}
                }
            }
        }
    }
    Ok(MovementPlan {
        plan_id,
        wall_clock_generation,
        slices,
    })
}
