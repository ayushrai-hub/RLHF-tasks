use std::process::ExitCode;

use neural_echo_forge::{run_export, run_ingest, run_reconcile};

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().collect();
    let mode = args.get(1).map(String::as_str).unwrap_or("run");

    match mode {
        "ingest" => match run_ingest() {
            Ok(skipped) if skipped > 0 => ExitCode::from(3),
            Ok(_) => ExitCode::SUCCESS,
            Err(err) => {
                eprintln!("{err}");
                ExitCode::from(2)
            }
        },
        "reconcile" => match run_reconcile() {
            Ok(()) => ExitCode::SUCCESS,
            Err(err) => {
                eprintln!("{err}");
                ExitCode::from(2)
            }
        },
        "export" => match run_export() {
            Ok(()) => ExitCode::SUCCESS,
            Err(err) => {
                eprintln!("{err}");
                ExitCode::from(2)
            }
        },
        "run" => {
            let skipped = match run_ingest() {
                Ok(s) => s,
                Err(err) => {
                    eprintln!("{err}");
                    return ExitCode::from(2);
                }
            };
            if let Err(err) = run_reconcile() {
                eprintln!("{err}");
                return ExitCode::from(2);
            }
            if let Err(err) = run_export() {
                eprintln!("{err}");
                return ExitCode::from(2);
            }
            if skipped > 0 {
                ExitCode::from(3)
            } else {
                ExitCode::SUCCESS
            }
        }
        _ => {
            eprintln!("usage: neural-echo-forge [ingest|reconcile|export|run]");
            ExitCode::from(2)
        }
    }
}
