use crate::checks::{validate_root, validate_tag};
use crate::errors::GateError;
use crate::model::{Ctx, Mode, Row};
use crate::prime::step_d;
use crate::stow::persist;

pub fn run(ctx: &mut Ctx, tag: &str) -> Result<(), GateError> {
    validate_root(&ctx.root)?;
    step_d(ctx)?;
    validate_tag(tag)?;
    if !ctx.gate_open {
        return Err(GateError::new(40, "gate closed"));
    }
    if ctx.backing_up {
        return Err(GateError::new(41, "backing already up"));
    }
    ctx.wave = ctx.wave.saturating_add(1);
    let wave = ctx.wave;
    ctx.rows.push(Row {
        tag: tag.to_string(),
        lane: "pre".to_string(),
        weight: wave,
        state: "stashed".to_string(),
        wave,
        stash_gen: wave,
        seed_origin: false,
    });
    persist(
        ctx,
        Mode::Offer {
            tag: tag.to_string(),
        },
    )?;
    Ok(())
}
