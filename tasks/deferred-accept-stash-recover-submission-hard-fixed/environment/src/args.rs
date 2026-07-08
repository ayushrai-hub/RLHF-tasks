use std::env;
use std::path::PathBuf;

use crate::errors::GateError;
use crate::model::Mode;

pub struct Parsed {
    pub root: PathBuf,
    pub mode: Mode,
}

pub fn parse() -> Result<Parsed, GateError> {
    let mut args: Vec<String> = env::args().skip(1).collect();
    if args.len() < 2 {
        return Err(GateError::new(1, usage()));
    }
    let cmd = args.remove(0);
    let root = PathBuf::from(args.remove(0));
    let mode = match cmd.as_str() {
        "open" => {
            let sample = args
                .first()
                .ok_or_else(|| GateError::new(1, usage()))?
                .clone();
            Mode::Open { sample }
        }
        "offer" => {
            let tag = args
                .first()
                .ok_or_else(|| GateError::new(1, usage()))?
                .clone();
            Mode::Offer { tag }
        }
        "cycle" => Mode::Cycle {
            partial: args.iter().any(|a| a == "--partial"),
        },
        "raise" => Mode::Raise,
        "sweep" => Mode::Sweep {
            again: args.iter().any(|a| a == "--again"),
        },
        _ => return Err(GateError::new(1, usage())),
    };
    Ok(Parsed { root, mode })
}

fn usage() -> String {
    "gatectl open <workroot> <sample> | offer <workroot> <tag> | cycle <workroot> [--partial] | raise <workroot> | sweep <workroot> [--again]".to_string()
}
