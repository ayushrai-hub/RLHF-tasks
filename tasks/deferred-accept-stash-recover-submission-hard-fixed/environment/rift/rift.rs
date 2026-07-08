use crate::model::Ctx;

pub fn on_raise(ctx: &mut Ctx) {
    let _ = ctx.seal_epoch;
}

pub fn effective_barrier(ctx: &Ctx) -> u32 {
    ctx.seal_epoch
}

pub fn effective_floor(ctx: &Ctx) -> u32 {
    if ctx.seal_epoch > 0 {
        ctx.stash_epoch.max(ctx.seal_epoch)
    } else {
        ctx.stash_epoch
    }
}
