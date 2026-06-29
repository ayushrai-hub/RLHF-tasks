use crate::digest::{die_root_digest, sha256_hex};
use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
pub struct DieRecord {
    pub die_id: String,
    pub checksum: u32,
    pub tonnage: u64,
    pub forge_epoch: u32,
    #[serde(default)]
    pub source_format: String,
    #[serde(default)]
    pub revision: Option<u64>,
    #[serde(default)]
    pub digest_hex: String,
}

#[derive(Clone, Debug, Default)]
pub struct ForgeLedger {
    dies: BTreeMap<String, DieRecord>,
    forge_epoch: u32,
    journal_revision: u64,
    scenario_tag: String,
    journal_digest: String,
    die_root_digest: String,
    lineage_digest_hex: String,
    snapshot_id: Option<String>,
}

impl ForgeLedger {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn set_digest_context(
        &mut self,
        journal_digest: &str,
        die_root: &str,
        lineage_digest_hex: &str,
    ) {
        self.journal_digest = journal_digest.to_string();
        self.die_root_digest = die_root_digest(die_root).unwrap_or_default();
        self.lineage_digest_hex = lineage_digest_hex.to_string();
    }

    pub fn set_snapshot_id(&mut self, snapshot_id: Option<String>) {
        self.snapshot_id = snapshot_id;
    }

    pub fn set_scenario_tag(&mut self, tag: &str) {
        self.scenario_tag = tag.to_string();
    }

    pub fn scenario_tag(&self) -> &str {
        &self.scenario_tag
    }

    pub fn forge_epoch(&self) -> u32 {
        self.forge_epoch
    }

    pub fn journal_revision(&self) -> u64 {
        self.journal_revision
    }

    pub fn set_forge_epoch(&mut self, epoch: u32) {
        self.forge_epoch = epoch;
        self.bump_journal_revision();
    }

    pub fn restore_full_state(
        &mut self,
        dies: BTreeMap<String, DieRecord>,
        forge_epoch: u32,
        journal_revision: u64,
    ) {
        self.dies = dies;
        self.forge_epoch = forge_epoch;
        self.journal_revision = journal_revision;
    }

    pub fn bump_journal_revision(&mut self) -> u64 {
        self.journal_revision = self.journal_revision.saturating_add(1);
        self.journal_revision
    }

    pub fn bind_die(&mut self, record: DieRecord) -> bool {
        if let Some(existing) = self.dies.get(&record.die_id) {
            if existing.checksum == record.checksum && existing.digest_hex == record.digest_hex {
                return false;
            }
        }
        self.dies.insert(record.die_id.clone(), record);
        self.bump_journal_revision();
        true
    }

    pub fn purge_not_on_epoch(&mut self, forge_epoch: u32) {
        self.dies.retain(|_, rec| rec.forge_epoch == forge_epoch);
        self.bump_journal_revision();
    }

    pub fn die_count(&self) -> usize {
        self.dies.len()
    }

    pub fn has_die(&self, die_id: &str) -> bool {
        self.dies.contains_key(die_id)
    }

    pub fn die_checksum(&self, die_id: &str) -> Option<u32> {
        self.dies.get(die_id).map(|r| r.checksum)
    }

    pub fn total_tonnage(&self) -> u64 {
        self.dies.values().map(|r| r.tonnage).sum()
    }

    pub fn snapshot(&self) -> BTreeMap<String, DieRecord> {
        self.dies.clone()
    }

    pub fn restore_snapshot(&mut self, snap: BTreeMap<String, DieRecord>) {
        self.dies = snap;
    }

    pub fn clone_state(&self) -> Self {
        self.clone()
    }

    pub fn bound_dies_sorted(&self) -> Vec<DieRecord> {
        let mut rows: Vec<DieRecord> = self.dies.values().cloned().collect();
        rows.sort_by(|a, b| a.die_id.cmp(&b.die_id));
        rows
    }

    pub fn die_root_digest(&self) -> &str {
        &self.die_root_digest
    }

    pub fn ledger_digest_hex(&self) -> String {
        let mut rows = Vec::new();
        for rec in self.bound_dies_sorted() {
            rows.push(format!(
                "{}|{}|{}|{}|{}|{}|{}|{}",
                rec.die_id,
                rec.checksum,
                rec.tonnage,
                rec.forge_epoch,
                self.journal_digest,
                self.die_root_digest,
                String::new(),
                String::new()
            ));
        }
        sha256_hex(rows.join("\n").as_bytes())
    }

    pub fn load_from_file(path: &str) -> Result<(Self, Option<String>), String> {
        let raw = std::fs::read_to_string(path).map_err(|e| e.to_string())?;
        let value: serde_json::Value = serde_json::from_str(&raw).map_err(|e| e.to_string())?;
        if value.get("schema_version").and_then(|v| v.as_u64()) == Some(2) {
            let snapshot_id = value
                .get("snapshot_id")
                .and_then(|v| v.as_str())
                .map(|s| s.to_string());
            let dies_val = value.get("dies").cloned().unwrap_or(serde_json::json!({}));
            let dies: BTreeMap<String, DieRecord> =
                serde_json::from_value(dies_val).map_err(|e| e.to_string())?;
            let mut ledger = Self::new();
            ledger.restore_full_state(
                dies,
                value
                    .get("forge_epoch")
                    .and_then(|v| v.as_u64())
                    .unwrap_or(0) as u32,
                value
                    .get("journal_revision")
                    .and_then(|v| v.as_u64())
                    .unwrap_or(0),
            );
            return Ok((ledger, snapshot_id));
        }
        let data: StoredForgeLedger = serde_json::from_str(&raw).map_err(|e| e.to_string())?;
        Ok((
            Self {
                dies: data.dies,
                forge_epoch: data.forge_epoch,
                journal_revision: data.journal_revision,
                scenario_tag: data.scenario_tag,
                journal_digest: data.journal_digest,
                die_root_digest: data.die_root_digest,
                lineage_digest_hex: String::new(),
                snapshot_id: None,
            },
            None,
        ))
    }
}

#[derive(Serialize, Deserialize)]
struct StoredForgeLedger {
    dies: BTreeMap<String, DieRecord>,
    forge_epoch: u32,
    journal_revision: u64,
    #[serde(default)]
    scenario_tag: String,
    #[serde(default)]
    journal_digest: String,
    #[serde(default)]
    die_root_digest: String,
}
