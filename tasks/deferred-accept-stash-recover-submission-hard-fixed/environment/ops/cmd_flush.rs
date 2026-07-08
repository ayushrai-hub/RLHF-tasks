use crate::apply::{accept_stashed, dispatch_waiting};
use crate::checks::validate_root;
use crate::errors::GateError;
use crate::model::{Ctx, Mode};
use crate::prime::step_d;
use crate::render::publish_ctx;
use crate::stow::persist;

pub fn run(ctx: &mut Ctx, again: bool) -> Result<(), GateError> {
    validate_root(&ctx.root)?;
    step_d(ctx)?;
    if !ctx.backing_up {
        return Err(GateError::new(60, "backing down"));
    }
    accept_stashed(ctx);
    dispatch_waiting(ctx)?;
    let _ = again;
    publish_ctx(ctx)?;
    persist(ctx, Mode::Sweep { again })?;
    Ok(())
}
