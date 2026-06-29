use clap::{Parser, Subcommand};
use meridian_api::handle_event;
use meridian_proto::{encode_record, EventRecord, RecordKind};
use meridian_sync::CheckpointStore;

#[derive(Parser)]
#[command(name = "meridian-cli")]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    Demo,
    Hash { payload: String },
}

fn main() {
    let cli = Cli::parse();
    match cli.command {
        Commands::Demo => {
            let mut store = CheckpointStore::new();
            store.seed_demo().expect("seed demo checkpoint");
            let checkpoint = store.snapshot().expect("checkpoint present");
            let first = checkpoint.records.first().expect("record present");
            let encoded = encode_record(first).expect("encode record");
            let digest = handle_event(&encoded).expect("handle event");
            println!("digest={digest}");
        }
        Commands::Hash { payload } => {
            let record = EventRecord::new(99, RecordKind::Delta, payload);
            let encoded = encode_record(&record).expect("encode record");
            let digest = handle_event(&encoded).expect("handle event");
            println!("digest={digest}");
        }
    }
}
