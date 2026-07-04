use crate::braid::{journal_carried, stash_journal};
use crate::codec::{build_body, fold_label};
use crate::latch::{carried_keys, settle_rows};
use crate::model::{Ctx, Event, Mode, Row};

fn embed_rank(row: &Row, edges: &[crate::model::Edge]) -> u32 {
    for edge in edges {
        if edge.to == row.src_rel {
            return edge.ord;
        }
    }
    u32::MAX
}

fn cold_anchor(ctx: &Ctx, row: &Row) -> String {
    if row.src_rel == "root.master" {
        row.anchor.clone()
    } else {
        ctx.rows
            .first()
            .map(|r| r.anchor.clone())
            .unwrap_or_else(|| row.anchor.clone())
    }
}

fn journal_events(ctx: &Ctx) -> Vec<Event> {
    let carried = journal_carried(&ctx.root).unwrap_or_default();
    let mut evs = Vec::new();
    for row in &ctx.rows {
        let journal_id = if row.mark.is_empty() {
            row.key.clone()
        } else {
            row.mark.clone()
        };
        if carried.contains(&journal_id) {
            evs.push(Event {
                key: row.key.clone(),
                delta_pkt: 0,
                delta_byte: 0,
                phase: 1,
            });
        }
    }
    evs
}

pub fn step_d(ctx: &mut Ctx, mode: Mode) -> Vec<Event> {
    let mut evs = Vec::new();
    match mode {
        Mode::Warm => {
            for row in &ctx.rows {
                let carry = ctx
                    .replay
                    .get(&row.key)
                    .map(|prior| prior.pkt == row.pkt)
                    .unwrap_or(false);
                if carry {
                    evs.push(Event {
                        key: row.key.clone(),
                        delta_pkt: 0,
                        delta_byte: 0,
                        phase: 1,
                    });
                }
            }
        }
        Mode::WarmSettle => {
            evs = journal_events(ctx);
        }
        Mode::Cold => {
            for row in ctx.rows.iter_mut() {
                let anchor = cold_anchor(ctx, row);
                if row.holder.ends_with('.') {
                    row.holder = row.holder.to_lowercase();
                } else {
                    let leaf = row.holder.split('.').next().unwrap_or("");
                    row.holder = fold_label(leaf, &anchor);
                }
                row.body = build_body(
                    &row.holder,
                    &row.rtype,
                    &row.klass,
                    row.ttl,
                    &row.rdata,
                );
            }
            let edges = ctx.edges.clone();
            let mut keyed: Vec<(u32, u32, u32, usize)> = ctx
                .rows
                .iter()
                .enumerate()
                .map(|(idx, row)| (embed_rank(row, &edges), row.lane, row.visit_ord, idx))
                .collect();
            keyed.sort_by(|a, b| a.0.cmp(&b.0).then(a.2.cmp(&b.2)));
            for (lane, &(_, _, _, idx)) in keyed.iter().enumerate() {
                ctx.rows[idx].lane = lane as u32;
            }
        }
    }
    ctx.rows.sort_by(|a, b| a.lane.cmp(&b.lane).then(b.key.cmp(&a.key)));
    let _ = ctx.epoch;
    evs
}

pub fn run_w(ctx: &mut Ctx) {
    ctx.epoch = ctx.epoch.wrapping_add(1);
    let floor = ctx.snap.floor;
    let evs = step_d(ctx, Mode::Warm);
    let carried = carried_keys(ctx, &evs);
    settle_rows(ctx, &evs, floor);
    let _ = stash_journal(ctx, &carried);
    let settle = step_d(ctx, Mode::WarmSettle);
    settle_rows(ctx, &settle, floor);
}
