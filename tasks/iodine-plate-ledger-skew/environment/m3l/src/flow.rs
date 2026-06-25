use crate::emit;
use crate::pool;
use crate::scan;
use crate::trim;
use std::path::PathBuf;

pub fn drive(args: impl Iterator<Item = String>) {
    let mut args = args;
    let _cmd = args.next().unwrap_or_default();
    let mut scenario = String::new();
    let mut output = PathBuf::new();
    while let Some(flag) = args.next() {
        match flag.as_str() {
            "--scenario" | "--pack" | "--bundle" | "--profile" | "--table"
    | "--checkpoint" | "--cache" | "--shard" | "--frame" | "--delta" | "--ring" | "--blob"
    | "--segment" | "--crate" | "--journal" | "--manifest" | "--index" | "--ledger" => {
                scenario = args.next().unwrap_or_default();
            }
            "--output" => output = PathBuf::from(args.next().unwrap_or_default()),
            _ => {}
        }
    }
    if scenario.is_empty() || output.as_os_str().is_empty() {
        eprintln!("missing scenario or output");
        std::process::exit(2);
    }
    let meta_path = PathBuf::from("/app/fixtures/scenarios").join(format!("{scenario}.json"));
    let meta = scan::load_meta(&meta_path);
    let seg_dir = PathBuf::from("/app/fixtures/segments").join(&scenario);
    let mut engine = pool::Engine::new(&seg_dir, &meta);
    if let Some(marker) = meta.prune_below {
        trim::apply_floor_cut(&mut engine, marker);
    } else if let Some(marker) = meta.rollback_after {
        trim::apply(&mut engine, marker);
    }
    engine.run();
    let cached = r8k::slot::read_head(&scenario, engine.applied);
    let rep = emit::build(&engine, &scenario, cached);
    emit::write_json(&output, &rep);
}
