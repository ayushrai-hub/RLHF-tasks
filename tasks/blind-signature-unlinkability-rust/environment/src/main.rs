use clap::Parser;
use std::path::PathBuf;
use std::process;

mod config;
mod types;
mod parser;
mod analyzer;
mod correlation;
mod matching;
mod timing;
mod entropy;
mod batch;
mod adversary;
mod commitment;
mod reporter;

#[derive(Parser)]
#[command(name = "blind-signature-unlinkability")]
struct Cli {
    #[arg(long)]
    config_dir: PathBuf,
    #[arg(long)]
    data_file: PathBuf,
    #[arg(long)]
    output: PathBuf,
}

fn main() {
    let cli = Cli::try_parse();
    let cli = match cli {
        Ok(c) => c,
        Err(e) => {
            eprintln!("{}", e);
            process::exit(1);
        }
    };

    let settings = config::load_config(&cli.config_dir);
    let input = parser::parse_input(&cli.data_file);
    let report = analyzer::analyze(&input, &settings);
    reporter::write_report(&report, &cli.output);
}
