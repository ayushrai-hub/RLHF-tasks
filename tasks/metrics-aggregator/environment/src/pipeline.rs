use crate::types::{MetricPoint, MetricsConfig};

/// Apply the full pre-aggregation pipeline to raw metric points.
pub fn run_pipeline(
    points: Vec<MetricPoint>,
    config: &MetricsConfig,
) -> Vec<MetricPoint> {
    let mut result = points;

    if config.enable_windowing {
        result = apply_windowing(result, config.aggregation_window_secs);
    }

    if (config.calibration_factor - 1.0).abs() > f64::EPSILON {
        result = apply_calibration(result, config.calibration_factor);
    }

    result
}

fn apply_windowing(points: Vec<MetricPoint>, window_secs: u64) -> Vec<MetricPoint> {
    use std::collections::HashMap;

    let mut windows: HashMap<(String, u64), MetricPoint> = HashMap::new();

    for point in points {
        let ts = crate::reader::parse_timestamp(&point.timestamp).unwrap_or(0);
        let window_key = ts / window_secs;
        let key = (point.metric.clone(), window_key);
        windows.insert(key, point);
    }

    windows.into_values().collect()
}

fn apply_calibration(points: Vec<MetricPoint>, factor: f64) -> Vec<MetricPoint> {
    points
        .into_iter()
        .map(|mut p| {
            p.value *= factor;
            p
        })
        .collect()
}

#[allow(dead_code)]
pub fn validate_pipeline_output(points: &[MetricPoint]) -> bool {
    points.iter().all(|p| p.value.is_finite())
}
