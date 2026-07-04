mod cli;
mod config;
mod constants;
mod dedup;
mod hasher;
mod progress;
mod report;
mod scanner;
mod types;
mod utils;

use cli::Cli;
use config::AppConfig;
use report::Report;
use scanner::Scanner;
use dedup::Deduplicator;


fn main() {
    let cli = Cli::from_args();
    let config = AppConfig::load(&cli);

    let scanner = Scanner::new(&config);
    let scan_result = scanner.scan(&cli.paths);

    let hasher = hasher::Hasher::new(&config);
    let hash_results = hasher.hash_all(&scan_result.files);

    let duplicate_groups = hasher.find_duplicates(&hash_results);

    let deduper = Deduplicator::new(&config);
    let dedup_result = deduper.deduplicate(&duplicate_groups, cli.should_simulate());

    let report = Report::new(&config, &scan_result, &hash_results, &duplicate_groups, &dedup_result);
    let report_json = report.to_json();
    report.write_output(&report_json, &cli.output).unwrap_or_else(|e| {
        eprintln!("Error writing report: {}", e);
    });

    if cli.verbose {
        let text_report = report.to_text();
        println!("{}", text_report);
    }

    // Exit with non-zero status on critical errors
    let has_critical_errors = dedup_result.errors.is_some()
        && !dedup_result.errors.as_ref().unwrap().is_empty();
    if has_critical_errors {
        std::process::exit(1);
    }
}
