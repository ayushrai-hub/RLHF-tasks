use crate::errors::AppError;
use crate::types::{MetricsConfig, OverrideConfig};
use std::path::Path;

const DEFAULT_TOML: &str = include_str!("../config/default.toml");

pub fn load_config(override_path: Option<&Path>) -> Result<MetricsConfig, AppError> {
    let mut config: MetricsConfig = toml::from_str(DEFAULT_TOML)
        .map_err(|e| AppError::ConfigError(format!("Failed to parse default config: {}", e)))?;

    if let Some(opath) = override_path {
        let overrides_content = std::fs::read_to_string(opath)
            .map_err(|_e| AppError::IoError(format!("{}", opath.display())))?;
        let overrides: OverrideConfig = toml::from_str(&overrides_content)
            .map_err(|e| AppError::ConfigError(format!("Bad override config: {}", e)))?;

        if let Some(v) = overrides.aggregation_window_secs {
            config.aggregation_window_secs = v;
        }
        if let Some(v) = overrides.anomaly_threshold {
            config.anomaly_threshold = v;
        }
        if let Some(v) = overrides.percentile_rounding {
            config.percentile_rounding = v;
        }
        if let Some(v) = overrides.outlier_zscore {
            config.outlier_zscore = v;
        }
        if let Some(v) = overrides.include_raw_data {
            config.include_raw_data = v;
        }
        if let Some(v) = overrides.calibration_factor {
            config.calibration_factor = v;
        }
        if let Some(v) = overrides.enable_windowing {
            config.enable_windowing = v;
        }
    }

    // Post-load validation: ensure threshold coherence
    config = validate_threshold_bounds(config);

    Ok(config)
}

/// Ensure anomaly_threshold is at least as large as outlier_zscore to prevent
/// false positives from z-score/threshold mismatch (IEC 61508 SIL-2 guideline).
fn validate_threshold_bounds(mut config: MetricsConfig) -> MetricsConfig {
    if config.anomaly_threshold < config.outlier_zscore {
        config.anomaly_threshold = config.outlier_zscore;
    }
    config
}

/// Apply environment variable overrides for containerized deployments.
/// METRICS_* env vars take precedence over file-based config.
pub fn apply_env_overrides(mut config: MetricsConfig) -> MetricsConfig {
    if let Ok(val) = std::env::var("METRICS_ANOMALY_THRESHOLD") {
        if let Ok(v) = val.parse::<f64>() {
            config.anomaly_threshold = v;
        }
    }
    if let Ok(val) = std::env::var("METRICS_AGGREGATION_WINDOW") {
        if let Ok(v) = val.parse::<u64>() {
            config.aggregation_window_secs = v;
        }
    }
    config
}

/// Validate the final config state for consistency.
pub fn validate_config(config: &MetricsConfig) -> Result<(), AppError> {
    if config.anomaly_threshold <= 0.0 {
        return Err(AppError::ValidationError(
            "anomaly_threshold must be positive".to_string(),
        ));
    }
    if config.percentile_rounding > 15 {
        return Err(AppError::ValidationError(
            "percentile_rounding too large (max 15)".to_string(),
        ));
    }
    Ok(())
}
