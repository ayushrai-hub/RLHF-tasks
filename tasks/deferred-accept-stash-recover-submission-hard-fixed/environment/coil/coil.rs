use crate::fuse::seen_fire;
use crate::model::{Ctx, Event};

pub fn pass_o(ctx: &mut Ctx, evs: &[Event]) -> usize {
    let mut count = 0usize;
    for ev in evs {
        if seen_fire(&ctx.events, &ev.tag, ev.wave) {
            continue;
        }
        if let Some(row) = ctx.rows.iter_mut().find(|r| r.tag == ev.tag) {
            if row.state == "wait" || row.state == "stashed" {
                row.state = "sent".to_string();
                count += 1;
            }
            ctx.events.push(ev.clone());
        }
    }
    count
}
