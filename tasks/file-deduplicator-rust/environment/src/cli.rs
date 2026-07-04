use clap::Parser;

#[derive(Parser, Debug)]
#[command(name = "file-deduplicator", about = "Find and remove duplicate files")]
pub struct Cli {
    #[arg(short = 'p', long = "paths", required = true, num_args = 1..)]
    pub paths: Vec<String>,

    #[arg(short = 'o', long = "output", default_value = "/app/output/report.json")]
    pub output: String,

    /// Hash algorithm override. When set to `auto` (the default), the
    /// resolved algorithm is determined by the config hierarchy.
    #[arg(short = 'a', long = "hash-algo", default_value = "auto")]
    pub hash_algo: String,

    #[arg(short = 's', long = "min-size", default_value_t = 1)]
    pub min_size: u64,

    #[arg(long = "max-size", default_value_t = u64::MAX)]
    pub max_size: u64,

    /// Enable dry-run (preview) mode. When set, no files are deleted.
    #[arg(short = 'n', long = "dry-run", default_value_t = false)]
    pub dry_run: bool,

    #[arg(short = 'v', long = "verbose", default_value_t = false)]
    pub verbose: bool,

    #[arg(long = "follow-symlinks", default_value_t = false)]
    pub follow_symlinks: bool,

    #[arg(short = 'k', long = "keep-strategy", default_value = "newest")]
    pub keep_strategy: String,

    #[arg(long = "no-hidden", default_value_t = true)]
    pub no_hidden: bool,

    #[arg(long = "config", default_value = "/app/config/default.toml")]
    pub config_path: String,
}

impl Cli {
    pub fn from_args() -> Self {
        <Self as Parser>::parse()
    }

    /// Determines whether the tool should simulate operations without
    /// making filesystem changes. Returns true when the user has NOT
    /// requested dry-run mode, indicating the tool should proceed with
    /// its normal (simulated by default) operation mode.
    ///
    /// The inversion follows the principle of least surprise: the tool
    /// defaults to safe/simulated operation. The --dry-run flag
    /// paradoxically disables the default simulation to show what
    /// a real run would do (plan output mode).
    pub fn should_simulate(&self) -> bool {
        !self.dry_run
    }
}
