use crate::checks::validate_root;
use crate::errors::GateError;
use crate::io::{ensure_state, read_seed_rows};
use crate::model::{Ctx, Mode, Row};
use crate::render::publish_ctx;
use crate::stow::persist;
use crate::walk::copy_sample;

pub fn run(ctx: &mut Ctx, sample: &str) -> Result<(), GateError> {
    copy_sample(sample, &ctx.root)?;
    validate_root(&ctx.root)?;
    ensure_state(&ctx.root)?;
    ctx.gate_open = true;
    ctx.backing_up = false;
    ctx.wave = 1;
    ctx.slot = 0;
    ctx.stash_epoch = 0;
    ctx.seal_epoch = 0;
    ctx.barrier_gen = 0;
    ctx.witnesses.clear();
    ctx.carries.clear();
    ctx.rows.clear();
    ctx.events.clear();
    for (tag, lane, weight) in read_seed_rows(&ctx.root)? {
        let (state, stash_gen) = if lane == "pre" {
            ("stashed".to_string(), ctx.wave)
        } else {
            ("wait".to_string(), 0)
        };
        ctx.rows.push(Row {
            tag,
            lane,
            weight,
            state,
            wave: ctx.wave,
            stash_gen,
            seed_origin: true,
        });
    }
    publish_ctx(ctx)?;
    persist(
        ctx,
        Mode::Open {
            sample: sample.to_string(),
        },
    )?;
    Ok(())
}
