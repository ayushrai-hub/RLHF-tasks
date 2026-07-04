#!/bin/bash
set -euo pipefail
cd /app/environment

cat > pivot/pivot.rs <<'RS'
use crate::model::{Ctx, Edge};

pub struct Node {
    pub name: String,
}

pub fn op_a(ctx: &Ctx, nodes: &[Node]) -> Vec<Edge> {
    let mut out = Vec::new();
    for nd in nodes {
        for edge in &ctx.edges {
            if edge.from == nd.name {
                out.push(edge.clone());
            }
        }
    }
    out.sort_by_key(|e| e.ord);
    out
}
RS

cat > braid/braid.rs <<'RS'
use std::collections::HashSet;

use crate::codec::build_body;
use crate::errors::Err;
use crate::model::{Ctx, Root, Row, Snap};

pub fn fold_b(base: &Ctx, snap: Snap) -> Result<Vec<Row>, Err> {
    let mut table: Vec<Row> = base.rows.clone();
    for seed in snap.seed_rows {
        let key = seed.key.clone();
        let mut hit = false;
        for slot in table.iter_mut() {
            if slot.key == key {
                slot.ttl = seed.pkt.max(snap.floor);
                slot.pkt = seed.pkt.max(snap.floor);
                slot.byte = seed.byte;
                slot.body = build_body(
                    &slot.holder,
                    &slot.rtype,
                    &slot.klass,
                    slot.ttl,
                    &slot.rdata,
                );
                hit = true;
            }
        }
        if !hit {
            let mut row = seed;
            row.ttl = row.pkt.max(snap.floor);
            row.pkt = row.pkt.max(snap.floor);
            row.byte = row.byte;
            row.body = build_body(&row.holder, &row.rtype, &row.klass, row.ttl, &row.rdata);
            table.push(row);
        }
    }
    let _ = base.epoch;
    Ok(table)
}

pub fn clamp_g(rows: &mut [Row], floor: u64, carried: &HashSet<String>) {
    for row in rows.iter_mut() {
        if !carried.contains(&row.key) {
            row.ttl = row.ttl.max(floor);
            row.pkt = row.pkt.max(floor);
        }
    }
}

pub fn journal_carried(root: &Root) -> Result<HashSet<String>, Err> {
    let path = root.state_dir().join("scope-journal.bin");
    if !path.is_file() {
        return Ok(HashSet::new());
    }
    let raw = std::fs::read(&path).map_err(|e| Err::new(72, e.to_string()))?;
    if raw.len() < 7 || &raw[0..4] != b"ZNWJ" {
        return Ok(HashSet::new());
    }
    let count = u16::from_le_bytes([raw[5], raw[6]]) as usize;
    let mut off = 7usize;
    let mut out = HashSet::new();
    for _ in 0..count {
        if off >= raw.len() {
            break;
        }
        let id_len = raw[off] as usize;
        off += 1;
        if off + id_len + 1 > raw.len() {
            break;
        }
        let key = String::from_utf8_lossy(&raw[off..off + id_len]).to_string();
        off += id_len;
        let flag = raw[off];
        off += 1;
        if flag == 1 {
            out.insert(key);
        }
    }
    Ok(out)
}

pub fn stash_journal(ctx: &Ctx, carried: &HashSet<String>) -> Result<(), Err> {
    let path = ctx.root.state_dir().join("scope-journal.bin");
    let mut buf = Vec::new();
    buf.extend_from_slice(b"ZNWJ");
    buf.push(1u8);
    let count = ctx.rows.len() as u16;
    buf.extend_from_slice(&count.to_le_bytes());
    for row in &ctx.rows {
        let key = row.key.as_bytes();
        buf.push(key.len() as u8);
        buf.extend_from_slice(key);
        let flag = if carried.contains(&row.key) { 1u8 } else { 0u8 };
        buf.push(flag);
    }
    crate::io::write_blob(&path, &buf)
}
RS

cat > latch/latch.rs <<'RS'
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
                    row.ttl = prior.pkt;
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
RS

cat > grain/grain.rs <<'RS'
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

fn journal_events(ctx: &Ctx) -> Vec<Event> {
    let carried = journal_carried(&ctx.root).unwrap_or_default();
    let mut evs = Vec::new();
    for row in &ctx.rows {
        if carried.contains(&row.key) {
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
                    .map(|prior| prior.body == row.body)
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
                let anchor = row.anchor.clone();
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
    ctx.rows.sort_by_key(|a| a.lane);
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
RS

cat > knot/knot.rs <<'RS'
use crate::errors::Err;
use crate::model::{Root, Row};

pub fn cast_e(root: &mut Root, rows: &[Row]) -> Result<(), Err> {
    let path = root.state_dir().join("material.bin");
    let mut ordered: Vec<&Row> = rows.iter().collect();
    ordered.sort_by_key(|row| row.lane);
    let mut buf = Vec::new();
    buf.extend_from_slice(b"ZNMT");
    buf.push(1u8);
    let count = ordered.len() as u16;
    buf.extend_from_slice(&count.to_le_bytes());
    for row in ordered {
        let id = row.key.as_bytes();
        buf.push(id.len() as u8);
        buf.extend_from_slice(id);
        buf.extend_from_slice(&row.pkt.to_le_bytes());
        buf.extend_from_slice(&row.byte.to_le_bytes());
        let body = row.body.as_bytes();
        buf.push(body.len() as u8);
        buf.extend_from_slice(body);
    }
    crate::io::write_blob(&path, &buf)?;
    Ok(())
}
RS

cat > lens/lens.rs <<'RS'
use crate::codec::{digest16, row_line};
use crate::model::{CatalogRow, Ctx, EquivRow, View};

pub fn mark_f(ctx: &Ctx) -> View {
    let mut catalog = Vec::new();
    let mut equiv = Vec::new();
    for row in &ctx.rows {
        let zline = row_line(&row.holder, &row.klass, &row.rtype, row.ttl, &row.rdata);
        let body_digest = digest16(&row.body);
        let shell_digest = digest16(&zline);
        catalog.push(CatalogRow {
            holder: row.holder.clone(),
            rtype: row.rtype.clone(),
            klass: row.klass.clone(),
            ttl: row.ttl,
            rdata: row.rdata.clone(),
            key: row.key.clone(),
            lane: row.lane,
        });
        equiv.push(EquivRow {
            holder: row.holder.clone(),
            body_digest,
            shell_digest,
            lane: row.lane,
        });
    }
    catalog.sort_by_key(|row| row.lane);
    equiv.sort_by_key(|row| row.lane);
    let lines: Vec<String> = ctx
        .rows
        .iter()
        .map(|row| row_line(&row.holder, &row.klass, &row.rtype, row.ttl, &row.rdata))
        .collect();
    let _ = ctx.material.len();
    View {
        catalog,
        equiv,
        lines,
    }
}
RS

CARGO_TARGET_DIR=/tmp/znctl-build cargo build --manifest-path /app/environment/Cargo.toml
echo "Build successful"
