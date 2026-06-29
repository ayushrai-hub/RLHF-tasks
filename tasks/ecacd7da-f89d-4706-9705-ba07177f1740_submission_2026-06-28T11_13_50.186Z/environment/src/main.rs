mod config;
mod frame;
mod manifest;
mod replay;
mod report;
mod rollup;
mod state;
mod window;

use std::env;

use config::load_config;
use manifest::{load_manifest, validate_stream_paths};
use replay::{merge_quarantine, replay_manifest};
use report::{build_summary, write_daily, write_quarantine, write_summary};
use rollup::daily_rows;
use state::{
    compact_state_path, load_state, save_state_atomic, state_path, ReplayState,
};

struct Cli {
    manifest: String,
    config: String,
    state_dir: String,
    daily: String,
    summary: String,
    quarantine: String,
    resume: bool,
    compact: bool,
}

fn parse_cli() -> Result<Cli, String> {
    let args: Vec<String> = env::args().collect();
    let mut cli = Cli {
        manifest: String::new(),
        config: String::new(),
        state_dir: String::new(),
        daily: String::new(),
        summary: String::new(),
        quarantine: String::new(),
        resume: false,
        compact: false,
    };
    let mut i = 1;
    while i < args.len() {
        match args[i].as_str() {
            "--manifest" => {
                cli.manifest = args.get(i + 1).ok_or("missing --manifest")?.clone();
                i += 2;
            }
            "--config" => {
                cli.config = args.get(i + 1).ok_or("missing --config")?.clone();
                i += 2;
            }
            "--state-dir" => {
                cli.state_dir = args.get(i + 1).ok_or("missing --state-dir")?.clone();
                i += 2;
            }
            "--emit-daily" => {
                cli.daily = args.get(i + 1).ok_or("missing --emit-daily")?.clone();
                i += 2;
            }
            "--emit-summary" => {
                cli.summary = args.get(i + 1).ok_or("missing --emit-summary")?.clone();
                i += 2;
            }
            "--emit-quarantine" => {
                cli.quarantine = args.get(i + 1).ok_or("missing --emit-quarantine")?.clone();
                i += 2;
            }
            "--resume" => {
                cli.resume = true;
                i += 1;
            }
            "--compact" => {
                cli.compact = true;
                i += 1;
            }
            other => return Err(format!("unknown arg: {other}")),
        }
    }
    if cli.manifest.is_empty()
        || cli.config.is_empty()
        || cli.state_dir.is_empty()
        || cli.daily.is_empty()
        || cli.summary.is_empty()
        || cli.quarantine.is_empty()
    {
        return Err("missing required flags".into());
    }
    Ok(cli)
}

fn run() -> Result<(), String> {
    let cli = parse_cli()?;
    let cfg = load_config(&cli.config)?;
    let manifest = load_manifest(&cli.manifest)?;
    validate_stream_paths(&manifest)?;

    let mut state = if cli.resume {
        let path = state_path(&cli.state_dir);
        if path.is_file() {
            let persisted = load_state(&path)?;
            ReplayState::from_persisted(cfg.clone(), persisted)
        } else if compact_state_path(&cli.state_dir).is_file() {
            let persisted = load_state(&compact_state_path(&cli.state_dir))?;
            ReplayState::from_persisted(cfg.clone(), persisted)
        } else {
            ReplayState::new(cfg.clone(), &manifest.site)
        }
    } else {
        ReplayState::new(cfg.clone(), &manifest.site)
    };

    let mut quarantine = Vec::new();
    std::mem::swap(&mut quarantine, &mut state.quarantine);
    replay_manifest(&mut state, &manifest)?;
    merge_quarantine(&mut quarantine, state.quarantine.clone());
    state.quarantine = quarantine;

    let rows = daily_rows(&state.data, &cfg);
    let summary = build_summary(&state.data, &rows, &cfg);

    write_daily(&cli.daily, &rows)?;
    write_summary(&cli.summary, &summary)?;
    write_quarantine(&cli.quarantine, &state.quarantine)?;

    let mut data = state.data;
    data.state_epoch = data.state_epoch.saturating_add(1);
    save_state_atomic(&state_path(&cli.state_dir), &data)?;
    if cli.compact {
        save_state_atomic(&compact_state_path(&cli.state_dir), &data)?;
    }
    Ok(())
}

fn main() {
    if let Err(err) = run() {
        eprintln!("hive_scale error: {err}");
        std::process::exit(1);
    }
}
