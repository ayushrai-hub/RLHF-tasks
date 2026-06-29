use std::fs;
use std::path::Path;

pub fn log_probe(audit_root: &str, scenario_id: u32) {
    let root = Path::new(audit_root);
    let _ = fs::create_dir_all(root.join("stats"));
    let _ = fs::write(root.join("stats/last_scenario.txt"), scenario_id.to_string());
}
