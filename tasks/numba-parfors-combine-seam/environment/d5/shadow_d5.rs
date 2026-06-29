pub fn log_steps(scenario_id: u32, steps: &[&str], log_root: &std::path::Path) {
    use std::fs;
    let _ = fs::create_dir_all(log_root);
    let body = format!("scenario={scenario_id} steps={}", steps.join(","));
    let _ = fs::write(log_root.join("phase-log.txt"), body);
}
