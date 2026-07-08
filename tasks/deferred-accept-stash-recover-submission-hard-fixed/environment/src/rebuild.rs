use crate::errors::GateError;
use crate::fuse::merge_journal;
use crate::model::{Ctx, Mode, Snap};
use crate::ring::fold_n;
use crate::seal::{merge_witness, witness_partial};
use crate::vault::step_p;

pub fn reload_after_cycle(ctx: &mut Ctx, partial: bool, snap: Snap) -> Result<(), GateError> {
    let prior_events = ctx.events.clone();
    ctx.rows.clear();
    ctx.events.clear();
    ctx.gate_open = true;
    ctx.stash_epoch = snap.stash_epoch;
    ctx.seal_epoch = snap.seal_epoch;
    ctx.barrier_gen = snap.barrier_gen;
    ctx.witnesses = merge_witness(&ctx.witnesses, &snap.witnesses);
    ctx.carries = snap.carries.clone();
    ctx.rows = fold_n(ctx, snap.clone())?;
    let startup = step_p(ctx, Mode::Cycle { partial });
    for ev in startup {
        ctx.slot = ev.slot;
        ctx.events.push(ev);
    }
    if partial {
        witness_partial(ctx);
    }
    ctx.events = merge_journal(&prior_events, &ctx.events);
    Ok(())
}
