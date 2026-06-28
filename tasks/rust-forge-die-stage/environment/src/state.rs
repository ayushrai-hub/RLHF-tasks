use crate::digest::die_root_digest;
use crate::ledger::{DieRecord, ForgeLedger};
use serde::{Deserialize, Serialize};
use std::fs;
use std::io::Write;
use std::path::Path;
use std::time::{SystemTime, UNIX_EPOCH};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ForgeStateV1 {
    pub die_root: String,
    pub journal_digest: String,
    pub scenario_tag: String,
    pub pack_generation: u64,
    pub forge_epoch: u32,
    pub journal_revision: u64,
    pub dies: std::collections::BTreeMap<String, DieRecord>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ForgeStateV2 {
    pub schema_version: u64,
    pub commit_generation: u64,
    pub die_root: String,
    pub journal_digest: String,
    pub scenario_tag: String,
    pub pack_generation: u64,
    pub lineage_digest_hex: String,
    pub die_root_digest: String,
    pub snapshot_digest: String,
    pub forge_epoch: u32,
    pub journal_revision: u64,
    pub dies: std::collections::BTreeMap<String, DieRecord>,
}

pub struct RunContext {
    pub die_root: String,
    pub state_dir: String,
    pub journal_digest: String,
    pub scenario_tag: String,
    pub pack_generation: u64,
    pub lineage_digest_hex: String,
}

pub fn state_path(state_dir: &str) -> String {
    format!("{state_dir}/forge_state.json")
}

pub fn quarantine_stale_tmp(state_dir: &str) -> Result<(), String> {
    let tmp = format!("{state_dir}/forge_state.json.tmp");
    if !Path::new(&tmp).is_file() {
        return Ok(());
    }
    fs::create_dir_all(state_dir).map_err(|e| e.to_string())?;
    let stamp = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_millis())
        .unwrap_or(0);
    let quarantined = format!("{state_dir}/forge_state.quarantined.{stamp}.tmp");
    fs::rename(&tmp, &quarantined).map_err(|e| e.to_string())?;
    Ok(())
}

pub fn validate_or_quarantine(
    state_dir: &str,
    ctx: &RunContext,
) -> Result<(Option<ForgeLedger>, u64), String> {
    quarantine_stale_tmp(state_dir)?;
    let path = state_path(state_dir);
    if !Path::new(&path).is_file() {
        return Ok((None, 0));
    }
    let raw = fs::read_to_string(&path).map_err(|e| e.to_string())?;
    let value: serde_json::Value = match serde_json::from_str(&raw) {
        Ok(v) => v,
        Err(err) => {
            quarantine_state(state_dir, &format!("corrupt json: {err}"))?;
            return Ok((None, 0));
        }
    };
    if value.get("schema_version").and_then(|v| v.as_u64()) == Some(2) {
        let parsed: ForgeStateV2 = serde_json::from_value(value).map_err(|e| e.to_string())?;
        if parsed.die_root != ctx.die_root
            || parsed.journal_digest != ctx.journal_digest
            || parsed.scenario_tag != ctx.scenario_tag
            || parsed.pack_generation != ctx.pack_generation
            || parsed.lineage_digest_hex != ctx.lineage_digest_hex
        {
            quarantine_state(state_dir, "stale v2 state metadata")?;
            return Ok((None, 0));
        }
        let mut ledger = ForgeLedger::new();
        ledger.set_digest_context(
            &ctx.journal_digest,
            &ctx.die_root,
            &ctx.lineage_digest_hex,
        );
        ledger.set_scenario_tag(&ctx.scenario_tag);
        ledger.restore_full_state(parsed.dies, parsed.forge_epoch, parsed.journal_revision);
        return Ok((Some(ledger), parsed.commit_generation));
    }
    let parsed: ForgeStateV1 = serde_json::from_value(value).map_err(|e| e.to_string())?;
    if parsed.die_root != ctx.die_root
        || parsed.journal_digest != ctx.journal_digest
        || parsed.scenario_tag != ctx.scenario_tag
        || parsed.pack_generation != ctx.pack_generation
    {
        quarantine_state(state_dir, "stale v1 state metadata")?;
        return Ok((None, 0));
    }
    Ok((None, 0))
}

pub fn write_state(
    state_dir: &str,
    ledger: &ForgeLedger,
    ctx: &RunContext,
    previous_generation: u64,
) -> Result<u64, String> {
    fs::create_dir_all(state_dir).map_err(|e| e.to_string())?;
    let commit_generation = previous_generation.saturating_add(1).max(1);
    let root_digest = die_root_digest(&ctx.die_root)?;
    let body = ForgeStateV2 {
        schema_version: 2,
        commit_generation,
        die_root: ctx.die_root.clone(),
        journal_digest: ctx.journal_digest.clone(),
        scenario_tag: ctx.scenario_tag.clone(),
        pack_generation: ctx.pack_generation,
        lineage_digest_hex: ctx.lineage_digest_hex.clone(),
        die_root_digest: root_digest.clone(),
        snapshot_digest: ledger.ledger_digest_hex(),
        forge_epoch: ledger.forge_epoch(),
        journal_revision: ledger.journal_revision(),
        dies: ledger.snapshot(),
    };
    let path = state_path(state_dir);
    let tmp = format!("{path}.tmp");
    let rendered = serde_json::to_string_pretty(&body).unwrap() + "\n";
    fs::write(&tmp, &rendered).map_err(|e| e.to_string())?;
    if let Ok(file) = fs::OpenOptions::new().write(true).open(&tmp) {
        let _ = file.sync_all();
    }
    fs::rename(&tmp, &path).map_err(|e| e.to_string())?;
    Ok(commit_generation)
}

pub fn quarantine_state(state_dir: &str, reason: &str) -> Result<(), String> {
    let path = state_path(state_dir);
    if !Path::new(&path).is_file() {
        return Ok(());
    }
    fs::create_dir_all(state_dir).map_err(|e| e.to_string())?;
    let stamp = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_millis())
        .unwrap_or(0);
    let quarantined = format!("{state_dir}/forge_state.quarantined.{stamp}");
    fs::rename(&path, &quarantined).map_err(|e| e.to_string())?;
    let note = format!("{quarantined}.reason.txt");
    fs::write(&note, reason).map_err(|e| e.to_string())?;
    Ok(())
}

pub fn build_run_context(
    journal_digest: &str,
    die_root: &str,
    scenario_tag: &str,
    pack_generation: u64,
    lineage_digest_hex: &str,
    state_dir: &str,
) -> RunContext {
    RunContext {
        die_root: die_root.to_string(),
        state_dir: state_dir.to_string(),
        journal_digest: journal_digest.to_string(),
        scenario_tag: scenario_tag.to_string(),
        pack_generation,
        lineage_digest_hex: lineage_digest_hex.to_string(),
    }
}
