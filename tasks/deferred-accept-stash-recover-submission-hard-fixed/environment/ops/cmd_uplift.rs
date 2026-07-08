use crate::checks::validate_root;
use crate::errors::GateError;
use crate::model::{Ctx, Mode};
use crate::prime::step_d;
use crate::stow::persist;

pub fn run(ctx: &mut Ctx) -> Result<(), GateError> {
    validate_root(&ctx.root)?;
    step_d(ctx)?;
    if !ctx.gate_open {
        return Err(GateError::new(50, "gate closed"));
    }
    ctx.backing_up = true;
    ctx.stash_epoch = ctx.wave;
    persist(ctx, Mode::Raise)?;
    Ok(())
}
