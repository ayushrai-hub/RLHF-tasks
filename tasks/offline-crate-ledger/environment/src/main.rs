mod lock;
mod model;
mod options;
mod registry;
mod report;
mod resolve;
mod version;
mod workspace;

fn main() {
    match real_main() {
        Ok(code) => std::process::exit(code),
        Err((code, msg)) => {
            eprintln!("{msg}");
            std::process::exit(code);
        }
    }
}

fn real_main() -> Result<i32, (i32, String)> {
    let opts = options::parse_args().map_err(|e| (2, e))?;
    options::validate_inputs(&opts).map_err(|e| (2, e))?;
    let roots =
        workspace::parse_workspace(std::path::Path::new(&opts.workspace)).map_err(|e| (2, e))?;
    match resolve::resolve(&opts, roots) {
        Ok(lock_json) => {
            let report_json = "{\n  \"conflicts\": []\n}\n".to_string();
            report::write_output(&opts.report, &report_json).map_err(|e| (1, e))?;
            report::write_output(&opts.lock, &lock_json).map_err(|e| (1, e))?;
            Ok(0)
        }
        Err(conflicts) => {
            let report = report::conflict_report(&conflicts);
            report::write_output(&opts.report, &report).map_err(|e| (1, e))?;
            report::write_output(&opts.lock, "{\n  \"packages\": []\n}\n").map_err(|e| (1, e))?;
            Ok(2)
        }
    }
}
