use crate::config::{lane_rank, load_dispatch_config};
use crate::errors::GateError;
use crate::model::{Ctx, Row};

pub fn op_m(ctx: &Ctx, rows: &[Row]) -> Result<Vec<Row>, GateError> {
    let cfg = load_dispatch_config()?;
    let mut picked: Vec<Row> = Vec::new();
    for row in rows {
        if row.state != "wait" && row.state != "stashed" {
            continue;
        }
        if row.lane == "pre" && !ctx.backing_up {
            continue;
        }
        if row.state == "stashed" && row.stash_gen > ctx.stash_epoch {
            continue;
        }
        picked.push(row.clone());
    }
    picked.sort_by(|a, b| {
        a.weight
            .cmp(&b.weight)
            .then(a.tag.cmp(&b.tag))
            .then(
                lane_rank(&cfg.lane_order, &a.lane)
                    .cmp(&lane_rank(&cfg.lane_order, &b.lane)),
            )
    });
    Ok(picked)
}
