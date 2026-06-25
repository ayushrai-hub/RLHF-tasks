mod apply;
mod apply_staging;
mod chunk_digest;
mod chunk_staging;
mod chunks;
mod envelope_staging;
mod journal;
mod rollback;
mod rollback_staging;
mod session;
mod sig_canon;
mod signature;
mod types;
mod util;

fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.len() < 2 {
        eprintln!("invalid ota command");
        std::process::exit(1);
    }
    let result = match args[1].as_str() {
        "m1-verify" => signature::run_verify(&args[2..]),
        "m1-commit" => signature::run_commit(&args[2..]),
        "m1" => signature::run(&args[2..]),
        "m2-validate" => chunks::run_validate(&args[2..]),
        "m2-commit" => chunks::run_commit(&args[2..]),
        "m2" => chunks::run(&args[2..]),
        "m3-validate" => rollback::run_validate(&args[2..]),
        "m3-commit" => rollback::run_commit(&args[2..]),
        "m3" => rollback::run(&args[2..]),
        "m4-validate" => apply::run_validate(&args[2..]),
        "m4-commit" => apply::run_commit(&args[2..]),
        "m4" => apply::run(&args[2..]),
        _ => Err("unknown subcommand".to_string()),
    };
    if let Err(e) = result {
        eprintln!("invalid ota workflow: {e}");
        std::process::exit(1);
    }
}
