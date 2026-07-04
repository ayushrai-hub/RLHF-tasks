use std::env;
use std::path::PathBuf;

use crate::errors::Err;
use crate::model::Cmd;

pub struct Parsed {
    pub root: PathBuf,
    pub cmd: Cmd,
}

pub fn parse() -> Result<Parsed, Err> {
    let mut args = env::args().skip(1);
    let verb = args.next().ok_or_else(|| {
        Err::new(
            1,
            "usage: znctl <init|apply-scope|normalize|reload> <workroot> [arg]",
        )
    })?;
    let root = args
        .next()
        .ok_or_else(|| Err::new(2, "missing workroot"))?;
    let root = PathBuf::from(root);
    let cmd = match verb.as_str() {
        "init" => {
            let case_id = args
                .next()
                .ok_or_else(|| Err::new(3, "init needs case id m1|m2|m3"))?;
            Cmd::Init { case_id }
        }
        "apply-scope" => {
            let scope_id = args.next().ok_or_else(|| {
                Err::new(4, "apply-scope needs scope id s1|s2|s3")
            })?;
            Cmd::ApplyScope { scope_id }
        }
        "normalize" => Cmd::Normalize,
        "reload" => Cmd::Reload,
        _ => return Err(Err::new(5, format!("unknown verb {verb}"))),
    };
    Ok(Parsed { root, cmd })
}
