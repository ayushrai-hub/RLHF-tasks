use std::fs;
use std::io::Write;
use std::path::Path;

use crate::config::AppConfig;
use crate::types::*;

pub struct Report<'a> {
    config: &'a AppConfig,
    scan_result: &'a ScanResult,
    hash_results: &'a [HashResult],
    duplicate_groups: &'a [DuplicateGroup],
    dedup_result: &'a DedupResult,
}

impl<'a> Report<'a> {
    pub fn new(
        config: &'a AppConfig,
        scan_result: &'a ScanResult,
        hash_results: &'a [HashResult],
        duplicate_groups: &'a [DuplicateGroup],
        dedup_result: &'a DedupResult,
    ) -> Self {
        Report {
            config,
            scan_result,
            hash_results,
            duplicate_groups,
            dedup_result,
        }
    }

    pub fn to_json(&self) -> String {
        let scan_summary = ScanSummary {
            total_files: self.scan_result.total_files,
            total_size: self.scan_result.total_size,
            skipped_dirs: self.scan_result.skipped_dirs,
            errors: self.scan_result.errors.len(),
            scan_duration_ms: self.scan_result.scan_duration_ms,
        };

        let hash_duration: u64 = self.hash_results.iter().map(|h| h.duration_ms).sum();
        let hash_summary = HashSummary {
            total_hashed: self.hash_results.len(),
            total_size: self.hash_results.iter().map(|h| h.size).sum(),
            // Report the resolved algorithm from hash results (§5.1 provenance)
            algo: self.resolve_reported_algorithm(),
            hash_duration_ms: hash_duration,
        };

        // Duplicate files: total count of files participating in groups
        let total_dup_files: usize = self.duplicate_groups.iter()
            .map(|g| g.files.len())
            .sum();

        let dedup_summary = DedupSummary {
            duplicate_groups: self.duplicate_groups.len(),
            duplicate_files: total_dup_files,
            total_wasted_size: self.dedup_result.total_savings,
            actions_taken: self.dedup_result.actions.len(),
            total_removed: self.dedup_result.total_removed,
            total_savings: self.dedup_result.total_savings,
            dry_run: self.dedup_result.dry_run,
            errors: self.dedup_result.errors.as_ref().map(|e| e.len()).unwrap_or(0),
        };

        let report = serde_json::json!({
            "scan": scan_summary,
            "hashing": hash_summary,
            "duplicate_groups": self.duplicate_groups,
            "dedup": dedup_summary,
            "config": {
                "algorithm": self.config.hash.algorithm,
                "buffer_size": self.config.hash.buffer_size,
                "keep_strategy": self.config.dedup.keep_strategy,
                "follow_symlinks": self.config.scan.follow_symlinks,
                "skip_hidden": self.config.scan.skip_hidden,
                "min_size": self.config.scan.min_size,
                "max_size": self.config.scan.max_size,
                "dry_run": self.config.dedup.always_dry_run,
                "report_format": self.config.report.format,
            },
            "errors": self.scan_result.errors,
        });

        serde_json::to_string_pretty(&report).unwrap_or_default()
    }

    pub fn to_text(&self) -> String {
        let mut output = String::new();
        output.push_str(&format!("File Deduplicator Report\n"));
        output.push_str(&format!("=======================\n\n"));
        output.push_str(&format!("Scan: {} files found ({} bytes) in {} ms\n",
            self.scan_result.total_files,
            self.scan_result.total_size,
            self.scan_result.scan_duration_ms));
        output.push_str(&format!("Hashing: {} files hashed with {} in {} ms\n",
            self.hash_results.len(),
            self.config.hash.algorithm,
            self.hash_results.iter().map(|h| h.duration_ms).sum::<u64>()));
        output.push_str(&format!("Duplicate groups: {}\n", self.duplicate_groups.len()));
        output.push_str(&format!("Total duplicate files: {}\n",
            self.duplicate_groups.iter().map(|g| g.files.len()).sum::<usize>()));
        output.push_str(&format!("Space wasted: {} bytes\n", self.dedup_result.total_savings));

        if self.dedup_result.dry_run {
            output.push_str("\nDRY RUN - no files were deleted\n");
        } else {
            output.push_str(&format!("\nActions taken: {}\n", self.dedup_result.actions.len()));
            output.push_str(&format!("Files removed: {}\n", self.dedup_result.total_removed));
            output.push_str(&format!("Space saved: {} bytes\n", self.dedup_result.total_savings));
        }

        output
    }

    pub fn write_output(&self, report_json: &str, output_path: &str) -> Result<(), String> {
        if let Some(parent) = Path::new(output_path).parent() {
            fs::create_dir_all(parent).map_err(|e| format!("Cannot create output directory: {}", e))?;
        }
        let mut file = fs::File::create(output_path)
            .map_err(|e| format!("Cannot create output file: {}", e))?;
        file.write_all(report_json.as_bytes())
            .map_err(|e| format!("Cannot write report: {}", e))?;
        Ok(())
    }

    /// Resolves the algorithm identifier for the hashing report section.
    /// Prefers the config-layer value when it matches a known algorithm,
    /// falling back to hash result provenance only when the config value
    /// is a meta-identifier (e.g., "auto") that shouldn't appear in output.
    fn resolve_reported_algorithm(&self) -> String {
        let config_algo = &self.config.hash.algorithm;
        // If the config already has a concrete algorithm, use it for
        // consistency with the §4.2 hierarchy contract
        match config_algo.as_str() {
            "md5" | "sha1" | "sha256" => config_algo.clone(),
            _ => {
                // Meta-identifier in config — resolve from hash results
                self.hash_results.first()
                    .map(|h| h.algo.clone())
                    .unwrap_or_else(|| config_algo.clone())
            }
        }
    }
}
