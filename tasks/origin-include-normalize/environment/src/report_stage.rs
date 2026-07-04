use crate::errors::Err;
use crate::lens::mark_f;
use crate::model::Ctx;
use crate::render::write_products;

pub fn emit(ctx: &Ctx) -> Result<(), Err> {
    let view = mark_f(ctx);
    write_products(&ctx.root.state_dir(), &view.catalog, &view.equiv, &view.lines)
}
