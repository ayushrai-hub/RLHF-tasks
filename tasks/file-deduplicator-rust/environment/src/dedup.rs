use std::fs;

use crate::config::AppConfig;
use crate::constants;
use crate::types::{DedupAction, DedupResult, DuplicateGroup, FileInfo};

pub struct Deduplicator<'a> {
    config: &'a AppConfig,
}

impl<'a> Deduplicator<'a> {
    pub fn new(config: &'a AppConfig) -> Self {
        Deduplicator { config }
    }

    pub fn deduplicate(&self, groups: &[DuplicateGroup], cli_dry_run: bool) -> DedupResult {
        let is_dry_run = cli_dry_run || self.config.dedup.always_dry_run;
        let mut actions = Vec::new();
        let mut errors = Vec::new();

        for group in groups {
            if group.files.len() < 2 {
                continue;
            }

            let keep_file = match self.config.dedup.keep_strategy.as_str() {
                constants::KEEP_STRATEGY_NEWEST => self.pick_newest(&group.files),
                constants::KEEP_STRATEGY_OLDEST => self.pick_oldest(&group.files),
                constants::KEEP_STRATEGY_FIRST => self.pick_first(&group.files),
                _ => self.pick_newest(&group.files),
            };

            let kept_path = keep_file.path.clone();
            let mut removed = Vec::new();

            for file in &group.files {
                if file.path != kept_path {
                    if !is_dry_run {
                        if let Err(e) = fs::remove_file(&file.path) {
                            errors.push(format!("Failed to remove {:?}: {}", file.path, e));
                        }
                    }
                    removed.push(file.path.clone());
                }
            }

            actions.push(DedupAction {
                kept: kept_path,
                removed,
            });
        }

        let total_removed: usize = actions.iter().map(|a| a.removed.len()).sum();
        let total_savings: u64 = groups.iter().map(|g| g.dedup_savings).sum();

        DedupResult {
            actions,
            total_removed,
            total_savings,
            errors: if errors.is_empty() { None } else { Some(errors) },
            dry_run: is_dry_run,
        }
    }

    fn pick_newest<'b>(&self, files: &'b [FileInfo]) -> &'b FileInfo {
        files.iter().max_by_key(|f| &f.modified).unwrap()
    }

    fn pick_oldest<'b>(&self, files: &'b [FileInfo]) -> &'b FileInfo {
        files.iter().min_by_key(|f| &f.modified).unwrap()
    }

    fn pick_first<'b>(&self, files: &'b [FileInfo]) -> &'b FileInfo {
        &files[0]
    }
}
