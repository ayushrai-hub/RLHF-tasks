use crate::types::{AggregationReport, MetricsConfig};

pub fn validate_report(report: &AggregationReport) -> Vec<String> {
    let mut warnings = Vec::new();

    for (name, metric) in &report.aggregated_metrics {
        if metric.min > metric.mean {
            warnings.push(format!("{}: min ({}) > mean ({})", name, metric.min, metric.mean));
        }
        if metric.mean > metric.max {
            warnings.push(format!("{}: mean ({}) > max ({})", name, metric.mean, metric.max));
        }
        if metric.stddev < 0.0 {
            warnings.push(format!("{}: negative stddev ({})", name, metric.stddev));
        }
        if metric.p95 > metric.p99 {
            warnings.push(format!("{}: p95 ({}) > p99 ({})", name, metric.p95, metric.p99));
        }
        if metric.count == 0 {
            warnings.push(format!("{}: zero count", name));
        }
    }

    warnings
}

#[allow(dead_code)]
pub fn validate_config_consistency(config: &MetricsConfig) -> bool {
    config.anomaly_threshold >= config.outlier_zscore
}
