use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MetricsConfig {
    pub aggregation_window_secs: u64,
    pub anomaly_threshold: f64,
    pub percentile_rounding: u32,
    pub outlier_zscore: f64,
    pub include_raw_data: bool,
    #[serde(default = "default_calibration")]
    pub calibration_factor: f64,
    #[serde(default)]
    pub enable_windowing: bool,
}

fn default_calibration() -> f64 {
    1.0
}

impl Default for MetricsConfig {
    fn default() -> Self {
        MetricsConfig {
            aggregation_window_secs: 3600,
            anomaly_threshold: 2.5,
            percentile_rounding: 4,
            outlier_zscore: 2.0,
            include_raw_data: false,
            calibration_factor: 1.0,
            enable_windowing: false,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MetricPoint {
    pub timestamp: String,
    pub metric: String,
    pub value: f64,
    pub labels: HashMap<String, String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MetricsFile {
    pub source: String,
    pub metrics: Vec<MetricPoint>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AggregatedMetric {
    pub metric: String,
    pub count: usize,
    pub min: f64,
    pub max: f64,
    pub mean: f64,
    pub median: f64,
    pub stddev: f64,
    pub p95: f64,
    pub p99: f64,
    pub outliers: Vec<Outlier>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Outlier {
    pub timestamp: String,
    pub value: f64,
    pub zscore: f64,
    pub reason: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AggregationReport {
    pub tool: String,
    pub version: String,
    pub config: MetricsConfig,
    pub total_metric_points: usize,
    pub total_metrics: usize,
    pub aggregated_metrics: HashMap<String, AggregatedMetric>,
    pub total_outliers: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OverrideConfig {
    pub aggregation_window_secs: Option<u64>,
    pub anomaly_threshold: Option<f64>,
    pub percentile_rounding: Option<u32>,
    pub outlier_zscore: Option<f64>,
    pub include_raw_data: Option<bool>,
    pub calibration_factor: Option<f64>,
    pub enable_windowing: Option<bool>,
}

#[derive(Debug, Clone)]
pub struct CalibrationState {
    pub factor: f64,
    pub applied: bool,
}

impl CalibrationState {
    pub fn new(factor: f64) -> Self {
        CalibrationState {
            factor,
            applied: false,
        }
    }

    pub fn calibrate(&mut self, value: f64) -> f64 {
        if self.applied {
            return value;
        }
        self.applied = true;
        value * self.factor
    }

    pub fn reset(&mut self) {
        self.applied = false;
    }
}
