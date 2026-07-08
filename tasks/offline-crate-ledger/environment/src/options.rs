use std::env;
use std::path::{Path, PathBuf};

#[derive(Default)]
pub struct Options {
    pub workspace: String,
    pub registry: String,
    pub lock: String,
    pub report: String,
}

pub fn parse_args() -> Result<Options, String> {
    let mut opts = Options::default();
    let mut args = env::args().skip(1);
    while let Some(flag) = args.next() {
        let value = args.next().ok_or_else(|| format!("missing value for {flag}"))?;
        match flag.as_str() {
            "--workspace" => opts.workspace = value,
            "--registry" => opts.registry = value,
            "--lock" => opts.lock = value,
            "--report" => opts.report = value,
            _ => return Err(format!("unknown flag {flag}")),
        }
    }
    if opts.workspace.is_empty()
        || opts.registry.is_empty()
        || opts.lock.is_empty()
        || opts.report.is_empty()
    {
        return Err("crateledger --workspace <absolute-file> --registry <absolute-dir> --lock <absolute-file> --report <absolute-file>".to_string());
    }
    for path in [&opts.workspace, &opts.registry, &opts.lock, &opts.report] {
        if !PathBuf::from(path).is_absolute() {
            return Err("all paths must be absolute".to_string());
        }
    }
    Ok(opts)
}

pub fn validate_inputs(opts: &Options) -> Result<(), String> {
    if !Path::new(&opts.workspace).is_file() {
        return Err("workspace file does not exist".to_string());
    }
    if !Path::new(&opts.registry).is_dir() {
        return Err("registry directory does not exist".to_string());
    }
    Ok(())
}
