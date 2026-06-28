use crate::digest::die_root_digest;
use crate::ledger::ForgeLedger;
use serde_json::{json, Value};
use std::collections::BTreeMap;

#[derive(Clone, PartialEq, Eq)]
struct CacheKey {
    scenario_tag: String,
    forge_epoch: u32,
    journal_revision: u64,
    journal_digest: String,
    lineage_digest_hex: String,
    die_root_digest: String,
    state_generation: u64,
}

static mut CACHE_KEY: Option<CacheKey> = None;
static mut CACHE_BLOB: Option<Value> = None;

pub struct CacheContext {
    pub scenario_tag: String,
    pub die_root: String,
    pub journal_digest: String,
    pub lineage_digest_hex: String,
    pub state_generation: u64,
}

pub fn cached_registry(index: &ForgeLedger, ctx: &CacheContext) -> Result<Value, String> {
    let key = CacheKey {
        scenario_tag: ctx.scenario_tag.clone(),
        forge_epoch: index.forge_epoch(),
        journal_revision: index.journal_revision(),
        journal_digest: ctx.journal_digest.clone(),
        lineage_digest_hex: ctx.lineage_digest_hex.clone(),
        die_root_digest: die_root_digest(&ctx.die_root)?,
        state_generation: ctx.state_generation,
    };
    unsafe {
        if let (Some(cached_key), Some(blob)) = (&CACHE_KEY, &CACHE_BLOB) {
            if *cached_key == key {
                return Ok(blob.clone());
            }
        }
        let snap = build_snapshot(index, &key);
        CACHE_KEY = Some(key);
        CACHE_BLOB = Some(snap.clone());
        Ok(snap)
    }
}

fn build_snapshot(index: &ForgeLedger, key: &CacheKey) -> Value {
    let mut dies = BTreeMap::new();
    for (die_id, rec) in index.snapshot() {
        dies.insert(
            die_id,
            json!({
                "checksum": rec.checksum,
                "tonnage": rec.tonnage,
                "forge_epoch": rec.forge_epoch
            }),
        );
    }
    json!({
        "forge_epoch": key.forge_epoch,
        "journal_revision": key.journal_revision,
        "dies": dies,
        "die_count": dies.len(),
        "scenario_tag": key.scenario_tag,
        "journal_digest": key.journal_digest,
        "lineage_digest_hex": key.lineage_digest_hex,
        "die_root_digest": key.die_root_digest,
        "state_generation": key.state_generation,
    })
}

pub fn reset_cache_for_tests() {
    unsafe {
        CACHE_KEY = None;
        CACHE_BLOB = None;
    }
}

pub fn truth_registry(index: &ForgeLedger) -> Value {
    json!({
        "forge_epoch": index.forge_epoch(),
        "journal_revision": index.journal_revision(),
        "die_count": index.die_count(),
    })
}
