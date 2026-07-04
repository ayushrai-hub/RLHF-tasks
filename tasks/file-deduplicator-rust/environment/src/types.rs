use serde::{Deserialize, Serialize};
use std::path::PathBuf;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FileInfo {
    pub path: PathBuf,
    pub size: u64,
    pub modified: String,
    pub is_symlink: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HashResult {
    pub path: PathBuf,
    pub hash: String,
    pub algo: String,
    pub size: u64,
    pub duration_ms: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DuplicateGroup {
    pub hash: String,
    pub algo: String,
    pub files: Vec<FileInfo>,
    pub total_size: u64,
    pub dedup_savings: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DedupAction {
    pub kept: PathBuf,
    pub removed: Vec<PathBuf>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DedupResult {
    pub actions: Vec<DedupAction>,
    pub total_removed: usize,
    pub total_savings: u64,
    pub errors: Option<Vec<String>>,
    pub dry_run: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ScanResult {
    pub files: Vec<FileInfo>,
    pub total_size: u64,
    pub total_files: usize,
    pub skipped_dirs: usize,
    pub errors: Vec<String>,
    pub scan_duration_ms: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ScanSummary {
    pub total_files: usize,
    pub total_size: u64,
    pub skipped_dirs: usize,
    pub errors: usize,
    pub scan_duration_ms: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HashSummary {
    pub total_hashed: usize,
    pub total_size: u64,
    pub algo: String,
    pub hash_duration_ms: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DedupSummary {
    pub duplicate_groups: usize,
    pub duplicate_files: usize,
    pub total_wasted_size: u64,
    pub actions_taken: usize,
    pub total_removed: usize,
    pub total_savings: u64,
    pub dry_run: bool,
    pub errors: usize,
}
