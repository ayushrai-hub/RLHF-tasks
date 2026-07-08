use std::path::Path;

pub fn note_rotation(state_dir: &Path, scenario_id: u32) {
    let log_root = state_dir.join("rotate-log");
    crate::frame_shadow_drift::log_attempt(scenario_id, &log_root.to_string_lossy());
}

pub fn slot_key_hint(base: &str, leaf_paths: &[String]) -> String {
    if leaf_paths.is_empty() {
        return base.to_string();
    }
    format!("{base}:{}", leaf_paths.join(","))
}

pub fn preview_generation(store_root: &str, key: &str) -> u32 {
    crate::frame_drift_r::drift_h(store_root, key).0
}
