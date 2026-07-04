use std::path::PathBuf;

use crate::errors::Err;
use crate::model::Ctx;
use crate::parse_stage::expand_includes;
use crate::pivot::{op_a, Node};

pub fn fixture_path(case_id: &str) -> Result<PathBuf, Err> {
    let base = PathBuf::from("/app/environment/fixtures/masters").join(case_id);
    if !base.is_dir() {
        return Err(Err::new(60, "unknown case"));
    }
    Ok(base)
}

pub fn scope_path(scope_id: &str) -> Result<PathBuf, Err> {
    let p = PathBuf::from("/app/environment/fixtures/scopes")
        .join(scope_id)
        .join("seed.bin");
    if !p.is_file() {
        return Err(Err::new(61, "unknown scope"));
    }
    Ok(p)
}

pub fn ingest(ctx: &mut Ctx) -> Result<(), Err> {
    let src_dir = ctx.root.src_dir();
    let root_path = src_dir.join("root.master");
    let text = crate::io::read_text(&root_path)?;
    let (rows, edges) = expand_includes(&src_dir, "root.master", &text, "example.com.")?;
    ctx.rows = rows;
    ctx.edges = edges;
    let nodes = vec![Node {
        name: "root.master".to_string(),
    }];
    ctx.edges = op_a(ctx, &nodes);
    Ok(())
}
