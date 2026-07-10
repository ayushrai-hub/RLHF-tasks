mod model;
mod parser;
mod proof;

pub mod adjudicate {
    pub mod record;
}

pub mod appeal {
    pub mod replay;
}

pub mod judge {
    pub mod standings;
}

use std::env;
use std::fs;
use std::process;

fn main() {
    if let Err(message) = run() {
        eprintln!("rookline: {}", message);
        process::exit(1);
    }
}

fn run() -> Result<(), String> {
    let args: Vec<String> = env::args().collect();
    if args.len() < 2 || args[1] != "prove" {
        return Err("usage: rookline prove --cases <path> --out <path>".to_string());
    }

    let mut cases_path: Option<String> = None;
    let mut out_path: Option<String> = None;
    let mut index = 2;
    while index < args.len() {
        match args[index].as_str() {
            "--cases" => {
                index += 1;
                cases_path = args.get(index).cloned();
            }
            "--out" => {
                index += 1;
                out_path = args.get(index).cloned();
            }
            other => return Err(format!("unknown argument {}", other)),
        }
        index += 1;
    }

    let cases_path = cases_path.ok_or_else(|| "--cases is required".to_string())?;
    let out_path = out_path.ok_or_else(|| "--out is required".to_string())?;
    let raw = fs::read_to_string(&cases_path)
        .map_err(|err| format!("cannot read cases {}: {}", cases_path, err))?;
    let cases = parser::parse_cases(&raw)?;
    let proof = judge::standings::build_proof(&raw, &cases);
    if let Some(parent) = std::path::Path::new(&out_path).parent() {
        fs::create_dir_all(parent)
            .map_err(|err| format!("cannot create output directory {:?}: {}", parent, err))?;
    }
    fs::write(&out_path, proof).map_err(|err| format!("cannot write {}: {}", out_path, err))?;
    Ok(())
}
