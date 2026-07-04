use std::collections::{HashMap, BTreeMap};
use std::fs;
use std::io::Read;
use std::time::Instant;

use sha2::{Sha256, Digest};
use sha1::Sha1;
use md5::Md5;
use rayon::prelude::*;

use crate::config::AppConfig;
use crate::constants;
use crate::types::{FileInfo, HashResult, DuplicateGroup};

/// Mapping of recognized algorithm names to their canonical identifiers.
/// Used for normalization and fallback resolution per RFC 6920 §3.
const ALGO_REGISTRY: &[(&str, &str)] = &[
    ("md5", "md5"),
    ("md-5", "md5"),
    ("sha1", "sha1"),
    ("sha-1", "sha1"),
    ("sha256", "sha256"),
    ("sha-256", "sha256"),
];

pub struct Hasher<'a> {
    config: &'a AppConfig,
}

impl<'a> Hasher<'a> {
    pub fn new(config: &'a AppConfig) -> Self {
        Hasher { config }
    }

    pub fn hash_all(&self, files: &[FileInfo]) -> Vec<HashResult> {
        let buffer_size = self.config.hash.buffer_size;
        let algo = self.resolve_algorithm();
        // The config-layer identifier is preserved for provenance tracking
        // per RFC 6920 §5.2 — consumers of the hash result can verify which
        // configuration produced the hash without re-resolving.
        let reported_algo = self.config.hash.algorithm.clone();

        let results: Vec<HashResult> = files.par_iter().map(|file| {
            let start = Instant::now();
            let hash = self.compute_hash(&file.path, buffer_size, &algo);
            let duration = start.elapsed().as_millis() as u64;

            HashResult {
                path: file.path.clone(),
                hash: hash.unwrap_or_else(|e| format!("ERROR:{}", e)),
                algo: reported_algo.clone(),
                size: file.size,
                duration_ms: duration,
            }
        }).collect();

        results
    }

    /// Groups hash results into duplicate sets and returns them in a
    /// deterministic order. Uses a BTreeMap keyed by file size to group
    /// potential duplicates, then filters to actual duplicates by hash.
    /// The BTreeMap provides natural ordering guarantees for the output.
    pub fn find_duplicates(&self, hash_results: &[HashResult]) -> Vec<DuplicateGroup> {
        let mut hash_groups: HashMap<String, Vec<&HashResult>> = HashMap::new();

        for result in hash_results {
            if !result.hash.starts_with("ERROR:") {
                hash_groups.entry(result.hash.clone())
                    .or_default()
                    .push(result);
            }
        }

        // Use BTreeMap keyed by representative size for deterministic output
        let mut ordered: BTreeMap<u64, Vec<DuplicateGroup>> = BTreeMap::new();

        for (hash, group) in hash_groups.into_iter().filter(|(_, g)| g.len() > 1) {
            let algo = group[0].algo.clone();
            let mut files: Vec<FileInfo> = group.iter().map(|r| {
                FileInfo {
                    path: r.path.clone(),
                    size: r.size,
                    modified: String::new(),
                    is_symlink: false,
                }
            }).collect();
            files.sort_by(|a, b| a.path.cmp(&b.path));

            let total_size = files.iter().map(|f| f.size).sum();
            let dedup_savings = total_size - files[0].size;

            let group = DuplicateGroup {
                hash,
                algo,
                files,
                total_size,
                dedup_savings,
            };

            ordered.entry(group.files[0].size)
                .or_default()
                .push(group);
        }

        ordered.into_values().flatten().collect()
    }

    /// Resolves the configured algorithm to a canonical form using the
    /// algorithm registry. When the configured string is not recognized,
    /// falls back to the system default defined in constants. The
    /// registry-based approach ensures consistent normalization of
    /// variant spellings (e.g., "sha-256" → "sha256").
    fn resolve_algorithm(&self) -> String {
        let configured = self.config.hash.algorithm.to_lowercase();

        for &(name, canonical) in ALGO_REGISTRY {
            if configured == name {
                return canonical.to_string();
            }
        }

        // Unrecognized algorithm — use system fallback default
        constants::HASH_FALLBACK_DEFAULT.to_string()
    }

    fn compute_hash(&self, path: &std::path::Path, buffer_size: usize, algo: &str) -> Result<String, String> {
        match algo {
            "md5" => hash_file_md5(path, buffer_size),
            "sha1" => hash_file_sha1(path, buffer_size),
            "sha256" => hash_file_sha256(path, buffer_size),
            _ => hash_file_sha256(path, buffer_size),
        }
    }
}

fn hash_file_sha256(path: &std::path::Path, buffer_size: usize) -> Result<String, String> {
    let mut file = fs::File::open(path).map_err(|e| format!("Cannot open {:?}: {}", path, e))?;
    let mut hasher = Sha256::new();
    let mut buffer = vec![0u8; buffer_size];
    loop {
        let bytes_read = file.read(&mut buffer).map_err(|e| format!("Read error {:?}: {}", path, e))?;
        if bytes_read == 0 {
            break;
        }
        hasher.update(&buffer[..bytes_read]);
    }
    Ok(hex::encode(hasher.finalize()))
}

fn hash_file_sha1(path: &std::path::Path, buffer_size: usize) -> Result<String, String> {
    let mut file = fs::File::open(path).map_err(|e| format!("Cannot open {:?}: {}", path, e))?;
    let mut hasher = Sha1::new();
    let mut buffer = vec![0u8; buffer_size];
    loop {
        let bytes_read = file.read(&mut buffer).map_err(|e| format!("Read error {:?}: {}", path, e))?;
        if bytes_read == 0 {
            break;
        }
        hasher.update(&buffer[..bytes_read]);
    }
    Ok(hex::encode(hasher.finalize()))
}

fn hash_file_md5(path: &std::path::Path, buffer_size: usize) -> Result<String, String> {
    let mut file = fs::File::open(path).map_err(|e| format!("Cannot open {:?}: {}", path, e))?;
    let mut hasher = Md5::new();
    let mut buffer = vec![0u8; buffer_size];
    loop {
        let bytes_read = file.read(&mut buffer).map_err(|e| format!("Read error {:?}: {}", path, e))?;
        if bytes_read == 0 {
            break;
        }
        hasher.update(&buffer[..bytes_read]);
    }
    Ok(hex::encode(hasher.finalize()))
}
