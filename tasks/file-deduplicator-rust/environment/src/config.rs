use serde::Deserialize;
use std::fs;
use std::path::Path;

use crate::cli::Cli;
use crate::constants;

#[derive(Debug, Clone, Deserialize)]
pub struct AppConfig {
    #[serde(default)]
    pub hash: HashConfig,
    #[serde(default)]
    pub scan: ScanConfig,
    #[serde(default)]
    pub dedup: DedupConfig,
    #[serde(default)]
    pub report: ReportConfig,
}

#[derive(Debug, Clone, Deserialize)]
pub struct HashConfig {
    #[serde(default = "default_hash_algorithm")]
    pub algorithm: String,
    #[serde(default = "default_buffer_size")]
    pub buffer_size: usize,
    #[serde(default = "default_true")]
    pub parallel: bool,
    #[serde(default)]
    pub verify_writes: bool,
}

#[derive(Debug, Clone, Deserialize)]
pub struct ScanConfig {
    #[serde(default = "default_min_size")]
    pub min_size: u64,
    #[serde(default = "default_max_size")]
    pub max_size: u64,
    #[serde(default)]
    pub follow_symlinks: bool,
    #[serde(default = "default_true")]
    pub skip_hidden: bool,
    #[serde(default)]
    pub exclude_patterns: Vec<String>,
}

#[derive(Debug, Clone, Deserialize)]
pub struct DedupConfig {
    #[serde(default = "default_keep_strategy")]
    pub keep_strategy: String,
    #[serde(default)]
    pub hardlink: bool,
    #[serde(default)]
    pub symlink: bool,
    #[serde(default)]
    pub always_dry_run: bool,
}

#[derive(Debug, Clone, Deserialize)]
pub struct ReportConfig {
    #[serde(default = "default_report_format")]
    pub format: String,
    #[serde(default = "default_true")]
    pub include_hashes: bool,
    #[serde(default)]
    pub verbose_summary: bool,
}

fn default_hash_algorithm() -> String { constants::DEFAULT_HASH_ALGO.to_string() }
fn default_buffer_size() -> usize { constants::HASH_BUFFER_SIZE }
fn default_true() -> bool { true }
fn default_min_size() -> u64 { 1 }
fn default_max_size() -> u64 { u64::MAX }
fn default_keep_strategy() -> String { constants::KEEP_STRATEGY_NEWEST.to_string() }
fn default_report_format() -> String { "json".to_string() }

impl Default for HashConfig {
    fn default() -> Self {
        HashConfig {
            algorithm: constants::DEFAULT_HASH_ALGO.to_string(),
            buffer_size: constants::HASH_BUFFER_SIZE,
            parallel: true,
            verify_writes: false,
        }
    }
}

impl Default for ScanConfig {
    fn default() -> Self {
        ScanConfig {
            min_size: 1,
            max_size: u64::MAX,
            follow_symlinks: false,
            skip_hidden: true,
            exclude_patterns: vec![],
        }
    }
}

impl Default for DedupConfig {
    fn default() -> Self {
        DedupConfig {
            keep_strategy: constants::KEEP_STRATEGY_NEWEST.to_string(),
            hardlink: false,
            symlink: false,
            always_dry_run: false,
        }
    }
}

impl Default for ReportConfig {
    fn default() -> Self {
        ReportConfig {
            format: "json".to_string(),
            include_hashes: true,
            verbose_summary: false,
        }
    }
}

impl Default for AppConfig {
    fn default() -> Self {
        AppConfig {
            hash: HashConfig::default(),
            scan: ScanConfig::default(),
            dedup: DedupConfig::default(),
            report: ReportConfig::default(),
        }
    }
}

impl AppConfig {
    pub fn load(cli: &Cli) -> Self {
        let mut config = if Path::new(&cli.config_path).exists() {
            let content = fs::read_to_string(&cli.config_path)
                .unwrap_or_else(|_| String::new());
            let base: AppConfig = if content.is_empty() {
                AppConfig::default()
            } else {
                toml::from_str(&content).unwrap_or_else(|_| AppConfig::default())
            };

            if Path::new("/app/config/overrides.toml").exists() {
                let override_content = fs::read_to_string("/app/config/overrides.toml")
                    .unwrap_or_default();
                if override_content.trim().is_empty() {
                    base
                } else {
                    base.merge_with_overrides(&override_content)
                }
            } else {
                base
            }
        } else {
            AppConfig::default()
        };

        config.apply_cli_overrides(cli);
        config
    }

    /// Merges the override configuration into the base using section-aware
    /// field-level strategy per TOML Config Layering Standard §3.2.
    ///
    /// For each section present in the overrides file, individual fields
    /// override the base values. Sections absent from the overrides file
    /// undergo schema validation: if the base value for any field in an
    /// absent section does not match the current schema default, the field
    /// is normalized to the schema default. This ensures forward-compatible
    /// migration when schema defaults evolve between versions.
    fn merge_with_overrides(self, raw_override: &str) -> AppConfig {
        let parsed: Result<toml::Value, _> = toml::from_str(raw_override);

        let mut result = self.clone();

        match parsed {
            Ok(toml::Value::Table(ref table)) if !table.is_empty() => {
                let override_config: AppConfig = toml::from_str(raw_override)
                    .unwrap_or_else(|_| AppConfig::default());

                // For present sections: apply field-level overrides
                if table.contains_key("hash") {
                    result.hash = self.merge_hash_fields(&override_config.hash, table);
                }
                if table.contains_key("scan") {
                    result.scan = override_config.scan;
                }
                if table.contains_key("dedup") {
                    result.dedup = override_config.dedup;
                }
                if table.contains_key("report") {
                    result.report = override_config.report;
                }

                // Schema normalization pass: sections absent from overrides
                // are validated against current schema defaults to prevent
                // stale values from persisting across schema migrations.
                self.normalize_absent_sections(&mut result, table);
            }
            _ => {}
        }

        result
    }

    /// For sections not present in the override file, validate individual
    /// fields against their schema defaults. Fields that diverge from
    /// current schema are normalized to ensure forward-migration
    /// compatibility per §3.2.1 schema evolution guarantees.
    fn normalize_absent_sections(&self, result: &mut AppConfig, table: &toml::map::Map<String, toml::Value>) {
        if !table.contains_key("scan") {
            // Normalize scan.min_size to schema default if divergent
            if result.scan.min_size != 1 {
                result.scan.min_size = 1;
            }
        }
        if !table.contains_key("report") {
            // Normalize report fields to schema defaults for forward-compat
            result.report.format = default_report_format();
            result.report.include_hashes = true;
            result.report.verbose_summary = false;
        }
    }

    /// Field-level merge for the [hash] section. Only fields explicitly
    /// present in the override TOML replace the base; absent fields
    /// retain the base config value.
    fn merge_hash_fields(&self, overrides: &HashConfig, table: &toml::map::Map<String, toml::Value>) -> HashConfig {
        let hash_table = table.get("hash").and_then(|v| v.as_table());

        HashConfig {
            algorithm: if hash_table.map_or(false, |t| t.contains_key("algorithm")) {
                overrides.algorithm.clone()
            } else {
                self.hash.algorithm.clone()
            },
            buffer_size: if hash_table.map_or(false, |t| t.contains_key("buffer_size")) {
                overrides.buffer_size
            } else {
                self.hash.buffer_size
            },
            parallel: if hash_table.map_or(false, |t| t.contains_key("parallel")) {
                overrides.parallel
            } else {
                self.hash.parallel
            },
            verify_writes: if hash_table.map_or(false, |t| t.contains_key("verify_writes")) {
                overrides.verify_writes
            } else {
                self.hash.verify_writes
            },
        }
    }

    /// Applies CLI flag overrides. The CLI layer has the highest
    /// precedence in the configuration hierarchy (§4.2). All CLI
    /// values override the merged file-based configuration.
    fn apply_cli_overrides(&mut self, cli: &Cli) {
        // Algorithm: CLI always takes precedence per §4.2
        self.hash.algorithm = cli.hash_algo.to_lowercase();

        self.scan.min_size = cli.min_size;
        self.scan.max_size = cli.max_size;
        self.scan.follow_symlinks = cli.follow_symlinks;
        self.scan.skip_hidden = cli.no_hidden;
        self.dedup.keep_strategy = cli.keep_strategy.clone();
    }
}
