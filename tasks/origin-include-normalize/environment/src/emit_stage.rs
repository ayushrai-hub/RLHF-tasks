use crate::errors::Err;
use crate::knot::cast_e;
use crate::model::Ctx;

pub fn persist(ctx: &mut Ctx) -> Result<(), Err> {
    cast_e(&mut ctx.root, &ctx.rows)
}
