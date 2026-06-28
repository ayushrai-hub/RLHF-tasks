use crate::fdie::{die_path, read_fdie_block};
use crate::journal::{LoadedReplay, OpEntry};
use crate::ledger::{DieRecord, ForgeLedger};
use serde_json::{json, Map, Value};
use std::collections::{BTreeMap, BTreeSet};
use std::fs::OpenOptions;
use std::io::Write;
use std::path::Path;

#[derive(Clone)]
pub struct ReplayContext {
    pub ledger: ForgeLedger,
    pub log_path: Option<String>,
    pub die_root: String,
    pub next_seq: u64,
    pub current_epoch: u32,
    pub dies_sealed: u32,
    pub dies_tombstoned: u32,
    pub scenarios: BTreeSet<String>,
    pub warnings: Vec<String>,
}

impl ReplayContext {
    pub fn from_replay(replay: &LoadedReplay, journal_digest: &str) -> Self {
        let mut ledger = ForgeLedger::new();
        ledger.set_digest_context(
            journal_digest,
            &replay.die_root,
            &replay.lineage_digest_hex,
        );
        ledger.set_scenario_tag(&replay.scenario_tag);
        Self {
            ledger,
            log_path: None,
            die_root: replay.die_root.clone(),
            next_seq: 1,
            current_epoch: 0,
            dies_sealed: 0,
            dies_tombstoned: 0,
            scenarios: BTreeSet::new(),
            warnings: Vec::new(),
        }
    }

    pub fn with_ledger(ledger: ForgeLedger, die_root: String, scenario_tag: &str) -> Self {
        let current_epoch = ledger.forge_epoch();
        let mut ledger = ledger;
        ledger.set_scenario_tag(scenario_tag);
        Self {
            ledger,
            log_path: None,
            die_root,
            next_seq: 1,
            current_epoch,
            dies_sealed: 0,
            dies_tombstoned: 0,
            scenarios: BTreeSet::new(),
            warnings: Vec::new(),
        }
    }

    pub fn emit(&mut self, kind: &str, entry: &OpEntry, extra: BTreeMap<String, Value>) {
        let Some(path) = &self.log_path else {
            return;
        };
        let mut obj = Map::new();
        obj.insert("kind".into(), json!(kind));
        obj.insert("scenario_tag".into(), json!(entry.scenario_tag));
        obj.insert("seq".into(), json!(self.next_seq));
        obj.insert("journal_revision".into(), json!(self.ledger.journal_revision()));
        obj.insert("forge_epoch".into(), json!(self.ledger.forge_epoch()));
        for (k, v) in extra {
            obj.insert(k, v);
        }
        self.next_seq += 1;
        let line = serde_json::to_string(&Value::Object(obj)).unwrap() + "\n";
        if let Some(parent) = Path::new(path).parent() {
            std::fs::create_dir_all(parent).expect("create log parent directory");
        }
        OpenOptions::new()
            .create(true)
            .append(true)
            .open(path)
            .and_then(|mut f| f.write_all(line.as_bytes()))
            .expect("write forge log");
    }

    pub fn emit_tombstone_audit(&mut self, entry: &OpEntry) {
        self.dies_tombstoned += 1;
        let mut extra = BTreeMap::new();
        extra.insert("op_id".into(), json!(entry.op_id));
        self.emit("op_tombstoned", entry, extra);
    }

    pub fn replay(&mut self, replay: &LoadedReplay) -> Result<(), String> {
        for entry in &replay.entries {
            self.apply_entry(entry)?;
        }
        for tomb in &replay.tombstone_audit {
            self.emit_tombstone_audit(tomb);
        }
        Ok(())
    }

    fn apply_entry(&mut self, entry: &OpEntry) -> Result<(), String> {
        self.try_apply_entry(entry)
    }

    pub fn try_apply_entry(&mut self, entry: &OpEntry) -> Result<(), String> {
        self.scenarios.insert(entry.scenario_tag.clone());
        match entry.op.as_str() {
            "forge_start" => {
                self.current_epoch = entry.forge_epoch;
                self.ledger.set_forge_epoch(entry.forge_epoch);
                let mut extra = BTreeMap::new();
                extra.insert("forge_epoch".into(), json!(entry.forge_epoch));
                self.emit("forge_started", entry, extra);
            }
            "die_bind" => {
                let path = die_path(&self.die_root, &entry.die_id);
                let (payload, checksum) = read_fdie_block(Path::new(&path))?;
                if self.ledger.has_die(&payload.die_id)
                    && self.ledger.die_checksum(&payload.die_id) == Some(checksum)
                {
                    return Ok(());
                }
                let record = DieRecord {
                    die_id: payload.die_id.clone(),
                    checksum,
                    tonnage: payload.tonnage,
                    forge_epoch: self.current_epoch,
                    source_format: payload.source_format,
                    revision: payload.revision,
                    digest_hex: payload.digest_hex,
                };
                self.ledger.bind_die(record);
                let mut extra = BTreeMap::new();
                extra.insert("die_id".into(), json!(payload.die_id));
                extra.insert("forge_epoch".into(), json!(self.current_epoch));
                self.emit("die_bound", entry, extra);
            }
            "die_sealed" => {
                self.dies_sealed += 1;
                let mut extra = BTreeMap::new();
                extra.insert("forge_epoch".into(), json!(entry.forge_epoch));
                self.emit("die_sealed", entry, extra);
            }
            "forge_purged" => {
                self.ledger.purge_not_on_epoch(self.current_epoch);
                let mut extra = BTreeMap::new();
                extra.insert("forge_epoch".into(), json!(self.current_epoch));
                self.emit("forge_purged", entry, extra);
            }
            other => return Err(format!("unknown op: {other}")),
        }
        Ok(())
    }
}
