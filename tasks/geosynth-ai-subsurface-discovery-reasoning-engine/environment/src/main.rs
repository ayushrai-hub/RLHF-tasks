mod apex;
mod lamina;
mod weft;

use apex::{discovery_trails, qrvn_g5st};
use lamina::{qrvn_g1pd, qrvn_g2tm};
use weft::{qrvn_g3lk, qrvn_g4gd};

fn run_python_branch() -> Result<(), String> {
    let status = std::process::Command::new("python3")
        .args(["-m", "geokit.qrvn_f7br.splitter"])
        .env("PYTHONPATH", "/app")
        .current_dir("/app")
        .status()
        .map_err(|e| e.to_string())?;
    if status.success() {
        Ok(())
    } else {
        Err("formation branch planner failed".into())
    }
}

fn validate_discovery() -> Result<(), String> {
    let data = std::fs::read_to_string("/app/output/geosynth-discovery-report.json")
        .map_err(|e| e.to_string())?;
    let report: serde_json::Value = serde_json::from_str(&data).map_err(|e| e.to_string())?;
    if report["discovery_store"].as_str() != Some("geosynth-bundled") {
        return Err("unexpected discovery_store".into());
    }
    let fp = report["discovery_fingerprint"].as_str().unwrap_or("");
    if fp.len() != 64 {
        return Err("discovery_fingerprint must be 64 hex chars".into());
    }
    let blocks = report["blocks"].as_array().ok_or("blocks missing")?;
    if blocks.len() < 3 {
        return Err("need three block rows".into());
    }
    Ok(())
}

fn discovery_seal() -> Result<(), String> {
    let report: serde_json::Value = serde_json::from_str(
        &std::fs::read_to_string("/app/output/geosynth-discovery-report.json").map_err(|e| e.to_string())?,
    )
    .map_err(|e| e.to_string())?;
    let staging: serde_json::Value = serde_json::from_str(
        &std::fs::read_to_string("/app/state/formation-compose-staging.json").map_err(|e| e.to_string())?,
    )
    .map_err(|e| e.to_string())?;
    let guard: serde_json::Value = serde_json::from_str(
        &std::fs::read_to_string("/app/state/hypothesis-guard-ledger.json").map_err(|e| e.to_string())?,
    )
    .map_err(|e| e.to_string())?;
    let bind = serde_json::json!({
        "consolidation_epoch": 3,
        "status": "finalized",
        "discovery_fingerprint": report["discovery_fingerprint"],
        "formation_compose_digest": staging["formation_compose_digest"],
        "bound_guard_digest": guard["guard_digest"],
    });
    std::fs::write(
        "/app/state/discovery-export-bind.json",
        serde_json::to_string_pretty(&bind).unwrap() + "\n",
    )
    .unwrap();
    let seal = serde_json::json!({
        "seal": "discovery-seal",
        "discovery_fingerprint": report["discovery_fingerprint"],
    });
    std::fs::write(
        "/app/output/discovery-seal.json",
        serde_json::to_string_pretty(&seal).unwrap() + "\n",
    )
    .unwrap();
    Ok(())
}

fn dispatch(cmd: &str) -> Result<(), String> {
    match cmd {
        "load-surveys" => qrvn_g1pd::run(),
        "depth-epoch" => qrvn_g2tm::run(),
        "fuse-voxels" => qrvn_g3lk::run(),
        "guard-hypotheses" => qrvn_g4gd::run(),
        "score-confidence" => qrvn_g5st::run(),
        "branch-formations" => run_python_branch(),
        "export-discovery" => discovery_trails::run(),
        "validate-discovery" => validate_discovery(),
        "discovery-seal" => discovery_seal(),
        "discovery-run" => {
            qrvn_g1pd::run()
                .and_then(|_| qrvn_g2tm::run())
                .and_then(|_| qrvn_g3lk::run())
                .and_then(|_| qrvn_g4gd::run())
                .and_then(|_| qrvn_g5st::run())
                .and_then(|_| run_python_branch())
                .and_then(|_| discovery_trails::run())
                .and_then(|_| discovery_seal())
        }
        _ => Err(format!("unknown command {cmd}")),
    }
}

fn main() {
    if std::env::args().len() < 2 {
        eprintln!(
            "usage: geosynth <load-surveys|depth-epoch|fuse-voxels|guard-hypotheses|score-confidence|branch-formations|export-discovery|validate-discovery|discovery-seal|discovery-run>"
        );
        std::process::exit(2);
    }
    let cmd = std::env::args().nth(1).unwrap();
    if let Err(err) = dispatch(&cmd) {
        eprintln!("{err}");
        std::process::exit(1);
    }
}
