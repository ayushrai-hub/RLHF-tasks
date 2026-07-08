use crate::errors::GateError;
use crate::mesh::mark_r;
use crate::model::{Ctx, View};

pub fn write_products(root: &crate::model::Root, view: &View) -> Result<(), GateError> {
    let row_lines: Vec<String> = view.row_obs.iter().map(|r| r.to_json()).collect();
    let dispatch_lines: Vec<String> = view.dispatch_obs.iter().map(|d| d.to_json()).collect();
    crate::io::append_jsonl(&root.row_obs_path(), &row_lines)?;
    crate::io::append_jsonl(&root.dispatch_obs_path(), &dispatch_lines)?;
    Ok(())
}

pub fn publish_ctx(ctx: &Ctx) -> Result<(), GateError> {
    let view = mark_r(ctx);
    write_products(&ctx.root, &view)
}
