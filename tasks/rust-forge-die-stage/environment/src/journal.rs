use crate::bundle::{is_bundle_dir, load_bundle, OrderedPack};
use crate::pack::{
    is_pack_dir, load_pack, manifest_path_for, resolve_shard_path, JournalPack,
};
use serde::Deserialize;
use serde_json::Value;
use std::collections::BTreeMap;
use std::fs::File;
use std::io::{BufRead, BufReader};
use std::path::PathBuf;

#[derive(Debug, Clone, Deserialize)]
pub struct OpEntry {
    pub seq: u64,
    #[serde(default = "default_journal_revision")]
    pub journal_revision: u64,
    #[serde(default)]
    pub op_id: String,
    pub op: String,
    pub scenario_tag: String,
    #[serde(default)]
    pub forge_epoch: u32,
    #[serde(default)]
    pub die_id: String,
    #[serde(default)]
    pub shard_index: usize,
    #[serde(default)]
    pub source_path: String,
    #[serde(default)]
    pub line_number: usize,
    #[serde(default)]
    pub ancestry_index: usize,
}

fn default_journal_revision() -> u64 {
    1
}

#[derive(Debug, Clone)]
pub struct LineagePackDigest {
    pub id: String,
    pub parent: Option<String>,
    pub generation: u64,
    pub journal_digest: String,
}

#[derive(Debug, Clone)]
pub struct LoadedReplay {
    pub pack: Option<JournalPack>,
    pub pack_dir: Option<PathBuf>,
    pub manifest_path: Option<String>,
    pub scenario_tag: String,
    pub pack_generation: u64,
    pub journal_digest: String,
    pub lineage_digest_hex: String,
    pub die_root: String,
    pub snapshot_path: String,
    pub entries: Vec<OpEntry>,
    pub tombstone_audit: Vec<OpEntry>,
    pub warnings: Vec<String>,
}

pub fn load_replay(input_path: &str, die_root: &str, snapshot_path: &str) -> Result<LoadedReplay, String> {
    if is_bundle_dir(input_path) {
        load_bundle_replay(input_path, die_root, snapshot_path)
    } else if is_pack_dir(input_path) {
        load_single_pack_replay(input_path, die_root, snapshot_path, None)
    } else {
        load_file_replay(input_path, die_root, snapshot_path)
    }
}

fn load_file_replay(input_path: &str, die_root: &str, snapshot_path: &str) -> Result<LoadedReplay, String> {
    let (raw, warnings) = load_file_entries(input_path, 0, 0, "default")?;
    let pack_digest = crate::digest::journal_stream_digest(&raw);
    let lineage_packs = vec![LineagePackDigest {
        id: "file".into(),
        parent: None,
        generation: 0,
        journal_digest: pack_digest.clone(),
    }];
    let (entries, tombstone_audit) = collapse_entries(raw, &lineage_packs);
    let journal_digest = crate::digest::journal_stream_digest(&entries);
    let surviving_op_ids: Vec<String> = entries.iter().map(|e| e.op_id.clone()).collect();
    let lineage_digest_hex = crate::digest::lineage_digest_hex(&lineage_packs, &surviving_op_ids);
    let scenario_tag = entries
        .first()
        .map(|e| e.scenario_tag.clone())
        .unwrap_or_else(|| "default".to_string());
    Ok(LoadedReplay {
        pack: None,
        pack_dir: None,
        manifest_path: manifest_path_for(input_path),
        scenario_tag,
        pack_generation: 0,
        journal_digest,
        lineage_digest_hex,
        die_root: die_root.to_string(),
        snapshot_path: snapshot_path.to_string(),
        entries,
        tombstone_audit,
        warnings,
    })
}

fn load_single_pack_replay(
    input_path: &str,
    die_root: &str,
    snapshot_path: &str,
    bundle_scenario: Option<&str>,
) -> Result<LoadedReplay, String> {
    let (pack, pack_dir) = load_pack(input_path)?;
    let manifest_path = pack_dir.join("manifest.json").to_string_lossy().to_string();
    let (raw, warnings) = load_pack_rows(&pack, &pack_dir, 0)?;
    let pack_digest = crate::digest::journal_stream_digest(&raw);
    let lineage_packs = vec![LineagePackDigest {
        id: "pack".into(),
        parent: None,
        generation: pack.pack_generation,
        journal_digest: pack_digest,
    }];
    let (entries, tombstone_audit) = collapse_entries(raw, &lineage_packs);
    let journal_digest = crate::digest::journal_stream_digest(&entries);
    let surviving_op_ids: Vec<String> = entries.iter().map(|e| e.op_id.clone()).collect();
    let lineage_digest_hex = crate::digest::lineage_digest_hex(&lineage_packs, &surviving_op_ids);
    Ok(LoadedReplay {
        pack: Some(pack.clone()),
        pack_dir: Some(pack_dir),
        manifest_path: Some(manifest_path),
        scenario_tag: bundle_scenario.unwrap_or(&pack.scenario_tag).to_string(),
        pack_generation: pack.pack_generation,
        journal_digest,
        lineage_digest_hex,
        die_root: die_root.to_string(),
        snapshot_path: snapshot_path.to_string(),
        entries,
        tombstone_audit,
        warnings,
    })
}

fn load_bundle_replay(input_path: &str, die_root: &str, snapshot_path: &str) -> Result<LoadedReplay, String> {
    let (bundle, _bundle_dir, ordered) = load_bundle(input_path)?;
    let mut raw_entries = Vec::new();
    let mut warnings = Vec::new();
    let mut lineage_packs = Vec::new();
    let mut max_generation = 0u64;
    for ordered_pack in &ordered {
        max_generation = max_generation.max(ordered_pack.generation);
        let (rows, row_warnings) = load_pack_rows(
            &ordered_pack.pack,
            &ordered_pack.pack_dir,
            ordered_pack.ancestry_index,
        )?;
        let pack_digest = crate::digest::journal_stream_digest(&rows);
        let parent = ordered_pack
            .pack
            .scenario_tag
            .clone(); // placeholder, use bundle parent below
        let _ = parent;
        let pack_ref = bundle
            .packs
            .iter()
            .find(|p| p.id == ordered_pack.id)
            .ok_or_else(|| format!("missing bundle pack {}", ordered_pack.id))?;
        lineage_packs.push(LineagePackDigest {
            id: ordered_pack.id.clone(),
            parent: pack_ref.parent.clone(),
            generation: ordered_pack.generation,
            journal_digest: pack_digest,
        });
        raw_entries.extend(rows);
        warnings.extend(row_warnings);
    }
    let (entries, tombstone_audit) = collapse_entries(raw_entries, &lineage_packs);
    let journal_digest = crate::digest::journal_stream_digest(&entries);
    let surviving_op_ids: Vec<String> = entries.iter().map(|e| e.op_id.clone()).collect();
    let lineage_digest_hex = crate::digest::lineage_digest_hex(&lineage_packs, &surviving_op_ids);
    Ok(LoadedReplay {
        pack: None,
        pack_dir: None,
        manifest_path: Some(format!("{input_path}/bundle.json")),
        scenario_tag: bundle.scenario_tag.clone(),
        pack_generation: max_generation,
        journal_digest,
        lineage_digest_hex,
        die_root: die_root.to_string(),
        snapshot_path: snapshot_path.to_string(),
        entries,
        tombstone_audit,
        warnings,
    })
}

fn load_pack_rows(
    pack: &JournalPack,
    pack_dir: &PathBuf,
    ancestry_index: usize,
) -> Result<(Vec<OpEntry>, Vec<String>), String> {
    let mut raw_entries = Vec::new();
    let mut warnings = Vec::new();
    for (shard_index, shard) in pack.shards.iter().enumerate() {
        let shard_path = resolve_shard_path(pack_dir, &shard.path)?;
        let (rows, row_warnings) = load_file_entries(
            shard_path.to_str().unwrap_or_default(),
            shard_index,
            ancestry_index,
            &pack.scenario_tag,
        )?;
        let (collapsed, _) = collapse_entries(rows, &[]);
        raw_entries.extend(collapsed);
        warnings.extend(row_warnings);
    }
    Ok((raw_entries, warnings))
}

fn normalize_row(mut value: Value) -> Result<Value, String> {
    let obj = value
        .as_object_mut()
        .ok_or_else(|| "journal row must be an object".to_string())?;
    if let Some(tier) = obj.get("forge_tier").cloned() {
        obj.insert("forge_epoch".to_string(), tier);
    }
    if let Some(op) = obj.get("op").and_then(|v| v.as_str()) {
        let normalized = match op {
            "die_seal" => "die_sealed",
            "forge_purge" => "forge_purged",
            other => other,
        };
        obj.insert("op".to_string(), Value::String(normalized.to_string()));
    }
    Ok(Value::Object(obj.clone()))
}

fn load_file_entries(
    path: &str,
    shard_index: usize,
    ancestry_index: usize,
    default_tag: &str,
) -> Result<(Vec<OpEntry>, Vec<String>), String> {
    let file = File::open(path).map_err(|e| e.to_string())?;
    let reader = BufReader::new(file);
    let lines: Vec<String> = reader.lines().collect::<Result<_, _>>().map_err(|e| e.to_string())?;
    let mut rows = Vec::new();
    let mut warnings = Vec::new();
    for (line_no, line) in lines.iter().enumerate() {
        let trimmed = line.trim();
        if trimmed.is_empty() {
            continue;
        }
        match serde_json::from_str::<Value>(trimmed) {
            Ok(raw) => {
                let normalized = normalize_row(raw)?;
                let mut entry: OpEntry =
                    serde_json::from_value(normalized).map_err(|e| e.to_string())?;
                if entry.scenario_tag.is_empty() {
                    entry.scenario_tag = default_tag.to_string();
                }
                if entry.op_id.is_empty() {
                    entry.op_id = format!("{}-{}", entry.seq, line_no + 1);
                }
                entry.shard_index = shard_index;
                entry.ancestry_index = ancestry_index;
                entry.source_path = path.to_string();
                entry.line_number = line_no + 1;
                rows.push(entry);
            }
            Err(err) => {
                let is_last = line_no + 1 == lines.len();
                if is_last && !rows.is_empty() {
                    warnings.push(format!("truncated journal row in {path}: {err}"));
                    continue;
                }
                return Err(format!("invalid journal row in {path}: {err}"));
            }
        }
    }
    Ok((rows, warnings))
}

fn ordering_key(entry: &OpEntry) -> (usize, u64, u64, usize, usize) {
    (
        entry.ancestry_index,
        entry.seq,
        entry.journal_revision,
        entry.shard_index,
        entry.line_number,
    )
}

pub fn collapse_entries(
    raw: Vec<OpEntry>,
    _lineage_packs: &[LineagePackDigest],
) -> (Vec<OpEntry>, Vec<OpEntry>) {
    let mut by_op_id: BTreeMap<String, OpEntry> = BTreeMap::new();
    for entry in raw {
        let existing = by_op_id.get(&entry.op_id);
        let newer = |a: &OpEntry, b: &OpEntry| ordering_key(a) > ordering_key(b);
        match existing {
            Some(prev) if !newer(&entry, prev) => {}
            _ => {
                by_op_id.insert(entry.op_id.clone(), entry);
            }
        }
    }
    let mut tombstone_audit = Vec::new();
    let mut surviving = Vec::new();
    for entry in by_op_id.into_values() {
        if entry.op == "op_tombstone" {
            tombstone_audit.push(entry);
        } else {
            surviving.push(entry);
        }
    }
    surviving.sort_by(|a, b| ordering_key(a).cmp(&ordering_key(b)));
    (surviving, tombstone_audit)
}
