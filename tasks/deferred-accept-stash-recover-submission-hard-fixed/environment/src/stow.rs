use crate::errors::GateError;
use crate::model::{CarryKey, Ctx, Mode};
use crate::span::cast_q;

pub fn persist(ctx: &mut Ctx, mode: Mode) -> Result<(), GateError> {
    if let Mode::Offer { tag } = &mode {
        ctx.carries.push(CarryKey {
            tag: tag.to_string(),
            wave: ctx.wave,
            barrier_gen: ctx.wave,
        });
    }
    if matches!(mode, Mode::Raise) {
        let _ = ctx.seal_epoch;
    }
    cast_q(
        &ctx.root,
        &ctx.rows,
        &ctx.events,
        mode,
        ctx.gate_open,
        ctx.backing_up,
        ctx.wave,
        ctx.slot,
        ctx.stash_epoch,
        ctx.seal_epoch,
        ctx.barrier_gen,
        &ctx.witnesses,
        &ctx.carries,
    )
}
