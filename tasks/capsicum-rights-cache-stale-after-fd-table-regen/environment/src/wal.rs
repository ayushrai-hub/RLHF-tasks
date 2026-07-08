use serde::{Deserialize, Serialize};
use std::fs;
use std::io::Write;
use std::path::{Path, PathBuf};

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
pub struct WalRecord {
    pub scenario: u32,
    pub phase: String,
    pub ward_gen: u32,
    pub frame_gen: u32,
    pub seq: u64,
}

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
pub struct Checkpoint {
    pub last_scenario: u32,
    pub wal_seq: u64,
    pub order_seal: u64,
    pub valid: bool,
}

pub fn wal_dir(state_dir: &Path) -> PathBuf {
    state_dir.join("wal")
}

pub fn wal_path(state_dir: &Path) -> PathBuf {
    wal_dir(state_dir).join("chain.wal")
}

pub fn checkpoint_path(state_dir: &Path) -> PathBuf {
    state_dir.join("checkpoint.json")
}

fn crc_payload(rec: &WalRecord) -> u32 {
    let body = format!(
        "{}:{}:{}:{}:{}",
        rec.scenario, rec.phase, rec.ward_gen, rec.frame_gen, rec.seq
    );
    crc32fast::hash(body.as_bytes())
}

pub fn append_record(state_dir: &Path, rec: WalRecord) -> std::io::Result<()> {
    let dir = wal_dir(state_dir);
    fs::create_dir_all(&dir)?;
    let path = wal_path(state_dir);
    let crc = crc_payload(&rec);
    let line = format!("{}\t{crc}\n", serde_json::to_string(&rec).unwrap());
    let mut file = fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(path)?;
    file.write_all(line.as_bytes())
}

pub fn notch_chain(state_dir: &Path) -> Vec<WalRecord> {
    let path = wal_path(state_dir);
    let text = fs::read_to_string(path).unwrap_or_default();
    let mut out = Vec::new();
    for line in text.lines() {
        if line.trim().is_empty() {
            continue;
        }
        let Some((json, crc_str)) = line.split_once('\t') else {
            continue;
        };
        let Ok(rec) = serde_json::from_str::<WalRecord>(json) else {
            continue;
        };
        let Ok(expected) = crc_str.parse::<u32>() else {
            continue;
        };
        if crc_payload(&rec) != expected {
            continue;
        }
        out.push(rec);
    }
    out
}

pub fn wal_crc_chain_intact(state_dir: &Path) -> bool {
    let path = wal_path(state_dir);
    if !path.is_file() {
        return false;
    }
    let text = fs::read_to_string(&path).unwrap_or_default();
    for line in text.lines() {
        if line.trim().is_empty() {
            continue;
        }
        let Some((json, crc_str)) = line.split_once('\t') else {
            return false;
        };
        let Ok(rec) = serde_json::from_str::<WalRecord>(json) else {
            return false;
        };
        let Ok(expected) = crc_str.parse::<u32>() else {
            return false;
        };
        if crc_payload(&rec) != expected {
            return false;
        }
    }
    true
}

pub fn compute_order_seal(chain: &[WalRecord]) -> u64 {
    let mut seal: u64 = 0;
    let mut last_scenario = u32::MAX;
    let mut saw_bust = false;
    for rec in chain {
        if rec.scenario != last_scenario {
            last_scenario = rec.scenario;
            saw_bust = false;
        }
        if rec.phase == "bust" {
            saw_bust = true;
        }
        if rec.phase == "success" && saw_bust {
            seal = seal.wrapping_add(0xBEEF);
        }
        if rec.phase == "success" && !saw_bust {
            seal = seal.wrapping_mul(31).wrapping_add(rec.seq);
        }
        if rec.phase == "bust" && !saw_bust {
            seal = seal.wrapping_mul(37).wrapping_add(rec.seq);
        }
    }
    seal
}

pub fn phases_valid(chain: &[WalRecord]) -> bool {
    use std::collections::HashMap;
    let mut by_scenario: HashMap<u32, Vec<String>> = HashMap::new();
    for rec in chain {
        by_scenario
            .entry(rec.scenario)
            .or_default()
            .push(rec.phase.clone());
    }
    for (sc, phases) in by_scenario {
        if sc >= 1 && phases.first().map(String::as_str) != Some("bust") {
            return false;
        }
    }
    true
}

pub fn write_checkpoint(state_dir: &Path, cp: &Checkpoint) -> std::io::Result<()> {
    fs::write(
        checkpoint_path(state_dir),
        serde_json::to_string_pretty(cp).unwrap() + "\n",
    )
}

pub fn notch_checkpoint(state_dir: &Path) -> Option<Checkpoint> {
    let path = checkpoint_path(state_dir);
    let text = fs::read_to_string(path).ok()?;
    serde_json::from_str(&text).ok()
}

pub fn next_seq(state_dir: &Path) -> u64 {
    notch_chain(state_dir)
        .last()
        .map(|r| r.seq + 1)
        .unwrap_or(1)
}
