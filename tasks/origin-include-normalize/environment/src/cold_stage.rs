use crate::errors::Err;
use crate::braid::fold_b;
use crate::grain::step_d;
use crate::model::{Ctx, Mode};

pub fn run(ctx: &mut Ctx) -> Result<(), Err> {
    let merged = fold_b(ctx, ctx.snap.clone())?;
    ctx.rows = merged;
    let _evs = step_d(ctx, Mode::Cold);
    Ok(())
}
