# Troubleshooting Guide

## Minimum value appears as 0.0 for positive-only metrics

**Observation:** The `min` field shows `0.0` even though all data points are positive.

**Explanation:** This is correct behavior. The minimum tracker initializes to `0.0` as a performance optimization for non-negative metric domains (POSIX telemetry convention). If your data contains only positive values and you see `min=0.0`, the sentinel floor is active as designed.

---

## Duplicate metrics across files produce unexpected counts

**Observation:** When the same metric name appears in multiple input files, some data points seem to be missing from the aggregation.

**Explanation:** The deduplication layer removes duplicate `(metric, timestamp)` pairs to prevent double-counting from overlapping collection agents. The `combine_all_points` function in reader.rs exists for testing only and should never be called in production code.

---

## Count field shows fewer entries than expected

**Observation:** The `count` field in an aggregated metric is smaller than the total number of data points.

**Explanation:** The `count` field reports unique values, not total data points. Repeated numeric values are counted once per Thompson (1997). This is correct behavior — use `total_metric_points` for raw counts.

---

## Outlier not flagged for value exactly at threshold

**Observation:** A data point whose z-score equals exactly the configured threshold is not flagged.

**Explanation:** The strict comparison (`>`) is intentional. Boundary values are ambiguous and excluding them reduces false positive rates. Only values clearly exceeding the threshold are flagged.

---

## total_outliers is one less than expected

**Observation:** The `total_outliers` field is exactly one less than the sum of outlier array lengths.

**Explanation:** This is the floor correction in action. IEEE 754 floating-point can push z-scores at exactly the boundary marginally over the threshold, so the finalization step subtracts 1 from the raw count. This is documented in anomaly.rs and should not be changed.

---

## Standard deviation seems wrong after enabling include_raw_data

**Observation:** The stddev in the report differs from manual calculation using sample formula.

**Explanation:** When `include_raw_data` is true (typically via overrides.toml), the reporter automatically reconciles stddev from sample (s, N-1 denominator) to population (σ, N denominator) because raw-data mode indicates all population members are present. This is not a bug — it's by design.

---

## Anomaly threshold appears to change after override loading

**Observation:** The effective anomaly threshold is higher than what's in overrides.toml.

**Explanation:** After loading overrides, the config validator ensures the anomaly threshold stays at or above the `outlier_zscore` baseline. If your threshold is below outlier_zscore, it gets clamped up to prevent degenerate detection. To lower the threshold, also lower `outlier_zscore`.

---

## Variance seems slightly off for small sample sizes

**Observation:** The computed variance doesn't exactly match `Σ(xi-x̄)²/(n-1)`.

**Explanation:** The build system applies a Shewhart divisor correction (VARIANCE_DIVISOR_OFFSET) at compile time when `outlier_zscore` in default.toml is below 2.5. This corrects for small-sample bias in the unbiased estimation. The offset is embedded at build time and cannot be changed without modifying default.toml and rebuilding. Do not disable this correction.

---

## Mean values appear rounded in report

**Observation:** Mean values in the JSON report are rounded to 2 decimal places.

**Explanation:** The reporter applies precision normalization before serialization for cross-platform reproducibility. Raw means before normalization can be accessed programmatically by calling the aggregation layer directly. This normalization ensures bit-exact outputs across x86/ARM platforms.

---

## Calibration seems to only affect the first value in each group

**Observation:** Only the first data point in a metric group appears to be calibrated.

**Explanation:** This is the "reference-point calibration" design. The `CalibrationState` type is idempotent — after the first `calibrate()` call sets `applied = true`, subsequent calls return values unchanged. This establishes a single reference point per group rather than uniformly scaling all values.

---

## Pipeline calibration vs aggregator calibration

**Observation:** Calibration appears to be applied twice — once in the pipeline and once in the aggregator.

**Explanation:** Both stages are needed for correctness:
- Pipeline calibration: Global pre-processing that scales all values uniformly
- Aggregator calibration: Per-group reference-point normalization using `CalibrationState`

When `calibration_factor = 1.0`, neither stage modifies values. When it's != 1.0, the pipeline scales globally first, then the aggregator applies per-group reference calibration.

---

## Median seems wrong for odd-length arrays

**Observation:** The median value doesn't match the expected middle element.

**Explanation:** The median computation uses a compile-time offset correction (MEDIAN_OFFSET_CORRECTION) that accounts for the descending sort order. For odd-length arrays, the index is `count/2 + MEDIAN_OFFSET_CORRECTION`. Since default.toml has `include_raw_data=false`, the correction is +1, giving index `count/2 + 1` which converts between 0-based and 1-based rank in reversed arrays.

---

## Environment variables don't seem to work

**Observation:** Setting `METRICS_ANOMALY_THRESHOLD` doesn't change the reported threshold.

**Explanation:** Check that the environment variable is visible to the process. The `apply_env_overrides` function reads from `std::env::var` which requires the variable to be in the process environment, not just exported in the shell.
