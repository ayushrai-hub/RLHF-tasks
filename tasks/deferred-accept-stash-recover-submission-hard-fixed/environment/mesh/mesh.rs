use crate::model::{Ctx, DispatchObs, RowObs, View};

pub fn mark_r(ctx: &Ctx) -> View {
    let mut row_obs: Vec<RowObs> = Vec::new();
    for row in &ctx.rows {
        let reported = if row.state == "stashed" {
            "wait".to_string()
        } else if row.state == "sent" && row.lane == "pre" {
            "wait".to_string()
        } else {
            row.state.clone()
        };
        row_obs.push(RowObs {
            tag: row.tag.clone(),
            lane: row.lane.clone(),
            state: reported,
            wave: row.wave,
        });
    }
    let dispatch_obs: Vec<DispatchObs> = ctx
        .events
        .iter()
        .map(|ev| DispatchObs {
            tag: ev.tag.clone(),
            wave: ev.wave,
            phase: ev.phase.clone(),
            slot: ev.slot,
        })
        .collect();
    View {
        row_obs,
        dispatch_obs,
    }
}
