//! Trace payload replay helpers.

use std::fs;
use std::path::{Path, PathBuf};

use crate::ingest::staged_digest_lines;

pub fn digest_lines_for_payload(payload: &[u8], chunk_size: usize) -> Vec<String> {
    staged_digest_lines(payload, chunk_size)
}

pub fn probe_offsets_for_payload(payload: &[u8], chunk_size: usize) -> Vec<u64> {
    digest_lines_for_payload(payload, chunk_size)
        .iter()
        .map(|line| {
            let offset = line.split(':').next().expect("offset");
            offset.parse::<u64>().expect("parse offset")
        })
        .collect()
}

pub fn collect_trace_paths(dir: &Path, out: &mut Vec<PathBuf>) -> std::io::Result<()> {
    if !dir.is_dir() {
        return Ok(());
    }
    for entry in fs::read_dir(dir)? {
        let entry = entry?;
        let path = entry.path();
        if path.is_dir() {
            collect_trace_paths(&path, out)?;
        } else if path.extension().and_then(|s| s.to_str()) == Some("trace") {
            out.push(path);
        }
    }
    Ok(())
}

pub fn replay_dir(
    traces_dir: &Path,
    chunk_size: usize,
) -> std::io::Result<Vec<(String, Vec<String>)>> {
    let mut paths = Vec::new();
    collect_trace_paths(traces_dir, &mut paths)?;
    paths.sort();

    let mut runs = Vec::new();
    for path in paths {
        let rel = path
            .strip_prefix(traces_dir)
            .unwrap_or(&path)
            .to_string_lossy()
            .to_string();
        let payload = fs::read(&path)?;
        let lines = digest_lines_for_payload(&payload, chunk_size);
        runs.push((rel, lines));
    }
    Ok(runs)
}
