use crate::check::layout_ok;
use crate::cold_stage;
use crate::emit_stage;
use crate::errors::Err;
use crate::latch::pass_c;
use crate::model::Ctx;
use crate::report_stage;
use crate::walk;

pub fn run(ctx: &mut Ctx) -> Result<(), Err> {
    layout_ok(&ctx.root.base)?;
    crate::driver::hydrate_snap(ctx)?;
    walk::ingest(ctx)?;
    cold_stage::run(ctx)?;
    pass_c(ctx, &[]);
    emit_stage::persist(ctx)?;
    report_stage::emit(ctx)
}
