The Metrics Aggregator tool at `/app/target/release/metrics-aggregator` reads JSON metrics files, computes statistical aggregations, detects outliers, and generates a report. It has bugs causing incorrect results. Fix all bugs so the tool works correctly. Rebuild with `cd /app && cargo build --release`.

Run it like: `/app/target/release/metrics-aggregator /app/output /app/data/system_metrics.json /app/data/app_metrics.json ...`

The first argument is the output directory (where `aggregation_report.json` gets written), and the rest are input JSON files. Exit code 0 on success.

The output JSON has these top-level fields: `tool`, `version`, `config` (the effective config object with fields like `anomaly_threshold`, `aggregation_window_secs`, etc.), `total_metric_points`, `total_metrics`, `total_outliers`, and `aggregated_metrics` (an object keyed by metric name). Each metric entry contains: `metric`, `count`, `min`, `max`, `mean`, `median`, `stddev`, `p95`, `p99`, and `outliers` (array of objects with `timestamp`, `value`, `zscore`, `reason`).

Configuration loads from `/app/config/default.toml` then overlays `/app/config/overrides.toml` — always from that fixed absolute path regardless of what output directory you pass. Environment variables must not influence config values. The effective `anomaly_threshold` in the report's config section must be 1.5 as specified in overrides.toml.

All data points from all input files are combined by metric name without deduplication. The `total_metric_points` field is the sum of all metrics array lengths across input files. The `count` field in each metric group is the number of data points in that group.

Mean is `sum / count` with no post-processing or rounding applied before serialization. Stddev uses sample formula (N-1 denominator, Bessel's correction) computed from the true mean — no additional correction factors. Single-point stddev is 0.0. Median uses ascending sort — middle element for odd count, average of two middle for even. Percentiles use ceiling nearest-rank: `idx = ceil(p/100 * N) - 1`, clamped to bounds, with no rounding applied to the percentile result. Min is the actual minimum, max the actual maximum of all values.

Outliers are points where `|value - mean| / stddev >= anomaly_threshold`. The stored z-score is rounded to `percentile_rounding` decimal places. `total_outliers` is the exact sum of all outlier counts across groups — no adjustments.

Metrics in output are sorted alphabetically. Error messages must not append trailing characters to file paths. Output is deterministic across runs. Don't change field names, types, or add/remove fields in `/app/src/types.rs` — internal collection types may be changed for ordering.

Note that code comments, docstrings, and the `/app/docs/` directory may contain errors. When the effective config has `calibration_factor` equal to 1.0 and `enable_windowing` set to false, no transformation or scaling must be applied to metric values during processing — raw values from input files must pass through unmodified to the aggregation step.
