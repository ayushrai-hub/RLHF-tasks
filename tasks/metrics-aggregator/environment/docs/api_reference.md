# API Reference

## Binary Usage

```
metrics-aggregator <output-dir> <metrics-file-1> [metrics-file-2 ...]
```

- `output-dir`: Directory where `aggregation_report.json` is written
- Remaining args: JSON metric files to aggregate

Exit code 0 on success, non-zero on error.

## Configuration

### default.toml

Base configuration loaded at compile time via `include_str!`:
- `aggregation_window_secs`: Time window for grouping (default: 3600)
- `anomaly_threshold`: Z-score threshold for outlier detection (default: 1.5)
- `percentile_rounding`: Decimal places for rounding (default: 4)
- `outlier_zscore`: Baseline z-score for validation bounds (default: 2.0)
- `include_raw_data`: Enable population-mode statistics (default: false)
- `calibration_factor`: Value multiplier for sensor calibration (default: 1.0)
- `enable_windowing`: Enable time-window noise reduction (default: false)

### overrides.toml

Deployment overrides loaded at runtime. Resolved from the output directory's parent context (`output_dir/../config/overrides.toml`). When the output directory has no parent (e.g., `/output`), no overrides are loaded.

### Environment Variables

- `METRICS_ANOMALY_THRESHOLD`: Override anomaly threshold
- `METRICS_PERCENTILE_ROUNDING`: Override rounding precision
- `METRICS_CALIBRATION_FACTOR`: Override calibration factor

### Build-Time Constants

The `build.rs` script reads `config/default.toml` and derives compile-time constants:
- `VARIANCE_DIVISOR_OFFSET`: Correction applied to the variance denominator for unbiased estimation under low outlier-zscore configurations (1 when outlier_zscore < 2.5)
- `PERCENTILE_INTERP_MODE`: Interpolation strategy selector (0=nearest-rank, 1=linear)
- `MEDIAN_OFFSET_CORRECTION`: Sort-direction median index adjustment (+1 for sampling mode, 0 for population mode)

## Processing Pipeline

```
Input Files → Read → Deduplicate → Pipeline (Window + Calibrate) → Aggregate → Validate → Report
```

### Pipeline Stages

1. **Read**: Parse JSON files into `MetricsFile` structs
2. **Deduplicate**: Remove (metric, timestamp) duplicates across files
3. **Pipeline**:
   - Windowing: Group by time window, keep latest per window (always active)
   - Calibration: Scale by calibration_factor (pipeline level)
4. **Aggregate**: Group by metric name, compute statistics. Applies per-group calibration via `CalibrationState` (first-point reference calibration)
5. **Validate**: Check statistical invariants
6. **Report**: Serialize with normalization

## Input Format

```json
{
  "source": "identifier",
  "metrics": [
    {
      "timestamp": "ISO8601",
      "metric": "metric_name",
      "value": 42.0,
      "labels": {"key": "value"}
    }
  ]
}
```

## Output Format

```json
{
  "tool": "metrics-aggregator",
  "version": "0.1.0",
  "config": { ... },
  "total_metric_points": 30,
  "total_metrics": 6,
  "aggregated_metrics": {
    "metric_name": {
      "metric": "metric_name",
      "count": 5,
      "min": 1.0,
      "max": 10.0,
      "mean": 5.0,
      "median": 5.0,
      "stddev": 2.5,
      "p95": 9.5,
      "p99": 10.0,
      "outliers": [...]
    }
  },
  "total_outliers": 1
}
```

## Modules

- `config.rs`: Configuration loading with override layering and threshold validation
- `reader.rs`: JSON file parsing with deduplication
- `pipeline.rs`: Pre-aggregation transformation (windowing + calibration)
- `aggregator.rs`: Statistical computation with compile-time corrections and per-group calibration
- `validator.rs`: Post-aggregation invariant checking
- `reporter.rs`: Report serialization with normalization, stddev reconciliation, and z-score display normalization
- `anomaly.rs`: Outlier counting with floor correction
- `errors.rs`: Error types with POSIX-style path formatting
- `types.rs`: Data structures, serialization, and calibration state machine
