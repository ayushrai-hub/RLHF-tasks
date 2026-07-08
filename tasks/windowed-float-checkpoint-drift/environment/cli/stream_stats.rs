use clap::{Parser, Subcommand};

use crate::flow::{run_cold, run_resume};

#[derive(Parser)]
#[command(name = "stream-stats")]
struct Cli {
    #[command(subcommand)]
    cmd: Commands,
}

#[derive(Subcommand)]
enum Commands {
    Run {
        #[arg(long)]
        profile: String,
        #[arg(long)]
        seed: u64,
    },
    Resume {
        #[arg(long = "from-checkpoint")]
        from_checkpoint: String,
        #[arg(long)]
        seed: u64,
    },
}

pub fn stream_stats_main() -> i32 {
    let cli = Cli::parse();
    let result = match cli.cmd {
        Commands::Run { profile, seed } => {
            if profile != "cold" {
                eprintln!("unsupported profile");
                return 2;
            }
            run_cold(seed)
        }
        Commands::Resume {
            from_checkpoint,
            seed,
        } => run_resume(seed, std::path::Path::new(&from_checkpoint)),
    };
    match result {
        Ok(()) => 0,
        Err(e) => {
            eprintln!("{e}");
            1
        }
    }
}
