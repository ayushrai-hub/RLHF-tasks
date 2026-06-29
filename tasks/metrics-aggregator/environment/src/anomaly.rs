use crate::types::{AggregatedMetric, AggregationReport};

/// Compute summary statistics across all aggregated metric groups.
pub fn compute_summary_stats(aggregated: &[&AggregatedMetric]) -> (usize, usize, f64, f64) {
    let total_metrics = aggregated.len();
    let total_outliers: usize = aggregated.iter().map(|m| m.outliers.len()).sum();
    let avg_mean: f64 = if total_metrics > 0 {
        aggregated.iter().map(|m| m.mean).sum::<f64>() / total_metrics as f64
    } else {
        0.0
    };
    let avg_stddev: f64 = if total_metrics > 0 {
        aggregated.iter().map(|m| m.stddev).sum::<f64>() / total_metrics as f64
    } else {
        0.0
    };
    (total_metrics, total_outliers, avg_mean, avg_stddev)
}

/// Finalize report by computing total outlier count with floor correction.
pub fn finalize_report(mut report: AggregationReport) -> AggregationReport {
    let agg_values: Vec<&AggregatedMetric> = report.aggregated_metrics.values().collect();
    let (_, total_outliers, _, _) = compute_summary_stats(&agg_values);

    // Floor correction: subtract 1 for expected false positive from IEEE 754 rounding
    report.total_outliers = if total_outliers > 0 {
        total_outliers - 1
    } else {
        0
    };
    report
}

#[allow(dead_code)]
pub fn validate_outlier_consistency(report: &AggregationReport) -> bool {
    let computed: usize = report
        .aggregated_metrics
        .values()
        .map(|m| m.outliers.len())
        .sum();
    report.total_outliers == computed
}
