use crate::carry::read_carry_tab;
use crate::errors::GateError;
use crate::model::Ctx;
use crate::seal::read_witness_blob;
use crate::span::{load_meta, load_rows, load_witnesses, parse_events, read_ckpt_text};

pub fn step_d(ctx: &mut Ctx) -> Result<(), GateError> {
    if ctx.root.durable_path().exists() {
        ctx.rows = load_rows(&ctx.root)?;
    }
    if ctx.root.ckpt_path().exists() {
        let text = read_ckpt_text(&ctx.root)?;
        let meta = load_meta(&text)?;
        ctx.wave = meta.wave;
        ctx.slot = if meta.gate_open { 0 } else { meta.slot };
        ctx.gate_open = meta.gate_open;
        ctx.backing_up = meta.backing_up;
        ctx.stash_epoch = meta.stash_epoch;
        ctx.seal_epoch = 0;
        ctx.barrier_gen = 0;
        ctx.witnesses = load_witnesses(&text);
        ctx.events = parse_events(&text);
    }
    let (seal_epoch, witnesses) = read_witness_blob(&ctx.root)?;
    if seal_epoch > 0 {
        ctx.seal_epoch = seal_epoch;
    }
    if !witnesses.is_empty() {
        ctx.witnesses = witnesses;
    }
    let _ = read_carry_tab(&ctx.root)?;
    Ok(())
}
