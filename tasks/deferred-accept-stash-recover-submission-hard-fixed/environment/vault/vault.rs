use crate::model::{Ctx, Event, Mode};
use crate::seal::on_cycle_startup;

pub fn step_p(ctx: &mut Ctx, mode: Mode) -> Vec<Event> {
    on_cycle_startup(ctx, mode);
    Vec::new()
}
