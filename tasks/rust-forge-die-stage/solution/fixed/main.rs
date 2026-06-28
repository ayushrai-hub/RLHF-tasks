mod bundle;
mod digest;
mod fdie;
mod journal;
mod ledger;
mod pack;
mod recovery;
mod registry;
mod replay;
mod report;
mod state;
mod tonnage;

use crate::journal::load_replay;
use crate::ledger::{DieRecord, ForgeLedger};
use crate::recovery::{replay_with_recovery, write_atomic};
use crate::registry::{cached_registry, reset_cache_for_tests, truth_registry, CacheContext};
use crate::replay::ReplayContext;
use crate::report::{build_report, render_report};
use crate::state::{build_run_context, validate_or_quarantine, write_state};
use std::env;
use std::fs;
use std::path::PathBuf;

const DEFAULT_DIE_ROOT: &str = "/app/data/dies";
const DEFAULT_STATE_DIR: &str = "/app/output/state";
const DEFAULT_SNAPSHOT: &str = "/app/snapshot/forge_baseline.json";

fn main() {
    if let Err(err) = run() {
        eprintln!("forge_stage error: {err}");
        std::process::exit(1);
    }
}

fn run() -> Result<(), String> {
    let args: Vec<String> = env::args().collect();
    if args.len() < 2 {
        return Err(
            "usage: forge_stage --stage <journal-or-pack-or-bundle> ... | --stage-recover ... | --probe-forge-cache ..."
                .into(),
        );
    }
    match args[1].as_str() {
        "--probe-forge-cache" => probe_forge_cache(&args),
        "--stage" => {
            let events = flag_value(&args, "--stage")?;
            let log = flag_value(&args, "--emit-log")?;
            let report = optional_flag_value(&args, "--emit-report");
            let die_root = optional_flag_value(&args, "--die-root")
                .unwrap_or_else(|| DEFAULT_DIE_ROOT.to_string());
            let state_dir = optional_flag_value(&args, "--state-dir")
                .unwrap_or_else(|| DEFAULT_STATE_DIR.to_string());
            run_stage(&events, &log, report.as_deref(), &die_root, &state_dir)
        }
        "--stage-recover" => {
            let events = flag_value(&args, "--stage-recover")?;
            let log = flag_value(&args, "--emit-log")?;
            let report = optional_flag_value(&args, "--emit-report");
            let die_root = optional_flag_value(&args, "--die-root")
                .unwrap_or_else(|| DEFAULT_DIE_ROOT.to_string());
            let state_dir = optional_flag_value(&args, "--state-dir")
                .unwrap_or_else(|| DEFAULT_STATE_DIR.to_string());
            let snapshot = optional_flag_value(&args, "--snapshot")
                .unwrap_or_else(|| DEFAULT_SNAPSHOT.to_string());
            run_recover_stage(
                &events,
                &log,
                report.as_deref(),
                &die_root,
                &state_dir,
                &snapshot,
            )
        }
        other => Err(format!("unknown mode: {other}")),
    }
}

fn flag_value(args: &[String], name: &str) -> Result<String, String> {
    args.iter()
        .position(|a| a == name)
        .and_then(|i| args.get(i + 1))
        .cloned()
        .ok_or_else(|| format!("missing value for {name}"))
}

fn optional_flag_value(args: &[String], name: &str) -> Option<String> {
    args.iter()
        .position(|a| a == name)
        .and_then(|i| args.get(i + 1))
        .cloned()
}

fn prepare_output(path: &str) -> Result<(), String> {
    let p = PathBuf::from(path);
    if let Some(parent) = p.parent() {
        fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    }
    if p.exists() {
        fs::remove_file(&p).map_err(|e| e.to_string())?;
    }
    Ok(())
}

fn run_stage(
    events_path: &str,
    log_path: &str,
    report_path: Option<&str>,
    die_root: &str,
    state_dir: &str,
) -> Result<(), String> {
    prepare_output(log_path)?;
    if let Some(path) = report_path {
        prepare_output(path)?;
    }

    let replay = load_replay(events_path, die_root, DEFAULT_SNAPSHOT)?;
    let run_ctx = build_run_context(
        &replay.journal_digest,
        die_root,
        &replay.scenario_tag,
        replay.pack_generation,
        &replay.lineage_digest_hex,
        state_dir,
    );
    let (_prior, previous_generation) = validate_or_quarantine(state_dir, &run_ctx)?;

    let mut ctx = ReplayContext::from_replay(&replay, &replay.journal_digest);
    ctx.log_path = Some(log_path.to_string());
    ctx.warnings.extend(replay.warnings.clone());
    ctx.replay(&replay)?;

    let state_generation = write_state(state_dir, &ctx.ledger, &run_ctx, previous_generation)?;

    if let Some(path) = report_path {
        let body = build_report(&ctx, false, state_generation, None, None, &replay);
        write_atomic(path, &render_report(&body))?;
    }
    Ok(())
}

fn run_recover_stage(
    events_path: &str,
    log_path: &str,
    report_path: Option<&str>,
    die_root: &str,
    state_dir: &str,
    snapshot_path: &str,
) -> Result<(), String> {
    prepare_output(log_path)?;
    if let Some(path) = report_path {
        prepare_output(path)?;
    }

    let replay = load_replay(events_path, die_root, snapshot_path)?;
    let run_ctx = build_run_context(
        &replay.journal_digest,
        die_root,
        &replay.scenario_tag,
        replay.pack_generation,
        &replay.lineage_digest_hex,
        state_dir,
    );
    let (_prior, previous_generation) = validate_or_quarantine(state_dir, &run_ctx)?;

    let outcome = replay_with_recovery(
        events_path,
        die_root,
        snapshot_path,
        log_path,
        Some(state_dir),
    )?;
    let state_generation = if outcome.rollback {
        previous_generation
    } else {
        write_state(state_dir, &outcome.ledger, &run_ctx, previous_generation)?
    };

    if let Some(path) = report_path {
        let body = build_report(
            &outcome.ctx,
            outcome.rollback,
            state_generation,
            outcome.rollback_reason.as_deref(),
            outcome.snapshot_id.as_deref(),
            &replay,
        );
        write_atomic(path, &render_report(&body))?;
    }
    Ok(())
}

fn probe_forge_cache(args: &[String]) -> Result<(), String> {
    reset_cache_for_tests();
    let die_root = optional_flag_value(args, "--die-root")
        .unwrap_or_else(|| DEFAULT_DIE_ROOT.to_string());
    let stage_path = optional_flag_value(args, "--stage");
    let (journal_digest, lineage_digest_hex) = if let Some(path) = &stage_path {
        let replay = load_replay(path, &die_root, DEFAULT_SNAPSHOT)?;
        (replay.journal_digest, replay.lineage_digest_hex)
    } else {
        (String::new(), String::new())
    };

    let scenario_tag = "probe".to_string();
    let ctx = CacheContext {
        scenario_tag: scenario_tag.clone(),
        die_root: die_root.clone(),
        journal_digest: journal_digest.clone(),
        lineage_digest_hex: lineage_digest_hex.clone(),
        state_generation: 1,
    };

    let mut ledger = ForgeLedger::new();
    ledger.set_digest_context(&journal_digest, &die_root, &lineage_digest_hex);
    ledger.set_scenario_tag(&scenario_tag);
    ledger.set_forge_epoch(1);
    ledger.bind_die(DieRecord {
        die_id: "die_alpha_a".into(),
        checksum: 1,
        tonnage: 12000,
        forge_epoch: 1,
        source_format: "probe".into(),
        revision: None,
        digest_hex: String::new(),
    });
    ledger.bind_die(DieRecord {
        die_id: "die_alpha_b".into(),
        checksum: 2,
        tonnage: 68000,
        forge_epoch: 1,
        source_format: "probe".into(),
        revision: None,
        digest_hex: String::new(),
    });
    let first = cached_registry(&ledger, &ctx)?;

    ledger.bind_die(DieRecord {
        die_id: "die_beta_y".into(),
        checksum: 3,
        tonnage: 35000,
        forge_epoch: 1,
        source_format: "probe".into(),
        revision: None,
        digest_hex: String::new(),
    });
    let second = cached_registry(&ledger, &ctx)?;

    let migrated_ctx = CacheContext {
        scenario_tag: scenario_tag.clone(),
        die_root: die_root.clone(),
        journal_digest: journal_digest.clone(),
        lineage_digest_hex: lineage_digest_hex.clone(),
        state_generation: 2,
    };
    let migrated = cached_registry(&ledger, &migrated_ctx)?;

    let isolated_ctx = CacheContext {
        scenario_tag: "probe-isolated".into(),
        die_root: format!("{die_root}_isolated"),
        journal_digest: journal_digest.clone(),
        lineage_digest_hex: lineage_digest_hex.clone(),
        state_generation: 2,
    };
    let mut isolated_ledger = ledger.clone_state();
    isolated_ledger.restore_snapshot({
        let mut snap = std::collections::BTreeMap::new();
        snap.insert(
            "die_isolated".into(),
            DieRecord {
                die_id: "die_isolated".into(),
                checksum: 9,
                tonnage: 12000,
                forge_epoch: 1,
                source_format: "probe".into(),
                revision: None,
                digest_hex: String::new(),
            },
        );
        snap
    });
    let isolated = cached_registry(&isolated_ledger, &isolated_ctx)?;
    let truth = truth_registry(&ledger);
    let payload = serde_json::json!({
        "first": first,
        "second": second,
        "migrated": migrated,
        "isolated": isolated,
        "truth": truth,
    });
    println!("{}", serde_json::to_string(&payload).unwrap());
    Ok(())
}
