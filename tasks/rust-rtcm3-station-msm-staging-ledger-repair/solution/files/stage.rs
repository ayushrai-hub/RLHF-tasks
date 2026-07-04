use crate::staging_manifest;
use crate::types::{DecodeRow, StagedRow};
use std::fs::{self, File};
use std::io::{BufRead, BufReader, BufWriter, Write};
use std::path::Path;

pub fn run(ledger_path: &str, staged_path: &str) -> Result<(), String> {
    let reader = BufReader::new(File::open(ledger_path).map_err(|e| e.to_string())?);
    let parent = Path::new(staged_path)
        .parent()
        .ok_or("invalid staged path")?;
    fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    let tmp = parent.join(".staged.tmp");
    let mut writer = BufWriter::new(File::create(&tmp).map_err(|e| e.to_string())?);

    let mut insertion_keys: Vec<String> = Vec::new();
    let mut row_count: u64 = 0;

    for line in reader.lines() {
        let line = line.map_err(|e| e.to_string())?;
        if line.trim().is_empty() {
            continue;
        }
        let row: DecodeRow = serde_json::from_str(&line).map_err(|e| e.to_string())?;
        if !row.valid {
            continue;
        }
        let staged = StagedRow {
            station_key: format!("{}:{}", row.station_id, row.mountpoint),
            station_id: row.station_id,
            mountpoint: row.mountpoint,
            sequence: row.sequence,
            epoch_ms: row.epoch_ms,
            observable_sum: row.observable_sum,
        };
        insertion_keys.push(staged.station_key.clone());
        row_count += 1;
        let json = serde_json::to_string(&staged).map_err(|e| e.to_string())?;
        writeln!(writer, "{json}").map_err(|e| e.to_string())?;
    }
    writer.flush().map_err(|e| e.to_string())?;
    fs::rename(&tmp, staged_path).map_err(|e| e.to_string())?;
    staging_manifest::write_manifest(staged_path, &insertion_keys, row_count)?;
    Ok(())
}
