use crate::{db, decode, export, ledger, persist, seal, snapshot, types};

pub fn run(args: Vec<String>) -> Result<(), String> {
    if args.is_empty() {
        return Err("usage: rtcmctl <command> [flags]".into());
    }
    match args[0].as_str() {
        "init" => cmd_init(&args[1..]),
        "decode" => cmd_decode(&args[1..]),
        "stage" => cmd_stage(&args[1..]),
        "persist" => cmd_persist(&args[1..]),
        "ingest" => cmd_ingest(&args[1..]),
        "publish-ledger" => cmd_publish_ledger(&args[1..]),
        "seal-mutations" => cmd_seal(&args[1..]),
        "refresh-snapshot" => cmd_refresh(&args[1..]),
        "export" => cmd_export(&args[1..]),
        other => Err(format!("unknown command: {other}")),
    }
}

fn flag_value(args: &[String], name: &str) -> Result<String, String> {
    let mut i = 0;
    while i < args.len() {
        if args[i] == name {
            if i + 1 >= args.len() {
                return Err(format!("missing value for {name}"));
            }
            return Ok(args[i + 1].clone());
        }
        i += 1;
    }
    Err(format!("required flag {name} not found"))
}

fn has_flag(args: &[String], name: &str) -> bool {
    args.iter().any(|a| a == name)
}

fn cmd_init(args: &[String]) -> Result<(), String> {
    let db = flag_value(args, "--db")?;
    db::init(&db)
}

fn cmd_decode(args: &[String]) -> Result<(), String> {
    let capture = flag_value(args, "--capture")?;
    let ledger = flag_value(args, "--ledger").unwrap_or_else(|_| types::DEFAULT_LEDGER.to_string());
    decode::run(&capture, &ledger)
}

fn cmd_stage(args: &[String]) -> Result<(), String> {
    let ledger = flag_value(args, "--ledger")?;
    let staged = flag_value(args, "--staged").unwrap_or_else(|_| types::DEFAULT_STAGED.to_string());
    crate::stage::run(&ledger, &staged)
}

fn cmd_persist(args: &[String]) -> Result<(), String> {
    let db = flag_value(args, "--db")?;
    let staged = flag_value(args, "--staged")?;
    let ingest_at = flag_value(args, "--ingest-at")?;
    persist::run(&db, &staged, &ingest_at)
}

fn cmd_ingest(args: &[String]) -> Result<(), String> {
    let db = flag_value(args, "--db")?;
    let capture = flag_value(args, "--capture")?;
    let ingest_at = flag_value(args, "--ingest-at")?;
    let ledger = types::DEFAULT_LEDGER.to_string();
    let staged = types::DEFAULT_STAGED.to_string();
    decode::run(&capture, &ledger)?;
    crate::stage::run(&ledger, &staged)?;
    persist::run(&db, &staged, &ingest_at)
}

fn cmd_publish_ledger(args: &[String]) -> Result<(), String> {
    let db = flag_value(args, "--db")?;
    ledger::publish(&db)
}

fn cmd_seal(args: &[String]) -> Result<(), String> {
    let db = flag_value(args, "--db")?;
    seal::seal(&db)
}

fn cmd_refresh(args: &[String]) -> Result<(), String> {
    let db = flag_value(args, "--db")?;
    let as_of = flag_value(args, "--as-of")?;
    snapshot::refresh(&db, &as_of)
}

fn cmd_export(args: &[String]) -> Result<(), String> {
    let db = flag_value(args, "--db")?;
    let as_of = flag_value(args, "--as-of")?;
    if !has_flag(args, "json") {
        return Err("export requires json flag".into());
    }
    export::run(&db, &as_of)
}
