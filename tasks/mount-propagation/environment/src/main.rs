use mount_propagation_desk::{run_scenario, write_matrix};
use std::env;
use std::process;

fn main() {
    let args: Vec<String> = env::args().collect();
    if args.len() != 3 || args[1] != "--scenario" {
        eprintln!("usage: ctl_r7 --scenario <slug>");
        process::exit(2);
    }
    match run_scenario(&args[2]) {
        Ok(record) => {
            if let Err(err) = write_matrix(&record) {
                eprintln!("{err}");
                process::exit(1);
            }
        }
        Err(err) => {
            eprintln!("{err}");
            process::exit(1);
        }
    }
}
