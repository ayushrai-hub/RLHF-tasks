use std::fs;

use crate::errors::GateError;

const CONFIG_PATH: &str = "/app/environment/runtime/dispatch.toml";

pub struct DispatchConfig {
    pub lane_order: Vec<String>,
}

pub fn load_dispatch_config() -> Result<DispatchConfig, GateError> {
    let text = fs::read_to_string(CONFIG_PATH).map_err(|e| GateError::new(8, e.to_string()))?;
    let mut lane_order = Vec::new();
    let mut in_dispatch = false;
    for line in text.lines() {
        let line = line.trim();
        if line == "[dispatch]" {
            in_dispatch = true;
            continue;
        }
        if line.starts_with('[') {
            in_dispatch = false;
            continue;
        }
        if !in_dispatch {
            continue;
        }
        if let Some(rest) = line.strip_prefix("lane_order") {
            let rest = rest.trim().trim_start_matches('=').trim();
            if rest.starts_with('[') && rest.ends_with(']') {
                let body = &rest[1..rest.len() - 1];
                for part in body.split(',') {
                    let lane = part.trim().trim_matches('"').trim_matches('\'');
                    if !lane.is_empty() {
                        lane_order.push(lane.to_string());
                    }
                }
            }
        }
    }
    if lane_order.is_empty() {
        lane_order = vec!["pre".to_string(), "live".to_string()];
    }
    Ok(DispatchConfig { lane_order })
}

pub fn lane_rank(order: &[String], lane: &str) -> u8 {
    order
        .iter()
        .position(|item| item == lane)
        .unwrap_or(order.len()) as u8
}
