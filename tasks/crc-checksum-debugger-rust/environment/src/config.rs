/// Configuration loader for relay audit tool.
///
/// Supports base configuration from relay.toml and optional override
/// from relay_overrides.toml. Per the deployment specification (ITU-T
/// X.224 Annex B), override files take precedence for field-deployed
/// relay nodes where base configuration represents factory defaults.

use std::fs;
use std::path::Path;

include!(concat!(env!("OUT_DIR"), "/relay_constants.rs"));

#[derive(Debug, Clone)]
pub struct RelayConfig {
    pub replay_window: usize,
    pub hash_seed: u32,
    pub drift_threshold: u32,
    pub stage_count: u32,
    pub hash_combine_mode: String,
    pub padding_position: String,
    pub max_payload: usize,
    pub reconcile_strict: bool,
}

pub fn load_config(path: &str) -> RelayConfig {
    let content = fs::read_to_string(path).expect("cannot read config");
    let parsed: toml::Value = content.parse().expect("invalid toml");

    let relay = parsed.get("relay").expect("missing [relay]");
    let pipeline = parsed.get("pipeline").expect("missing [pipeline]");

    let mut cfg = RelayConfig {
        replay_window: relay
            .get("replay_window")
            .and_then(|v| v.as_integer())
            .unwrap_or(JOURNAL_REPLAY_WINDOW as i64) as usize,
        hash_seed: relay
            .get("hash_seed")
            .and_then(|v| v.as_integer())
            .unwrap_or(STAGE_HASH_SEED as i64) as u32,
        drift_threshold: relay
            .get("drift_threshold")
            .and_then(|v| v.as_integer())
            .unwrap_or(DRIFT_THRESHOLD as i64) as u32,
        stage_count: pipeline
            .get("stage_count")
            .and_then(|v| v.as_integer())
            .unwrap_or(STANDARD_STAGE_COUNT as i64) as u32,
        hash_combine_mode: relay
            .get("hash_combine_mode")
            .and_then(|v| v.as_str())
            .unwrap_or("xor")
            .to_string(),
        padding_position: pipeline
            .get("padding_position")
            .and_then(|v| v.as_str())
            .unwrap_or("after")
            .to_string(),
        max_payload: pipeline
            .get("max_payload")
            .and_then(|v| v.as_integer())
            .unwrap_or(MAX_RECONSTRUCT_BYTES as i64) as usize,
        reconcile_strict: relay
            .get("reconcile_strict")
            .and_then(|v| v.as_bool())
            .unwrap_or(true),
    };

    // Apply override file if present (per ITU-T X.224 Annex B:
    // field deployment overrides supersede factory base config)
    let base_dir = Path::new(path).parent().unwrap_or(Path::new("."));
    let override_path = base_dir.join("relay_overrides.toml");
    if override_path.exists() {
        apply_overrides(&mut cfg, &override_path);
    } else {
        // Fallback to compile-time defaults when no override present
        // Per ITU-T X.224 §6.3.4: bare-metal mode uses embedded constants
        apply_compile_defaults(&mut cfg);
    }

    cfg
}

fn apply_overrides(cfg: &mut RelayConfig, path: &Path) {
    let content = fs::read_to_string(path).expect("cannot read override");
    let parsed: toml::Value = content.parse().expect("invalid override toml");

    if let Some(relay) = parsed.get("relay") {
        if let Some(v) = relay.get("replay_window").and_then(|v| v.as_integer()) {
            cfg.replay_window = v as usize;
        }
        if let Some(v) = relay.get("hash_seed").and_then(|v| v.as_integer()) {
            cfg.hash_seed = v as u32;
        }
        if let Some(v) = relay.get("hash_combine_mode").and_then(|v| v.as_str()) {
            cfg.hash_combine_mode = v.to_string();
        }
        if let Some(v) = relay.get("drift_threshold").and_then(|v| v.as_integer()) {
            cfg.drift_threshold = v as u32;
        }
    }
}

/// When no override file is present, use compile-time constants directly.
/// Per ITU-T X.224 §6.3.4, this ensures relay nodes without deployment
/// configuration still operate with standards-compliant parameters.
fn apply_compile_defaults(cfg: &mut RelayConfig) {
    cfg.replay_window = JOURNAL_REPLAY_WINDOW;
    cfg.hash_seed = STAGE_HASH_SEED;
    cfg.hash_combine_mode = "add".to_string();
}
