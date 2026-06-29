//! `kettleheat` — an offline, deterministic process-kettle element cycle ledger.
//!
//! Reads one JSON document (a kettle-temperature/power-mode event log plus
//! controller parameters) from stdin or a file path argument, replays the
//! controller, and prints the reconstructed element-ON intervals as JSON. The
//! input format and the control/interval contract live in docs/spec.md.

mod control;
mod json;
mod parse;

use std::io::Read;
use std::process::exit;

fn read_input() -> std::io::Result<String> {
    let args: Vec<String> = std::env::args().skip(1).collect();
    if let Some(path) = args.first() {
        std::fs::read_to_string(path)
    } else {
        let mut buf = String::new();
        std::io::stdin().read_to_string(&mut buf)?;
        Ok(buf)
    }
}

fn main() {
    let input = match read_input() {
        Ok(s) => s,
        Err(e) => {
            eprintln!("error: cannot read input: {}", e);
            exit(1);
        }
    };

    let problem = match parse::parse(&input) {
        Ok(p) => p,
        Err(e) => {
            eprintln!("error: {}", e.0);
            exit(1);
        }
    };

    match control::run(&problem) {
        Ok(ledger) => {
            print!("{}", ledger.to_json());
        }
        Err(e) => {
            eprintln!("error: {}", e);
            exit(1);
        }
    }
}
