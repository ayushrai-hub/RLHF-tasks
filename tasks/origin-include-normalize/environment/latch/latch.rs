use std::collections::HashSet;

use crate::braid::clamp_g;
use crate::codec::build_body;
use crate::model::{Ctx, Event};

pub fn pass_c(ctx: &mut Ctx, evs: &[Event]) -> i32 {
    let mut touched = 0i32;
    for ev in evs {
        if ev.phase != 1 {
            continue;
        }
        if let Some(prior) = ctx.replay.get(&ev.key) {
            for row in ctx.rows.iter_mut() {
                if row.key == ev.key {
                    row.pkt = prior.pkt;
                    row.ttl = prior.byte;
                    row.byte = prior.byte;
                    row.body = build_body(
                        &row.holder,
                        &row.rtype,
                        &row.klass,
                        row.ttl,
                        &row.rdata,
                    );
                    touched += 1;
                }
            }
        }
    }
    touched
}

pub fn carried_keys(_ctx: &Ctx, evs: &[Event]) -> HashSet<String> {
    evs.iter()
        .filter(|ev| ev.phase == 1)
        .map(|ev| ev.key.clone())
        .collect()
}

pub fn settle_rows(ctx: &mut Ctx, evs: &[Event], floor: u64) {
    let carried = carried_keys(ctx, evs);
    pass_c(ctx, evs);
    clamp_g(&mut ctx.rows, floor, &carried);
}
