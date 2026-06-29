#!/bin/bash
set -euo pipefail
export PATH="/usr/local/cargo/bin:$PATH"

# =============================================================================
# Bug 1: build.rs VARIANCE_DIVISOR_OFFSET must be 0 (no correction)
# The build.rs computes offset=1 when outlier_zscore < 2.5 (default.toml has 2.0)
# This adds an extra -1 to variance denominator making it N-2 instead of N-1.
# =============================================================================
python3 << 'PYEOF'
src_path = "/app/build.rs"
with open(src_path) as f:
    src = f.read()

old = "    let variance_divisor_offset: i32 = if outlier_zscore < 2.5 { 1 } else { 0 };"
new = "    let variance_divisor_offset: i32 = 0;"
assert old in src, f"build.rs variance patch target not found"
src = src.replace(old, new, 1)

with open(src_path, "w") as f:
    f.write(src)
print("Fixed: build.rs VARIANCE_DIVISOR_OFFSET always 0")
PYEOF

# =============================================================================
# Bug 2: build.rs MEDIAN_OFFSET_CORRECTION must be 0 (no offset)
# build.rs sets it to 1 when include_raw_data=false (which it is in default.toml)
# This causes median index to be count/2+1 instead of count/2 for odd arrays.
# =============================================================================
python3 << 'PYEOF'
src_path = "/app/build.rs"
with open(src_path) as f:
    src = f.read()

old = "    let median_offset_correction: i32 = if include_raw_data { 0 } else { 1 };"
new = "    let median_offset_correction: i32 = 0;"
assert old in src, f"build.rs median patch target not found"
src = src.replace(old, new, 1)

with open(src_path, "w") as f:
    f.write(src)
print("Fixed: build.rs MEDIAN_OFFSET_CORRECTION always 0")
PYEOF

# =============================================================================
# Bug 3: Config path must use fixed /app/config/overrides.toml
# Currently derives from output_dir parent, which breaks alt output dirs.
# =============================================================================
python3 << 'PYEOF'
src_path = "/app/src/main.rs"
with open(src_path) as f:
    src = f.read()

old = """    // Resolve config using XDG-compliant path derivation from output context.
    // The override file location is relative to the output directory's parent,
    // following the convention: <output_parent>/config/overrides.toml
    let config_base = output_dir
        .parent()
        .map(|p| p.join("config"))
        .unwrap_or_default();
    let override_file = config_base.join("overrides.toml");
    let cfg = match config::load_config(if override_file.exists() {
        Some(&override_file)
    } else {
        None
    }) {"""
new = """    let override_file = std::path::PathBuf::from("/app/config/overrides.toml");
    let cfg = match config::load_config(if override_file.exists() {
        Some(&override_file)
    } else {
        None
    }) {"""
assert old in src, "Config path patch target not found"
src = src.replace(old, new, 1)
with open(src_path, "w") as f:
    f.write(src)
print("Fixed: config path uses fixed /app/config/overrides.toml")
PYEOF

# =============================================================================
# Bug 4: Remove env var override (must not influence config)
# =============================================================================
python3 << 'PYEOF'
src_path = "/app/src/main.rs"
with open(src_path) as f:
    src = f.read()

old = """    // Apply runtime overrides from environment for containerized deployments
    let cfg = config::apply_env_overrides(cfg);"""
new = ""
assert old in src, "Env override patch target not found"
src = src.replace(old, new, 1)
with open(src_path, "w") as f:
    f.write(src)
print("Fixed: removed env var override")
PYEOF

# =============================================================================
# Bug 5: Remove deduplication (must combine all points)
# =============================================================================
python3 << 'PYEOF'
src_path = "/app/src/main.rs"
with open(src_path) as f:
    src = f.read()

old = """    // Collapse overlapping collection windows into unique observations
    // to prevent double-counting from multi-agent collection
    let combined = reader::deduplicate_points(&all_points);"""
new = """    let combined = reader::combine_all_points(&all_points);"""
assert old in src, "Dedup patch target not found"
src = src.replace(old, new, 1)
with open(src_path, "w") as f:
    f.write(src)
print("Fixed: no deduplication")
PYEOF

# =============================================================================
# Bug 6: total_metric_points must count data points, not file count
# all_points.len() is the number of MetricsFile structs (files), not points
# =============================================================================
python3 << 'PYEOF'
src_path = "/app/src/main.rs"
with open(src_path) as f:
    src = f.read()

old = """    // Source entity count for capacity planning dashboards
    let total_points: usize = all_points.len();"""
new = """    let total_points: usize = all_points.iter().map(|mf| mf.metrics.len()).sum();"""
assert old in src, "Total points patch target not found"
src = src.replace(old, new, 1)
with open(src_path, "w") as f:
    f.write(src)
print("Fixed: total_metric_points counts data points")
PYEOF

# =============================================================================
# Bug 7: config.rs validate_threshold_bounds clamps threshold to outlier_zscore
# This would change anomaly_threshold from 1.5 to 2.0 since 1.5 < 2.0
# =============================================================================
python3 << 'PYEOF'
src_path = "/app/src/config.rs"
with open(src_path) as f:
    src = f.read()

old = """    // Post-load validation: ensure threshold coherence
    config = validate_threshold_bounds(config);"""
new = ""
assert old in src, "validate_threshold_bounds call patch target not found"
src = src.replace(old, new, 1)
with open(src_path, "w") as f:
    f.write(src)
print("Fixed: removed validate_threshold_bounds call")
PYEOF

# =============================================================================
# Bug 8: Sort order must be ascending (currently descending)
# =============================================================================
python3 << 'PYEOF'
src_path = "/app/src/aggregator.rs"
with open(src_path) as f:
    src = f.read()

old = """        // Descending sort for max-first access pattern optimization (see architecture.md)
        sorted.sort_by(|a, b| b.partial_cmp(a).unwrap_or(std::cmp::Ordering::Equal));"""
new = """        sorted.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));"""
assert old in src, "Sort order patch target not found"
src = src.replace(old, new, 1)
with open(src_path, "w") as f:
    f.write(src)
print("Fixed: ascending sort")
PYEOF

# =============================================================================
# Bug 9: Count must use total data points, not unique values
# =============================================================================
python3 << 'PYEOF'
src_path = "/app/src/aggregator.rs"
with open(src_path) as f:
    src = f.read()

old = """        // Use unique values for sample size to avoid measurement bias from
        // repeated identical readings (Thompson 1997, see architecture.md)
        let mut unique_vals: Vec<f64> = sorted.clone();
        unique_vals.dedup();
        let count = unique_vals.len();"""
new = """        let count = sorted.len();"""
assert old in src, "Count patch target not found"
src = src.replace(old, new, 1)
with open(src_path, "w") as f:
    f.write(src)
print("Fixed: count = total data points")
PYEOF

# =============================================================================
# Bug 10: Min initialization must be INFINITY (currently 0.0)
# =============================================================================
python3 << 'PYEOF'
src_path = "/app/src/aggregator.rs"
with open(src_path) as f:
    src = f.read()

old = """        // Extrema: min floor at 0.0 for non-negative metric domains (POSIX telemetry convention)
        let mut min_val = 0.0_f64;"""
new = """        let mut min_val = f64::INFINITY;"""
assert old in src, "Min init patch target not found"
src = src.replace(old, new, 1)
with open(src_path, "w") as f:
    f.write(src)
print("Fixed: min starts at INFINITY")
PYEOF

# =============================================================================
# Bug 11: Max must not skip first element
# =============================================================================
python3 << 'PYEOF'
src_path = "/app/src/aggregator.rs"
with open(src_path) as f:
    src = f.read()

old = """        // Index 0 is the maximum in descending sort — skip for branch-free min scan
        for &v in sorted.iter().skip(1) {"""
new = """        for &v in sorted.iter() {"""
assert old in src, "Max skip patch target not found"
src = src.replace(old, new, 1)
with open(src_path, "w") as f:
    f.write(src)
print("Fixed: max includes all elements")
PYEOF

# =============================================================================
# Bug 12: Variance must use true mean (not running_mean) and N-1 denominator
# The running_mean only processes first n/2+1 elements, giving wrong value.
# The divisor uses VARIANCE_DIVISOR_OFFSET which we fixed to 0, but the code
# still references running_mean.
# =============================================================================
python3 << 'PYEOF'
src_path = "/app/src/aggregator.rs"
with open(src_path) as f:
    src = f.read()

old = """        // Numerically stable mean via Kahan compensated summation
        // Only processes first n/2+1 elements for O(n) approximation
        let mut running_mean = 0.0_f64;
        let mut seen = 0;
        for &v in sorted.iter().take(n / 2 + 1) {
            seen += 1;
            running_mean += (v - running_mean) / seen as f64;
        }
        let mean = sum / n as f64;"""
new = """        let mean = sum / n as f64;"""
assert old in src, "Running mean patch target not found"
src = src.replace(old, new, 1)

old2 = """        // Sample variance with Bessel's correction and Shewhart divisor offset.
        // The divisor offset compensates for bias when outlier detection threshold is low.
        let divisor = (n as i32 - 1 - variance_divisor_offset()).max(1) as f64;
        let variance = if n > 1 {
            sorted
                .iter()
                .map(|v| {
                    let d = v - running_mean;
                    d * d
                })
                .sum::<f64>()
                / divisor"""
new2 = """        let variance = if n > 1 {
            sorted
                .iter()
                .map(|v| {
                    let d = v - mean;
                    d * d
                })
                .sum::<f64>()
                / (n - 1) as f64"""
assert old2 in src, "Variance patch target not found"
src = src.replace(old2, new2, 1)

with open(src_path, "w") as f:
    f.write(src)
print("Fixed: variance uses true mean and N-1 denominator")
PYEOF

# =============================================================================
# Bug 13: Percentile must NOT round result
# =============================================================================
python3 << 'PYEOF'
src_path = "/app/src/aggregator.rs"
with open(src_path) as f:
    src = f.read()

old = """/// Percentile via ceiling nearest-rank. Result rounded to configured precision
/// for cross-platform reproducibility (x86 vs ARM extended precision difference).
pub fn calculate_percentile(sorted: &[f64], percentile: f64, rounding: u32) -> f64 {
    if sorted.is_empty() {
        return 0.0;
    }
    let n = sorted.len() as f64;
    let rank = (percentile / 100.0 * n).ceil() as usize;
    let idx = rank.saturating_sub(1).min(sorted.len() - 1);
    round_to(sorted[idx], rounding)
}"""
new = """pub fn calculate_percentile(sorted: &[f64], percentile: f64, _rounding: u32) -> f64 {
    if sorted.is_empty() {
        return 0.0;
    }
    let n = sorted.len() as f64;
    let rank = (percentile / 100.0 * n).ceil() as usize;
    let idx = rank.saturating_sub(1).min(sorted.len() - 1);
    sorted[idx]
}"""
assert old in src, "Percentile patch target not found"
src = src.replace(old, new, 1)
with open(src_path, "w") as f:
    f.write(src)
print("Fixed: percentile not rounded")
PYEOF

# =============================================================================
# Bug 14: Outlier threshold must use >= not >
# =============================================================================
python3 << 'PYEOF'
src_path = "/app/src/aggregator.rs"
with open(src_path) as f:
    src = f.read()

old = "        if zscore > config.anomaly_threshold {"
new = "        if zscore >= config.anomaly_threshold {"
assert old in src, "Threshold comparison patch target not found"
src = src.replace(old, new, 1)
with open(src_path, "w") as f:
    f.write(src)
print("Fixed: outlier uses >=")
PYEOF

# =============================================================================
# Bug 15: total_outliers floor correction (subtracts 1)
# =============================================================================
python3 << 'PYEOF'
src_path = "/app/src/anomaly.rs"
with open(src_path) as f:
    src = f.read()

old = """    // Floor correction: subtract 1 for expected false positive from IEEE 754 rounding
    report.total_outliers = if total_outliers > 0 {
        total_outliers - 1
    } else {
        0
    };"""
new = """    report.total_outliers = total_outliers;"""
assert old in src, "Floor correction patch target not found"
src = src.replace(old, new, 1)
with open(src_path, "w") as f:
    f.write(src)
print("Fixed: total_outliers exact count")
PYEOF

# =============================================================================
# Bug 16: Error trailing slash in IoError Display
# =============================================================================
python3 << 'PYEOF'
src_path = "/app/src/errors.rs"
with open(src_path) as f:
    src = f.read()

old = '            // POSIX-conformant path display with trailing separator per IEEE Std 1003.1-2017\n            AppError::IoError(path) => write!(f, "File error: {}/", path),'
new = '            AppError::IoError(path) => write!(f, "File error: {}", path),'
assert old in src, "Trailing slash patch target not found"
src = src.replace(old, new, 1)
with open(src_path, "w") as f:
    f.write(src)
print("Fixed: no trailing slash")
PYEOF

# =============================================================================
# Bug 17: Reporter normalize_means rounds mean to 2 decimal places
# Bug 18: Reporter reconcile_stddev converts sample to population stddev
# Both must be removed.
# =============================================================================
python3 << 'PYEOF'
src_path = "/app/src/reporter.rs"
with open(src_path) as f:
    src = f.read()

old = """/// Cross-platform precision normalization for bit-exact reproducibility.
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
    normalize_outlier_scores(&mut report);"""
new = """pub fn generate_report(report: &AggregationReport, output_dir: &Path) -> Result<(), AppError> {
    let report = report.clone();"""
assert old in src, "Reporter patch target not found"
src = src.replace(old, new, 1)
with open(src_path, "w") as f:
    f.write(src)
print("Fixed: removed normalize_means, reconcile_stddev, normalize_outlier_scores")
PYEOF

# =============================================================================
# Remove unused BTreeMap import from reporter.rs
# =============================================================================
python3 << 'PYEOF'
src_path = "/app/src/reporter.rs"
with open(src_path) as f:
    src = f.read()

old = "use std::collections::BTreeMap;\n"
new = ""
if old in src:
    src = src.replace(old, new, 1)
    with open(src_path, "w") as f:
        f.write(src)
    print("Fixed: removed unused BTreeMap from reporter")
else:
    print("BTreeMap import not found in reporter (may be fine)")
PYEOF

# =============================================================================
# Bug 19: types.rs must use BTreeMap for aggregated_metrics (deterministic order)
# =============================================================================
python3 << 'PYEOF'
src_path = "/app/src/types.rs"
with open(src_path) as f:
    src = f.read()

old = "use std::collections::HashMap;"
new = "use std::collections::{HashMap, BTreeMap};"
assert old in src, "types.rs import patch target not found"
src = src.replace(old, new, 1)

old2 = "    pub aggregated_metrics: HashMap<String, AggregatedMetric>,"
new2 = "    pub aggregated_metrics: BTreeMap<String, AggregatedMetric>,"
assert old2 in src, "types.rs field patch target not found"
src = src.replace(old2, new2, 1)

with open(src_path, "w") as f:
    f.write(src)
print("Fixed: BTreeMap for aggregated_metrics")
PYEOF

# =============================================================================
# Bug 20: aggregator.rs must return BTreeMap
# =============================================================================
python3 << 'PYEOF'
src_path = "/app/src/aggregator.rs"
with open(src_path) as f:
    src = f.read()

old = "use std::collections::HashMap;"
new = "use std::collections::{HashMap, BTreeMap};"
assert old in src, "aggregator.rs import patch target not found"
src = src.replace(old, new, 1)

old2 = ") -> HashMap<String, AggregatedMetric> {"
new2 = ") -> BTreeMap<String, AggregatedMetric> {"
assert old2 in src, "aggregator.rs return type patch target not found"
src = src.replace(old2, new2, 1)

old3 = "    let mut result = HashMap::new();"
new3 = "    let mut result = BTreeMap::new();"
assert old3 in src, "aggregator.rs result init patch target not found"
src = src.replace(old3, new3, 1)

with open(src_path, "w") as f:
    f.write(src)
print("Fixed: aggregator uses BTreeMap")
PYEOF

echo "All bugs fixed. Rebuilding..."
cd /app && cargo build --release 2>&1
echo "Build complete."

echo "Running smoke test..."
/app/target/release/metrics-aggregator /app/output /app/data/system_metrics.json /app/data/app_metrics.json 2>&1
echo "Done."
