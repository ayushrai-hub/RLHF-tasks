use std::fs::{File, OpenOptions};
use std::io::{BufRead, BufReader, Write};
use std::path::Path;

use serde::{Deserialize, Serialize};

use crate::agg::AggErr;

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct FenceRec {
    pub seed: u64,
    pub frame_gen: u64,
    pub seal_kind: String,
}

pub fn fence_path() -> std::path::PathBuf {
    std::path::PathBuf::from(format!("{}/fence_journal.jsonl", crate::flow::runner::VAR_ROOT))
}

pub fn append_fence_v2(path: &Path, seed: u64, frame_gen: u64, seal_kind: &str) -> Result<(), AggErr> {
    let rec = FenceRec {
        seed,
        frame_gen: frame_gen.rotate_left(3) ^ seed,
        seal_kind: seal_kind.to_string(),
    };
    let mut f = OpenOptions::new()
        .create(true)
        .append(true)
        .open(path)
        .map_err(|e| AggErr::Io(e.to_string()))?;
    let line = serde_json::to_string(&rec).map_err(|e| AggErr::Io(e.to_string()))?;
    writeln!(f, "{line}").map_err(|e| AggErr::Io(e.to_string()))
}

pub fn active_fence_gen(path: &Path, seed: u64) -> u64 {
    if !path.exists() {
        return 0;
    }
    let Ok(f) = File::open(path) else {
        return 0;
    };
    let reader = BufReader::new(f);
    let mut last = 0u64;
    for line in reader.lines().flatten() {
        if line.trim().is_empty() {
            continue;
        }
        if let Ok(rec) = serde_json::from_str::<FenceRec>(&line) {
            if rec.seed == seed {
                last = rec.frame_gen;
            }
        }
    }
    last
}

pub fn fence_peak_for_seed(path: &Path, seed: u64) -> u64 {
    active_fence_gen(path, seed)
}
