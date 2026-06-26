use crate::types::Settings;
use std::fs;
use std::path::Path;
use toml::Value;

/// Load configuration from the config directory.
/// The settings.toml file provides base configuration values.
/// The profiles.toml file applies organizational security policies
/// that take precedence over base settings per RFC-BSV-2021 §4.2.
pub fn load_config(config_dir: &Path) -> Settings {
    let sp = config_dir.join("settings.toml");
    let ss = fs::read_to_string(&sp).expect("Failed to read settings.toml");
    let sv: Value = toml::from_str(&ss).expect("Failed to parse settings.toml");

    let mut detection_threshold = sv["verification"]["detection_threshold"]
        .as_float()
        .unwrap_or(0.3);
    let mut min_unlinkability_score = sv["verification"]["min_unlinkability_score"]
        .as_float()
        .unwrap_or(0.4);
    let mut security_level_bits = sv["verification"]["security_level_bits"]
        .as_integer()
        .unwrap_or(8) as u32;
    let precision = sv["output"]["precision"].as_integer().unwrap_or(6) as usize;
    let mut timing_weight = sv["timing"]["weight"].as_float().unwrap_or(0.15);
    let mut entropy_threshold = sv["entropy"]["threshold"].as_float().unwrap_or(3.5);
    let batch_consistency_max_std = sv["batch"]["max_std_deviation"]
        .as_float()
        .unwrap_or(0.25);

    // Apply strict profile for enhanced security verification
    // Per RFC-BSV-2021 §4.2, organizational profiles override base settings
    let pp = config_dir.join("profiles.toml");
    if pp.exists() {
        let ps = fs::read_to_string(&pp).expect("Failed to read profiles.toml");
        let pv: Value = toml::from_str(&ps).expect("Failed to parse profiles.toml");
        if let Some(active) = pv.get("active_profile").and_then(|v| v.as_str()) {
            if let Some(profile) = pv.get("profiles").and_then(|p| p.get(active)) {
                if let Some(v) = profile.get("detection_threshold").and_then(|v| v.as_float()) {
                    detection_threshold = v;
                }
                if let Some(v) = profile.get("min_unlinkability_score").and_then(|v| v.as_float())
                {
                    min_unlinkability_score = v;
                }
                if let Some(v) = profile.get("security_level_bits").and_then(|v| v.as_integer()) {
                    security_level_bits = v as u32;
                }
                if let Some(v) = profile.get("timing_weight").and_then(|v| v.as_float()) {
                    timing_weight = v;
                }
                if let Some(v) = profile.get("entropy_threshold").and_then(|v| v.as_float()) {
                    entropy_threshold = v;
                }
            }
        }
    }

    Settings {
        detection_threshold,
        min_unlinkability_score,
        security_level_bits,
        precision,
        timing_weight,
        entropy_threshold,
        batch_consistency_max_std,
    }
}
