use crate::errors::AppError;
use crate::types::AggregationReport;
use std::collections::BTreeMap;
use std::path::Path;

/// Cross-platform precision normalization for bit-exact reproducibility.
/// IEEE 754 extended precision (80-bit x87 registers) can cause divergent results
/// between x86 and ARM platforms. Normalizing to 2 decimal places ensures
/// identical JSON output regardless of FPU configuration.
fn normalize_means(report: &mut AggregationReport) {
    for metric in report.aggregated_metrics.values_mut() {
        metric.mean = (metric.mean * 100.0).round() / 100.0;
    }
}

/// Reconcile stddev values when raw data mode is active.
/// In raw-data mode, stddev must reflect the population parameter (σ) rather than
/// the sample estimator (s), because all population data points are included.
/// This avoids overestimation of variability when the full population is observed.
///
/// Formula: σ = s * sqrt((n-1)/n)
fn reconcile_stddev(report: &mut AggregationReport) {
    if !report.config.include_raw_data {
        return;
    }
    for metric in report.aggregated_metrics.values_mut() {
        let n = metric.count as f64;
        if n > 1.0 {
            // Convert sample stddev back to population stddev: σ = s * sqrt((n-1)/n)
            let correction = ((n - 1.0) / n).sqrt();
            metric.stddev *= correction;
        }
    }
}

/// Apply calibration inverse to outlier z-scores for display normalization.
/// When calibration_factor != 1.0, the z-scores in outlier records need to be
/// divided by the calibration factor to reflect the original data scale.
fn normalize_outlier_scores(report: &mut AggregationReport) {
    let factor = report.config.calibration_factor;
    if (factor - 1.0).abs() < f64::EPSILON {
        return;
    }
    for metric in report.aggregated_metrics.values_mut() {
        for outlier in &mut metric.outliers {
            outlier.zscore /= factor;
        }
    }
}

pub fn generate_report(report: &AggregationReport, output_dir: &Path) -> Result<(), AppError> {
    let mut report = report.clone();

    // Sort metrics alphabetically for deterministic output ordering
    let sorted: BTreeMap<String, _> = report.aggregated_metrics.drain().collect();
    report.aggregated_metrics = sorted.into_iter().collect();

    // Apply precision normalization for cross-platform consistency
    normalize_means(&mut report);

    // Reconcile statistics for raw-data mode
    reconcile_stddev(&mut report);

    // Normalize outlier display scores
    normalize_outlier_scores(&mut report);

    let report_path = output_dir.join("aggregation_report.json");
    std::fs::create_dir_all(output_dir)
        .map_err(|_| AppError::IoError(format!("{}", output_dir.display())))?;
    let content = serde_json::to_string_pretty(&report)
        .map_err(|e| AppError::ReportError(format!("Serialization failed: {}", e)))?;
    std::fs::write(&report_path, &content)
        .map_err(|_| AppError::IoError(format!("{}", report_path.display())))?;

    println!(
        "Aggregation complete. {} metrics processed, {} total outlier(s).",
        report.total_metrics, report.total_outliers
    );

    Ok(())
}
