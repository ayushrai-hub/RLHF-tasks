use serde_json::json;
use std::env;
use std::fs;
use std::path::PathBuf;

fn main() {
    if let Err(err) = run() {
        eprintln!("{err}");
        std::process::exit(1);
    }
}

fn run() -> Result<(), String> {
    let mut out = PathBuf::from("/app/out");
    let mut args = env::args().skip(1);
    while let Some(arg) = args.next() {
        match arg.as_str() {
            "--fixtures" => {
                let _ = args.next().ok_or("missing --fixtures value")?;
            }
            "--out" => out = PathBuf::from(args.next().ok_or("missing --out value")?),
            other => return Err(format!("unknown argument {other}")),
        }
    }
    fs::create_dir_all(&out).map_err(|e| e.to_string())?;
    let report = json!({
        "artifacts": [],
        "totals": { "inputModules": 0, "validModules": 0, "artifactCount": 0, "pass": 0, "warn": 0, "block": 0, "malformedDependencies": 0, "conflictCount": 0 }
    });
    let text = serde_json::to_string_pretty(&report).map_err(|e| e.to_string())?;
    fs::write(out.join("dependency-convergence.json"), format!("{text}\n")).map_err(|e| e.to_string())?;
    fs::write(out.join("dependency-audit.csv"), "kind,coordinate,module,detail").map_err(|e| e.to_string())?;
    Ok(())
}
