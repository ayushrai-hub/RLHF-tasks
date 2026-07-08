use crate::checks::validate_root;
use crate::errors::GateError;
use crate::model::{Ctx, Mode, Snap};
use crate::prime::step_d;
use crate::rebuild::reload_after_cycle;
use crate::render::publish_ctx;
use crate::seal::write_witness_blob;
use crate::span::load_rows;
use crate::stow::persist;

pub fn run(ctx: &mut Ctx, partial: bool) -> Result<(), GateError> {
    validate_root(&ctx.root)?;
    step_d(ctx)?;
    if partial {
        persist(ctx, Mode::Cycle { partial })?;
    }
    let snap = Snap {
        rows: load_rows(&ctx.root)?,
        wave: ctx.wave,
        gate_open: ctx.gate_open,
        backing_up: ctx.backing_up,
        stash_epoch: ctx.stash_epoch,
        seal_epoch: ctx.seal_epoch,
        barrier_gen: ctx.barrier_gen,
        witnesses: ctx.witnesses.clone(),
        carries: ctx.carries.clone(),
        events: ctx.events.clone(),
    };
    reload_after_cycle(ctx, partial, snap)?;
    publish_ctx(ctx)?;
    if partial {
        write_witness_blob(&ctx.root, ctx.seal_epoch, &ctx.witnesses)?;
        return Ok(());
    }
    persist(ctx, Mode::Cycle { partial })?;
    write_witness_blob(&ctx.root, ctx.seal_epoch, &ctx.witnesses)?;
    Ok(())
}
