use crate::types::PlanRow;
use std::fs;
use std::path::Path;

pub fn load_plan(path: &Path) -> std::io::Result<Vec<PlanRow>> {
    let text = fs::read_to_string(path)?;
    let mut lines = text.lines();
    let _ = lines.next();
    let mut rows = Vec::new();
    for line in lines {
        if line.trim().is_empty() {
            continue;
        }
        let c: Vec<_> = line.split('|').collect();
        rows.push(PlanRow {
            tag: c[0].into(),
            y0: c[1].parse().unwrap_or(0.0),
            dt: c[2].parse().unwrap_or(0.0),
            steps: c[3].parse().unwrap_or(0),
            callback_order: c[4].into(),
            restart_step: c[5].parse().unwrap_or(-1),
        });
    }
    Ok(rows)
}
