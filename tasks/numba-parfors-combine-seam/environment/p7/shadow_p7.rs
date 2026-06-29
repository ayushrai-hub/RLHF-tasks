use std::fs;
use std::path::Path;

pub fn log_attempt(scenario_id: u32, log_root: &str) {
    let path = Path::new(log_root).join(format!("renew_{scenario_id}.cnt"));
    let n: u32 = fs::read_to_string(&path)
        .ok()
        .and_then(|t| t.trim().parse().ok())
        .unwrap_or(0);
    let _ = fs::create_dir_all(log_root);
    let _ = fs::write(path, format!("{}\n", n + 1));
}
