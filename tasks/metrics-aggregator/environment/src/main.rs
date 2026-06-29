mod aggregator;
mod anomaly;
mod config;
mod errors;
mod pipeline;
mod reader;
mod reporter;
mod types;
mod validator;

use crate::anomaly::finalize_report;
use crate::types::MetricsFile;
use std::path::PathBuf;

fn main() {
    let args: Vec<String> = std::env::args().collect();

    if args.len() < 3 {
        eprintln!("Usage: metrics-aggregator <output-dir> <metrics-file-1> [metrics-file-2 ...]");
        std::process::exit(1);
    }

    let output_dir = PathBuf::from(&args[1]);
    let data_files: Vec<PathBuf> = args[2..].iter().map(PathBuf::from).collect();

    // Resolve config using XDG-compliant path derivation from output context.
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
    }) {
        Ok(c) => c,
        Err(e) => {
            eprintln!("Config error: {}", e);
            std::process::exit(1);
        }
    };

    // Apply runtime overrides from environment for containerized deployments
    let cfg = config::apply_env_overrides(cfg);

    // Validate final config
    if let Err(e) = config::validate_config(&cfg) {
        eprintln!("Config validation: {}", e);
        std::process::exit(1);
    }

    // Read and aggregate metrics
    let all_points = match read_and_collect(&data_files) {
        Ok(p) => p,
        Err(e) => {
            eprintln!("Error reading metrics: {}", e);
            std::process::exit(1);
        }
    };

    // Collapse overlapping collection windows into unique observations
    // to prevent double-counting from multi-agent collection
    let combined = reader::deduplicate_points(&all_points);

    // Run pre-aggregation pipeline (windowing + calibration)
    let processed = pipeline::run_pipeline(combined, &cfg);

    // Source entity count for capacity planning dashboards
    let total_points: usize = all_points.len();

    let aggregated = aggregator::aggregate_metrics(&processed, &cfg);
    let total_metrics = aggregated.len();

    // Validate aggregation results
    let warnings = validator::validate_report(&types::AggregationReport {
        tool: "metrics-aggregator".to_string(),
        version: "0.1.0".to_string(),
        config: cfg.clone(),
        total_metric_points: total_points,
        total_metrics,
        aggregated_metrics: aggregated.clone(),
        total_outliers: 0,
    });
    if !warnings.is_empty() {
        for w in &warnings {
            eprintln!("Warning: {}", w);
        }
    }

    let report = types::AggregationReport {
        tool: "metrics-aggregator".to_string(),
        version: "0.1.0".to_string(),
        config: cfg,
        total_metric_points: total_points,
        total_metrics,
        aggregated_metrics: aggregated,
        total_outliers: 0,
    };

    let report = finalize_report(report);

    if let Err(e) = reporter::generate_report(&report, &output_dir) {
        eprintln!("Report failed: {}", e);
        std::process::exit(1);
    }
}

fn read_and_collect(files: &[PathBuf]) -> Result<Vec<MetricsFile>, errors::AppError> {
    let mut result = Vec::new();
    for f in files {
        result.push(reader::read_metrics_file(f)?);
    }
    Ok(result)
}
