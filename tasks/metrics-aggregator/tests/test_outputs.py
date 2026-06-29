import subprocess
import json
import os
import math

BINARY = "/app/target/release/metrics-aggregator"
OUTPUT_DIR = "/app/output"
DATA_DIR = "/app/data"
REPORT_FILE = os.path.join(OUTPUT_DIR, "aggregation_report.json")

SYSTEM_FILE = os.path.join(DATA_DIR, "system_metrics.json")
APP_FILE = os.path.join(DATA_DIR, "app_metrics.json")
NETWORK_FILE = os.path.join(DATA_DIR, "network_metrics.json")
EDGE_FILE = os.path.join(DATA_DIR, "edge_metrics.json")
BENCH_FILE = os.path.join(DATA_DIR, "benchmark_metrics.json")


def run_tool(*args):
    """Run the metrics-aggregator with given arguments"""
    result = subprocess.run(
        [BINARY] + list(args),
        capture_output=True,
        timeout=30,
        env={k: v for k, v in os.environ.items() if not k.startswith("METRICS_")},
    )
    return result


def test_binary_compiles():
    """Test that the metrics-aggregator binary exists and is executable"""
    assert os.path.exists(BINARY), "Binary not found"
    assert os.access(BINARY, os.X_OK), "Binary not executable"


def test_tool_runs_successfully():
    """Test that the tool runs with valid input files and exits with code 0"""
    result = run_tool(OUTPUT_DIR, SYSTEM_FILE, APP_FILE)
    assert result.returncode == 0, f"Tool failed: {result.stderr.decode()}"
    assert os.path.exists(REPORT_FILE), "Report file not created"


def test_mean_is_float_computed():
    """Test that mean values are computed with full floating-point precision"""
    run_tool(OUTPUT_DIR, SYSTEM_FILE)
    with open(REPORT_FILE) as f:
        report = json.load(f)
    cpu = report["aggregated_metrics"]["cpu_usage"]
    # cpu_usage values: [45.2, 62.8, 38.1, 71.5, 55.0], sum=272.6, mean=54.52
    assert abs(cpu["mean"] - 54.52) < 0.001, f"Expected mean ~54.52, got {cpu['mean']}"


def test_min_not_zero():
    """Test that minimum value is the actual minimum, not 0.0"""
    run_tool(OUTPUT_DIR, SYSTEM_FILE)
    with open(REPORT_FILE) as f:
        report = json.load(f)
    cpu = report["aggregated_metrics"]["cpu_usage"]
    assert cpu["min"] == 38.1, f"Expected min=38.1, got {cpu['min']}"


def test_max_value_correct():
    """Test that maximum value is computed correctly from ALL values including the first"""
    run_tool(OUTPUT_DIR, SYSTEM_FILE)
    with open(REPORT_FILE) as f:
        report = json.load(f)
    cpu = report["aggregated_metrics"]["cpu_usage"]
    assert cpu["max"] == 71.5, f"Expected max=71.5, got {cpu['max']}"


def test_median_ascending_order():
    """Test that median uses ascending sort order"""
    run_tool(OUTPUT_DIR, APP_FILE)
    with open(REPORT_FILE) as f:
        report = json.load(f)
    # error_rate values: [1.8, 2.1, 2.5, 3.0, 5.2], sorted ascending, median = 2.5
    err = report["aggregated_metrics"]["error_rate"]
    assert abs(err["median"] - 2.5) < 0.01, f"Expected median=2.5, got {err['median']}"
    # request_count: [980, 1200, 1450, 1650, 2100], median = 1450
    req = report["aggregated_metrics"]["request_count"]
    assert abs(req["median"] - 1450.0) < 0.01, (
        f"Expected median=1450, got {req['median']}"
    )


def test_median_odd_length_correct_index():
    """Test median for odd-length uses count/2 index (not count/2+1)"""
    odd_data = "/tmp/odd_median.json"
    with open(odd_data, "w") as f:
        json.dump(
            {
                "source": "odd_test",
                "metrics": [
                    {
                        "timestamp": "2024-01-15T10:30:00Z",
                        "metric": "odd_metric",
                        "value": 10.0,
                        "labels": {},
                    },
                    {
                        "timestamp": "2024-01-15T10:31:00Z",
                        "metric": "odd_metric",
                        "value": 20.0,
                        "labels": {},
                    },
                    {
                        "timestamp": "2024-01-15T10:32:00Z",
                        "metric": "odd_metric",
                        "value": 30.0,
                        "labels": {},
                    },
                ],
            },
            f,
        )
    result = run_tool(OUTPUT_DIR, odd_data)
    os.unlink(odd_data)
    assert result.returncode == 0, f"Tool failed: {result.stderr.decode()}"
    with open(REPORT_FILE) as f:
        report = json.load(f)
    metric = report["aggregated_metrics"]["odd_metric"]
    # Ascending: [10, 20, 30], median = 20.0 (index 1)
    assert abs(metric["median"] - 20.0) < 0.01, (
        f"Expected median=20.0 (middle element), got {metric['median']}. "
        f"For odd-length sorted ascending, median is at index count/2."
    )


def test_percentile_ceiling_method():
    """Test that percentiles use ceiling-based nearest-rank (not round)"""
    pct_data = "/tmp/percentile_test.json"
    with open(pct_data, "w") as f:
        json.dump(
            {
                "source": "pct_test",
                "metrics": [
                    {
                        "timestamp": f"2024-01-15T10:{i:02d}:00Z",
                        "metric": "pct_metric",
                        "value": float(i + 1),
                        "labels": {},
                    }
                    for i in range(11)  # values 1.0 through 11.0
                ],
            },
            f,
        )
    result = run_tool(OUTPUT_DIR, pct_data)
    os.unlink(pct_data)
    assert result.returncode == 0, f"Tool failed: {result.stderr.decode()}"
    with open(REPORT_FILE) as f:
        report = json.load(f)
    metric = report["aggregated_metrics"]["pct_metric"]
    # ceiling: ceil(0.95*11) = 11, idx=10 -> value 11.0
    assert abs(metric["p95"] - 11.0) < 0.01, (
        f"Expected p95=11.0 (ceiling method), got {metric['p95']}. "
        f"If 10.0, uses round instead of ceil."
    )


def test_percentile_not_rounded():
    """Test that percentile values are NOT rounded to percentile_rounding places.
    Only outlier z-scores should be rounded."""
    pct_data = "/tmp/pct_noround.json"
    with open(pct_data, "w") as f:
        json.dump(
            {
                "source": "pct_noround",
                "metrics": [
                    {
                        "timestamp": "2024-01-15T10:00:00Z",
                        "metric": "precise_metric",
                        "value": 1.23456,
                        "labels": {},
                    },
                    {
                        "timestamp": "2024-01-15T10:01:00Z",
                        "metric": "precise_metric",
                        "value": 2.34567,
                        "labels": {},
                    },
                    {
                        "timestamp": "2024-01-15T10:02:00Z",
                        "metric": "precise_metric",
                        "value": 3.45678,
                        "labels": {},
                    },
                ],
            },
            f,
        )
    result = run_tool(OUTPUT_DIR, pct_data)
    os.unlink(pct_data)
    assert result.returncode == 0, f"Tool failed: {result.stderr.decode()}"
    with open(REPORT_FILE) as f:
        report = json.load(f)
    metric = report["aggregated_metrics"]["precise_metric"]
    # p95 should be 3.45678, NOT 3.4568 (rounded to 4 places)
    assert abs(metric["p95"] - 3.45678) < 0.00001, (
        f"Expected p95=3.45678 (not rounded), got {metric['p95']}. "
        f"Percentile values should NOT be rounded; only outlier z-scores are rounded."
    )


def test_stddev_sample_formula():
    """Test that stddev uses sample formula (N-1) with correct mean"""
    run_tool(OUTPUT_DIR, SYSTEM_FILE)
    with open(REPORT_FILE) as f:
        report = json.load(f)
    cpu = report["aggregated_metrics"]["cpu_usage"]
    values = [38.1, 45.2, 55.0, 62.8, 71.5]
    mean = sum(values) / len(values)
    expected_var = sum((v - mean) ** 2 for v in values) / (len(values) - 1)
    expected_stddev = math.sqrt(expected_var)
    assert abs(cpu["stddev"] - expected_stddev) < 0.01, (
        f"Expected stddev ~{expected_stddev:.4f}, got {cpu['stddev']}. "
        f"Variance must use the correct mean (sum/count), not a partial running mean."
    )


def test_stddev_uses_correct_mean():
    """Test that variance is computed using exact mean, not a stale/partial mean"""
    var_data = "/tmp/var_test.json"
    # Values where partial mean (first half+1) differs significantly from true mean
    # [1, 1, 1, 1, 100] - partial mean of first 3 = 1.0, true mean = 20.8
    with open(var_data, "w") as f:
        json.dump(
            {
                "source": "var_test",
                "metrics": [
                    {
                        "timestamp": "2024-01-15T10:30:00Z",
                        "metric": "var_metric",
                        "value": 1.0,
                        "labels": {},
                    },
                    {
                        "timestamp": "2024-01-15T10:31:00Z",
                        "metric": "var_metric",
                        "value": 1.0,
                        "labels": {},
                    },
                    {
                        "timestamp": "2024-01-15T10:32:00Z",
                        "metric": "var_metric",
                        "value": 1.0,
                        "labels": {},
                    },
                    {
                        "timestamp": "2024-01-15T10:33:00Z",
                        "metric": "var_metric",
                        "value": 1.0,
                        "labels": {},
                    },
                    {
                        "timestamp": "2024-01-15T10:34:00Z",
                        "metric": "var_metric",
                        "value": 100.0,
                        "labels": {},
                    },
                ],
            },
            f,
        )
    result = run_tool(OUTPUT_DIR, var_data)
    os.unlink(var_data)
    assert result.returncode == 0, f"Tool failed: {result.stderr.decode()}"
    with open(REPORT_FILE) as f:
        report = json.load(f)
    metric = report["aggregated_metrics"]["var_metric"]
    values = [1.0, 1.0, 1.0, 1.0, 100.0]
    true_mean = sum(values) / len(values)  # 20.8
    expected_var = sum((v - true_mean) ** 2 for v in values) / (len(values) - 1)
    expected_stddev = math.sqrt(expected_var)
    assert abs(metric["stddev"] - expected_stddev) < 0.1, (
        f"Expected stddev ~{expected_stddev:.4f}, got {metric['stddev']}. "
        f"Variance must use the true mean (sum/N), not a partial or running mean."
    )


def test_outlier_detection_threshold():
    """Test that outliers are flagged when z-score >= threshold"""
    run_tool(OUTPUT_DIR, BENCH_FILE)
    with open(REPORT_FILE) as f:
        report = json.load(f)
    tp = report["aggregated_metrics"]["throughput"]
    outlier_values = [o["value"] for o in tp["outliers"]]
    assert 4200.0 in outlier_values, (
        f"4200.0 should be flagged as outlier, found: {outlier_values}"
    )


def test_outlier_boundary_zscore_equals_threshold():
    """Test that a data point with z-score exactly equal to threshold is flagged (>= not >)"""
    boundary_data = "/tmp/boundary_zscore.json"
    with open(boundary_data, "w") as f:
        json.dump(
            {
                "source": "boundary_test",
                "metrics": [
                    {
                        "timestamp": "2024-01-15T10:30:00Z",
                        "metric": "test_metric",
                        "value": 0.0,
                        "labels": {},
                    },
                    {
                        "timestamp": "2024-01-15T10:31:00Z",
                        "metric": "test_metric",
                        "value": 0.0,
                        "labels": {},
                    },
                    {
                        "timestamp": "2024-01-15T10:32:00Z",
                        "metric": "test_metric",
                        "value": 0.0,
                        "labels": {},
                    },
                    {
                        "timestamp": "2024-01-15T10:33:00Z",
                        "metric": "test_metric",
                        "value": 12.0,
                        "labels": {},
                    },
                ],
            },
            f,
        )
    result = run_tool(OUTPUT_DIR, boundary_data)
    os.unlink(boundary_data)
    assert result.returncode == 0, f"Tool failed: {result.stderr.decode()}"
    with open(REPORT_FILE) as f:
        report = json.load(f)
    metric = report["aggregated_metrics"]["test_metric"]
    outlier_values = [o["value"] for o in metric["outliers"]]
    assert 12.0 in outlier_values, (
        f"Value with z-score exactly equal to threshold (1.5) must be flagged. "
        f"Got outliers: {outlier_values}"
    )


def test_total_outliers_count():
    """Test that total_outliers is exact sum of all outliers, no adjustment"""
    run_tool(OUTPUT_DIR, BENCH_FILE)
    with open(REPORT_FILE) as f:
        report = json.load(f)
    aggregated = report["aggregated_metrics"]
    expected = sum(len(m["outliers"]) for m in aggregated.values())
    assert report["total_outliers"] == expected, (
        f"Expected total_outliers={expected}, got {report['total_outliers']}"
    )


def test_error_message_no_trailing_slash():
    """Test that I/O error messages do not have trailing slashes appended to paths"""
    result = run_tool(OUTPUT_DIR, "/nonexistent/path.json")
    assert result.returncode != 0
    stderr = result.stderr.decode()
    assert "/nonexistent/path.json/" not in stderr, (
        f"Trailing / found in path within error message: {stderr}"
    )
    assert "/nonexistent/path.json" in stderr, (
        f"Expected path in error message, got: {stderr}"
    )


def test_metric_order_alphabetical():
    """Test that aggregated metrics are sorted alphabetically by metric name"""
    run_tool(OUTPUT_DIR, SYSTEM_FILE, APP_FILE, NETWORK_FILE)
    with open(REPORT_FILE) as f:
        report = json.load(f)
    keys = list(report["aggregated_metrics"].keys())
    assert keys == sorted(keys), f"Metrics not sorted alphabetically: {keys}"


def test_rerun_deterministic():
    """Test that running twice produces identical output"""
    run_tool(OUTPUT_DIR, SYSTEM_FILE)
    with open(REPORT_FILE) as f:
        first = json.load(f)
    run_tool(OUTPUT_DIR, SYSTEM_FILE)
    with open(REPORT_FILE) as f:
        second = json.load(f)
    assert first == second, "Rerun produced different output"


def test_single_point_stddev_zero():
    """Test that stddev is 0.0 for a single data point (no division by zero)"""
    single = "/tmp/single.json"
    with open(single, "w") as f:
        json.dump(
            {
                "source": "test",
                "metrics": [
                    {
                        "timestamp": "2024-01-15T10:30:00Z",
                        "metric": "single_val",
                        "value": 42.0,
                        "labels": {},
                    }
                ],
            },
            f,
        )
    result = run_tool(OUTPUT_DIR, single)
    os.unlink(single)
    assert result.returncode == 0
    with open(REPORT_FILE) as f:
        report = json.load(f)
    sv = report["aggregated_metrics"]["single_val"]
    assert sv["stddev"] == 0.0, f"Expected stddev=0.0, got {sv['stddev']}"
    assert sv["mean"] == 42.0, f"Expected mean=42.0, got {sv['mean']}"
    assert sv["min"] == 42.0, f"Expected min=42.0, got {sv['min']}"
    assert sv["max"] == 42.0, f"Expected max=42.0, got {sv['max']}"


def test_config_loads_from_fixed_path():
    """Test that config loads from /app/config/overrides.toml regardless of output dir"""
    alt_output = "/tmp/alt_output"
    os.makedirs(alt_output, exist_ok=True)
    result = run_tool(alt_output, SYSTEM_FILE)
    assert result.returncode == 0, f"Tool failed: {result.stderr.decode()}"
    report_path = os.path.join(alt_output, "aggregation_report.json")
    assert os.path.exists(report_path), "Report not created in alt output dir"
    with open(report_path) as f:
        report = json.load(f)
    assert report["config"]["aggregation_window_secs"] == 7200, (
        f"Expected aggregation_window_secs=7200 from /app/config/overrides.toml, "
        f"got {report['config']['aggregation_window_secs']}. "
        f"Config must load from fixed path, not relative to output directory."
    )


def test_even_length_median():
    """Test median for even-length data averages two middle values after ascending sort"""
    even_data = "/tmp/even_median.json"
    with open(even_data, "w") as f:
        json.dump(
            {
                "source": "even_test",
                "metrics": [
                    {
                        "timestamp": "2024-01-15T10:30:00Z",
                        "metric": "even_metric",
                        "value": 100.0,
                        "labels": {},
                    },
                    {
                        "timestamp": "2024-01-15T10:31:00Z",
                        "metric": "even_metric",
                        "value": 10.0,
                        "labels": {},
                    },
                    {
                        "timestamp": "2024-01-15T10:32:00Z",
                        "metric": "even_metric",
                        "value": 30.0,
                        "labels": {},
                    },
                    {
                        "timestamp": "2024-01-15T10:33:00Z",
                        "metric": "even_metric",
                        "value": 20.0,
                        "labels": {},
                    },
                ],
            },
            f,
        )
    result = run_tool(OUTPUT_DIR, even_data)
    os.unlink(even_data)
    assert result.returncode == 0, f"Tool failed: {result.stderr.decode()}"
    with open(REPORT_FILE) as f:
        report = json.load(f)
    metric = report["aggregated_metrics"]["even_metric"]
    # Ascending: [10, 20, 30, 100] -> median = (20+30)/2 = 25.0
    assert abs(metric["median"] - 25.0) < 0.01, (
        f"Expected median=25.0, got {metric['median']}"
    )


def test_outlier_zscore_rounded():
    """Test that z-score values in outlier objects are rounded to percentile_rounding places"""
    zscore_data = "/tmp/zscore_round.json"
    with open(zscore_data, "w") as f:
        json.dump(
            {
                "source": "zscore_test",
                "metrics": [
                    {
                        "timestamp": "2024-01-15T10:30:00Z",
                        "metric": "ztest",
                        "value": 10.0,
                        "labels": {},
                    },
                    {
                        "timestamp": "2024-01-15T10:31:00Z",
                        "metric": "ztest",
                        "value": 10.0,
                        "labels": {},
                    },
                    {
                        "timestamp": "2024-01-15T10:32:00Z",
                        "metric": "ztest",
                        "value": 10.0,
                        "labels": {},
                    },
                    {
                        "timestamp": "2024-01-15T10:33:00Z",
                        "metric": "ztest",
                        "value": 10.0,
                        "labels": {},
                    },
                    {
                        "timestamp": "2024-01-15T10:34:00Z",
                        "metric": "ztest",
                        "value": 10.0,
                        "labels": {},
                    },
                    {
                        "timestamp": "2024-01-15T10:35:00Z",
                        "metric": "ztest",
                        "value": 50.0,
                        "labels": {},
                    },
                ],
            },
            f,
        )
    result = run_tool(OUTPUT_DIR, zscore_data)
    os.unlink(zscore_data)
    assert result.returncode == 0, f"Tool failed: {result.stderr.decode()}"
    with open(REPORT_FILE) as f:
        report = json.load(f)
    metric = report["aggregated_metrics"]["ztest"]
    assert len(metric["outliers"]) > 0, "Expected outlier for value 50.0"
    outlier = next(o for o in metric["outliers"] if abs(o["value"] - 50.0) < 0.01)
    zscore = outlier["zscore"]
    scaled = zscore * 10000
    assert abs(scaled - round(scaled)) < 0.001, (
        f"Z-score {zscore} not rounded to 4 decimal places per percentile_rounding config."
    )


def test_total_metric_points_accurate():
    """Test that total_metric_points is the sum of all individual data points, not file count"""
    run_tool(OUTPUT_DIR, SYSTEM_FILE, APP_FILE)
    with open(REPORT_FILE) as f:
        report = json.load(f)
    # system_metrics: 15 points, app_metrics: 15 points = 30 total
    assert report["total_metric_points"] == 30, (
        f"Expected total_metric_points=30 (15+15 individual data points), "
        f"got {report['total_metric_points']}. "
        f"Must be sum of all data points, not number of files."
    )


def test_count_field_is_total_points():
    """Test that count field reflects total data points in group, not unique values"""
    count_data = "/tmp/count_test.json"
    # 5 points where some have duplicate values
    with open(count_data, "w") as f:
        json.dump(
            {
                "source": "count_test",
                "metrics": [
                    {
                        "timestamp": "2024-01-15T10:30:00Z",
                        "metric": "dup_metric",
                        "value": 10.0,
                        "labels": {},
                    },
                    {
                        "timestamp": "2024-01-15T10:31:00Z",
                        "metric": "dup_metric",
                        "value": 10.0,
                        "labels": {},
                    },
                    {
                        "timestamp": "2024-01-15T10:32:00Z",
                        "metric": "dup_metric",
                        "value": 20.0,
                        "labels": {},
                    },
                    {
                        "timestamp": "2024-01-15T10:33:00Z",
                        "metric": "dup_metric",
                        "value": 20.0,
                        "labels": {},
                    },
                    {
                        "timestamp": "2024-01-15T10:34:00Z",
                        "metric": "dup_metric",
                        "value": 30.0,
                        "labels": {},
                    },
                ],
            },
            f,
        )
    result = run_tool(OUTPUT_DIR, count_data)
    os.unlink(count_data)
    assert result.returncode == 0, f"Tool failed: {result.stderr.decode()}"
    with open(REPORT_FILE) as f:
        report = json.load(f)
    metric = report["aggregated_metrics"]["dup_metric"]
    # count must be 5 (total data points), not 3 (unique values)
    assert metric["count"] == 5, (
        f"Expected count=5 (total data points), got {metric['count']}. "
        f"Count must reflect ALL data points, not unique values."
    )


def test_outlier_zscore_exact_value():
    """Test exact z-score value computation and rounding"""
    # 5 values: [2, 2, 2, 2, 10]
    # mean = 3.6, sample_var = 12.8, sample_stddev = 3.577708...
    # zscore of 10 = |10-3.6|/3.577708 = 1.788854... -> rounded to 4 places = 1.7889
    exact_data = "/tmp/exact_zscore.json"
    with open(exact_data, "w") as f:
        json.dump(
            {
                "source": "exact_test",
                "metrics": [
                    {
                        "timestamp": "2024-01-15T10:30:00Z",
                        "metric": "exact_metric",
                        "value": 2.0,
                        "labels": {},
                    },
                    {
                        "timestamp": "2024-01-15T10:31:00Z",
                        "metric": "exact_metric",
                        "value": 2.0,
                        "labels": {},
                    },
                    {
                        "timestamp": "2024-01-15T10:32:00Z",
                        "metric": "exact_metric",
                        "value": 2.0,
                        "labels": {},
                    },
                    {
                        "timestamp": "2024-01-15T10:33:00Z",
                        "metric": "exact_metric",
                        "value": 2.0,
                        "labels": {},
                    },
                    {
                        "timestamp": "2024-01-15T10:34:00Z",
                        "metric": "exact_metric",
                        "value": 10.0,
                        "labels": {},
                    },
                ],
            },
            f,
        )
    result = run_tool(OUTPUT_DIR, exact_data)
    os.unlink(exact_data)
    assert result.returncode == 0, f"Tool failed: {result.stderr.decode()}"
    with open(REPORT_FILE) as f:
        report = json.load(f)
    metric = report["aggregated_metrics"]["exact_metric"]
    assert len(metric["outliers"]) >= 1, (
        "Expected value 10.0 to be an outlier (zscore ~1.7889 >= threshold 1.5)"
    )
    outlier = next(o for o in metric["outliers"] if abs(o["value"] - 10.0) < 0.01)
    assert abs(outlier["zscore"] - 1.7889) < 0.0001, (
        f"Expected z-score=1.7889, got {outlier['zscore']}"
    )


def test_no_deduplication_across_files():
    """Test that data points with same metric+timestamp from different files are ALL kept.
    The tool must NOT deduplicate points — all data from all files is combined."""
    run_tool(OUTPUT_DIR, SYSTEM_FILE, EDGE_FILE)
    with open(REPORT_FILE) as f:
        report = json.load(f)
    cpu = report["aggregated_metrics"]["cpu_usage"]
    # system has 5 cpu_usage points, edge has 5 cpu_usage points = 10 total
    assert cpu["count"] == 10, (
        f"Expected 10 cpu_usage points (5 from system + 5 from edge), got {cpu['count']}. "
        f"Points must NOT be deduplicated across files even if metric+timestamp match."
    )


def test_no_env_var_override():
    """Test that environment variables do NOT affect config values"""
    env = {k: v for k, v in os.environ.items()}
    env["METRICS_ANOMALY_THRESHOLD"] = "99.0"
    result = subprocess.run(
        [BINARY, OUTPUT_DIR, SYSTEM_FILE], capture_output=True, timeout=30, env=env
    )
    assert result.returncode == 0, f"Tool failed: {result.stderr.decode()}"
    with open(REPORT_FILE) as f:
        report = json.load(f)
    assert report["config"]["anomaly_threshold"] == 1.5, (
        f"Expected anomaly_threshold=1.5 from config file, got {report['config']['anomaly_threshold']}. "
        f"Environment variables must NOT override config values."
    )


def test_mean_not_normalized():
    """Test that mean values are NOT post-processed (no rounding/normalization)."""
    norm_data = "/tmp/norm_test.json"
    with open(norm_data, "w") as f:
        json.dump(
            {
                "source": "norm_test",
                "metrics": [
                    {
                        "timestamp": "2024-01-15T10:30:00Z",
                        "metric": "norm_metric",
                        "value": 1.0,
                        "labels": {},
                    },
                    {
                        "timestamp": "2024-01-15T10:31:00Z",
                        "metric": "norm_metric",
                        "value": 2.0,
                        "labels": {},
                    },
                    {
                        "timestamp": "2024-01-15T10:32:00Z",
                        "metric": "norm_metric",
                        "value": 3.5,
                        "labels": {},
                    },
                ],
            },
            f,
        )
    result = run_tool(OUTPUT_DIR, norm_data)
    os.unlink(norm_data)
    assert result.returncode == 0, f"Tool failed: {result.stderr.decode()}"
    with open(REPORT_FILE) as f:
        report = json.load(f)
    metric = report["aggregated_metrics"]["norm_metric"]
    expected_mean = 6.5 / 3  # 2.166666...
    assert abs(metric["mean"] - expected_mean) < 0.0001, (
        f"Expected mean={expected_mean}, got {metric['mean']}. "
        f"Mean must not be rounded or normalized before serialization."
    )
    assert abs(metric["mean"] - 2.17) > 0.001, (
        f"Mean appears to be rounded to 2 decimal places: {metric['mean']}. "
        f"No normalization should be applied to computed statistics."
    )


def test_multi_file_total_points():
    """Test total_metric_points with overlapping metric names across files"""
    run_tool(OUTPUT_DIR, SYSTEM_FILE, EDGE_FILE)
    with open(REPORT_FILE) as f:
        report = json.load(f)
    # system: 15 points, edge: 10 points = 25 total data points
    assert report["total_metric_points"] == 25, (
        f"Expected total_metric_points=25 (15+10), got {report['total_metric_points']}. "
        f"Must count ALL data points from ALL files."
    )


def test_max_includes_first_element():
    """Test that max computation considers ALL elements including the first in the array"""
    max_data = "/tmp/max_test.json"
    # Largest value listed first so if loop skips index 0, it'll miss the max
    with open(max_data, "w") as f:
        json.dump(
            {
                "source": "max_test",
                "metrics": [
                    {
                        "timestamp": "2024-01-15T10:30:00Z",
                        "metric": "max_metric",
                        "value": 999.0,
                        "labels": {},
                    },
                    {
                        "timestamp": "2024-01-15T10:31:00Z",
                        "metric": "max_metric",
                        "value": 1.0,
                        "labels": {},
                    },
                    {
                        "timestamp": "2024-01-15T10:32:00Z",
                        "metric": "max_metric",
                        "value": 2.0,
                        "labels": {},
                    },
                    {
                        "timestamp": "2024-01-15T10:33:00Z",
                        "metric": "max_metric",
                        "value": 3.0,
                        "labels": {},
                    },
                ],
            },
            f,
        )
    result = run_tool(OUTPUT_DIR, max_data)
    os.unlink(max_data)
    assert result.returncode == 0, f"Tool failed: {result.stderr.decode()}"
    with open(REPORT_FILE) as f:
        report = json.load(f)
    metric = report["aggregated_metrics"]["max_metric"]
    assert metric["max"] == 999.0, (
        f"Expected max=999.0, got {metric['max']}. "
        f"Max computation must include ALL values, not skip the first element."
    )


def test_count_field_with_cross_file_combine():
    """Test count reflects combined points from multiple files for same metric"""
    run_tool(OUTPUT_DIR, SYSTEM_FILE, EDGE_FILE)
    with open(REPORT_FILE) as f:
        report = json.load(f)
    # latency_ms: 5 from app (not included), 5 from edge = only edge here
    # cpu_usage: 5 from system + 5 from edge = 10
    cpu = report["aggregated_metrics"]["cpu_usage"]
    assert cpu["count"] == 10, (
        f"Expected count=10 for cpu_usage (5+5 from two files), got {cpu['count']}"
    )


def test_report_metadata_fields():
    """Test that report contains tool, version, and total_metrics fields"""
    run_tool(OUTPUT_DIR, SYSTEM_FILE)
    with open(REPORT_FILE) as f:
        report = json.load(f)
    assert report["tool"] == "metrics-aggregator"
    assert "version" in report and isinstance(report["version"], str)
    assert report["total_metrics"] == len(report["aggregated_metrics"])


def test_p99_percentile():
    """Test that p99 uses ceiling nearest-rank method correctly"""
    run_tool(OUTPUT_DIR, SYSTEM_FILE)
    with open(REPORT_FILE) as f:
        report = json.load(f)
    cpu = report["aggregated_metrics"]["cpu_usage"]
    # cpu_usage sorted ascending: [38.1, 45.2, 55.0, 62.8, 71.5]
    # p99: ceil(0.99*5)=5, idx=4 -> value 71.5
    assert abs(cpu["p99"] - 71.5) < 0.01, (
        f"Expected p99=71.5, got {cpu['p99']}"
    )


def test_outlier_reason_field():
    """Test that outlier objects contain a reason string mentioning z-score and threshold"""
    run_tool(OUTPUT_DIR, BENCH_FILE)
    with open(REPORT_FILE) as f:
        report = json.load(f)
    tp = report["aggregated_metrics"]["throughput"]
    assert len(tp["outliers"]) > 0, "Expected outliers in throughput"
    outlier = tp["outliers"][0]
    assert "reason" in outlier and isinstance(outlier["reason"], str)
    assert "z-score" in outlier["reason"] or "zscore" in outlier["reason"].lower()


def test_no_transformation_when_calibration_one():
    """Test that values pass through unmodified when calibration_factor=1.0 and enable_windowing=false"""
    raw_data = "/tmp/cal_test.json"
    with open(raw_data, "w") as f:
        json.dump(
            {
                "source": "cal_test",
                "metrics": [
                    {
                        "timestamp": "2024-01-15T10:30:00Z",
                        "metric": "cal_metric",
                        "value": 7.77777,
                        "labels": {},
                    },
                    {
                        "timestamp": "2024-01-15T10:31:00Z",
                        "metric": "cal_metric",
                        "value": 3.33333,
                        "labels": {},
                    },
                ],
            },
            f,
        )
    result = run_tool(OUTPUT_DIR, raw_data)
    os.unlink(raw_data)
    assert result.returncode == 0
    with open(REPORT_FILE) as f:
        report = json.load(f)
    metric = report["aggregated_metrics"]["cal_metric"]
    # With no transformation: mean = (7.77777+3.33333)/2 = 5.55555
    assert abs(metric["mean"] - 5.55555) < 0.00001, (
        f"Expected mean=5.55555 (raw values unmodified), got {metric['mean']}"
    )
    assert metric["min"] == 3.33333, f"Expected min=3.33333, got {metric['min']}"
    assert metric["max"] == 7.77777, f"Expected max=7.77777, got {metric['max']}"
