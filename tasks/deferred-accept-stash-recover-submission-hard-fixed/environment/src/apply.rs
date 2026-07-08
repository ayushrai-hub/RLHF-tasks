use crate::coil::pass_o;
use crate::errors::GateError;
use crate::loom::op_m;
use crate::model::{Ctx, Event};
use crate::seal::accept_eligible;

pub fn accept_stashed(ctx: &mut Ctx) -> usize {
    if !ctx.backing_up {
        return 0;
    }
    let mut promote = Vec::new();
    for (idx, row) in ctx.rows.iter().enumerate() {
        if accept_eligible(ctx, row) {
            promote.push(idx);
        }
    }
    let mut count = 0usize;
    for idx in promote {
        ctx.rows[idx].state = "wait".to_string();
        count += 1;
    }
    count
}

pub fn dispatch_waiting(ctx: &mut Ctx) -> Result<(), GateError> {
    let picked = op_m(ctx, &ctx.rows)?;
    let mut evs: Vec<Event> = Vec::new();
    for row in picked {
        ctx.slot = ctx.slot.saturating_add(1);
        evs.push(Event {
            tag: row.tag.clone(),
            wave: row.wave,
            phase: "fire".to_string(),
            slot: ctx.slot,
        });
    }
    let _ = pass_o(ctx, &evs);
    Ok(())
}
