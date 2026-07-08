#!/bin/bash
set -euo pipefail
cd /app/environment
python3 - <<'PYFIX'
from pathlib import Path

Path('src/model.rs').write_text(r'''
use std::path::PathBuf;

#[derive(Clone, Debug)]
pub struct Root {
    pub base: PathBuf,
}

impl Root {
    pub fn new(base: PathBuf) -> Self {
        Self { base }
    }
    pub fn state_dir(&self) -> PathBuf {
        self.base.join(".state")
    }
    pub fn seed_file(&self) -> PathBuf {
        self.base.join("seed.txt")
    }
    pub fn durable_path(&self) -> PathBuf {
        self.state_dir().join("durable.json")
    }
    pub fn ckpt_path(&self) -> PathBuf {
        self.state_dir().join("ckpt.json")
    }
    pub fn row_obs_path(&self) -> PathBuf {
        self.state_dir().join("row-obs.jsonl")
    }
    pub fn dispatch_obs_path(&self) -> PathBuf {
        self.state_dir().join("dispatch-obs.jsonl")
    }
    pub fn witness_path(&self) -> PathBuf {
        self.state_dir().join("defer-witness.bin")
    }
    pub fn carry_path(&self) -> PathBuf {
        self.state_dir().join("defer-carry.tab")
    }
    pub fn anchor_path(&self) -> PathBuf {
        self.state_dir().join("recovery-anchor.tab")
    }
}

#[derive(Clone, Debug, Eq, PartialEq, Hash)]
pub struct WitnessKey {
    pub tag: String,
    pub wave: u32,
}

#[derive(Clone, Debug, Eq, PartialEq, Hash)]
pub struct CarryKey {
    pub tag: String,
    pub wave: u32,
    pub barrier_gen: u32,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Row {
    pub tag: String,
    pub lane: String,
    pub weight: u32,
    pub state: String,
    pub wave: u32,
    pub stash_gen: u32,
    pub seed_origin: bool,
}

#[derive(Clone, Debug)]
pub struct Snap {
    pub rows: Vec<Row>,
    pub wave: u32,
    pub gate_open: bool,
    pub backing_up: bool,
    pub stash_epoch: u32,
    pub seal_epoch: u32,
    pub barrier_gen: u32,
    pub witnesses: Vec<WitnessKey>,
    pub carries: Vec<CarryKey>,
    pub events: Vec<Event>,
}

#[derive(Clone, Debug)]
pub struct Event {
    pub tag: String,
    pub wave: u32,
    pub phase: String,
    pub slot: u32,
}

#[derive(Clone, Debug)]
pub struct RowObs {
    pub tag: String,
    pub lane: String,
    pub state: String,
    pub wave: u32,
}

#[derive(Clone, Debug)]
pub struct DispatchObs {
    pub tag: String,
    pub wave: u32,
    pub phase: String,
    pub slot: u32,
}

#[derive(Clone, Debug)]
pub struct View {
    pub row_obs: Vec<RowObs>,
    pub dispatch_obs: Vec<DispatchObs>,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub enum Mode {
    Open { sample: String },
    Offer { tag: String },
    Cycle { partial: bool },
    Raise,
    Sweep { again: bool },
}

#[derive(Clone, Debug)]
pub struct Ctx {
    pub root: Root,
    pub rows: Vec<Row>,
    pub wave: u32,
    pub slot: u32,
    pub gate_open: bool,
    pub backing_up: bool,
    pub stash_epoch: u32,
    pub seal_epoch: u32,
    pub barrier_gen: u32,
    pub witnesses: Vec<WitnessKey>,
    pub carries: Vec<CarryKey>,
    pub events: Vec<Event>,
}

impl RowObs {
    pub fn to_json(&self) -> String {
        format!(
            "{{\"tag\":\"{}\",\"lane\":\"{}\",\"state\":\"{}\",\"wave\":{}}}",
            esc(&self.tag),
            esc(&self.lane),
            esc(&self.state),
            self.wave
        )
    }
}

impl DispatchObs {
    pub fn to_json(&self) -> String {
        format!(
            "{{\"tag\":\"{}\",\"wave\":{},\"phase\":\"{}\",\"slot\":{}}}",
            esc(&self.tag),
            self.wave,
            esc(&self.phase),
            self.slot
        )
    }
}

fn esc(s: &str) -> String {
    s.replace('\\', "\\\\").replace('"', "\\\"")
}

impl Ctx {
    pub fn new(root: Root) -> Self {
        Self {
            root,
            rows: Vec::new(),
            wave: 0,
            slot: 0,
            gate_open: false,
            backing_up: false,
            stash_epoch: 0,
            seal_epoch: 0,
            barrier_gen: 0,
            witnesses: Vec::new(),
            carries: Vec::new(),
            events: Vec::new(),
        }
    }
}
''')

Path('carry/carry.rs').write_text(r'''
use std::collections::HashSet;
use std::fs;

use crate::errors::GateError;
use crate::model::{CarryKey, Ctx, Root};

pub fn stamp_offer(ctx: &mut Ctx, tag: &str, wave: u32) {
    ctx.carries.push(CarryKey {
        tag: tag.to_string(),
        wave,
        barrier_gen: ctx.seal_epoch,
    });
}

pub fn has_carry(ctx: &Ctx, tag: &str, wave: u32) -> bool {
    let barrier = ctx.barrier_gen.max(ctx.seal_epoch);
    ctx.carries.iter().any(|c| {
        c.tag == tag && c.wave == wave && c.barrier_gen <= barrier
    })
}

pub fn merge_carries(base: &[CarryKey], snap: &[CarryKey]) -> Vec<CarryKey> {
    let mut out = base.to_vec();
    let mut seen: HashSet<(String, u32, u32)> = out
        .iter()
        .map(|c| (c.tag.clone(), c.wave, c.barrier_gen))
        .collect();
    for c in snap {
        let key = (c.tag.clone(), c.wave, c.barrier_gen);
        if seen.insert(key) {
            out.push(c.clone());
        }
    }
    out
}

pub fn write_carry_tab(root: &Root, carries: &[CarryKey]) -> Result<(), GateError> {
    if let Some(parent) = root.carry_path().parent() {
        fs::create_dir_all(parent).map_err(|e| GateError::new(93, e.to_string()))?;
    }
    let body = carries
        .iter()
        .map(|c| format!("{}|{}|{}", c.tag, c.wave, c.barrier_gen))
        .collect::<Vec<_>>()
        .join("\n");
    let suffix = if body.is_empty() { String::new() } else { format!("{body}\n") };
    fs::write(root.carry_path(), suffix).map_err(|e| GateError::new(94, e.to_string()))
}

pub fn read_carry_tab(root: &Root) -> Result<Vec<CarryKey>, GateError> {
    let path = root.carry_path();
    if !path.exists() {
        return Ok(Vec::new());
    }
    let text = fs::read_to_string(path).map_err(|e| GateError::new(95, e.to_string()))?;
    let mut out = Vec::new();
    for line in text.lines() {
        let line = line.trim();
        if line.is_empty() {
            continue;
        }
        let parts: Vec<&str> = line.split('|').collect();
        if parts.len() != 3 {
            continue;
        }
        out.push(CarryKey {
            tag: parts[0].to_string(),
            wave: parts[1].parse().unwrap_or(0),
            barrier_gen: parts[2].parse().unwrap_or(0),
        });
    }
    Ok(out)
}
''')

Path('rift/rift.rs').write_text(r'''
use crate::model::Ctx;

pub fn on_raise(ctx: &mut Ctx) {
    ctx.barrier_gen = if ctx.seal_epoch > 0 {
        ctx.seal_epoch
    } else {
        ctx.stash_epoch
    };
}

pub fn effective_barrier(ctx: &Ctx) -> u32 {
    if ctx.seal_epoch > 0 {
        ctx.barrier_gen.min(ctx.seal_epoch)
    } else {
        ctx.barrier_gen
    }
}

pub fn effective_floor(ctx: &Ctx) -> u32 {
    ctx.stash_epoch
}
''')

Path('seal/seal.rs').write_text(r'''
use std::collections::HashSet;

use crate::carry::has_carry;
use crate::errors::GateError;
use crate::model::{Ctx, Root, Row, WitnessKey};
use crate::rift::effective_floor;

pub fn witness_partial(ctx: &mut Ctx) {
    let seal_at = ctx.seal_epoch;
    let mut seen: HashSet<(String, u32)> = ctx
        .witnesses
        .iter()
        .map(|w| (w.tag.clone(), w.wave))
        .collect();
    for row in &ctx.rows {
        if row.state != "stashed" || row.seed_origin {
            continue;
        }
        let key = (row.tag.clone(), row.wave);
        if !seen.insert(key.clone()) {
            continue;
        }
        if !ctx.carries.iter().any(|c| {
            c.tag == row.tag && c.wave == row.wave && c.barrier_gen <= seal_at
        }) {
            continue;
        }
        ctx.witnesses.push(WitnessKey {
            tag: key.0,
            wave: key.1,
        });
    }
    ctx.seal_epoch = ctx.seal_epoch.saturating_add(1);
}

pub fn accept_eligible(ctx: &Ctx, row: &Row) -> bool {
    if row.state != "stashed" || !ctx.backing_up {
        return false;
    }
    let floor = effective_floor(ctx);
    if row.stash_gen > floor {
        return false;
    }
    if row.seed_origin {
        return true;
    }
    let witnessed = ctx
        .witnesses
        .iter()
        .any(|w| w.tag == row.tag && w.wave == row.wave);
    witnessed && has_carry(ctx, &row.tag, row.wave)
}

pub fn merge_witness(base: &[WitnessKey], snap: &[WitnessKey]) -> Vec<WitnessKey> {
    let mut out = base.to_vec();
    let mut seen: HashSet<(String, u32)> = out
        .iter()
        .map(|w| (w.tag.clone(), w.wave))
        .collect();
    for w in snap {
        let key = (w.tag.clone(), w.wave);
        if seen.insert(key) {
            out.push(w.clone());
        }
    }
    out
}

pub fn write_witness_blob(root: &Root, seal_epoch: u32, witnesses: &[WitnessKey]) -> Result<(), GateError> {
    let mut raw = Vec::new();
    raw.extend_from_slice(b"GWHN");
    raw.push(1);
    raw.extend_from_slice(&seal_epoch.to_le_bytes());
    let count = witnesses.len().min(u16::MAX as usize) as u16;
    raw.extend_from_slice(&count.to_le_bytes());
    for w in witnesses.iter().take(count as usize) {
        let tag = w.tag.as_bytes();
        let tag_len = tag.len().min(u8::MAX as usize) as u8;
        raw.push(tag_len);
        raw.extend_from_slice(&tag[..tag_len as usize]);
        raw.extend_from_slice(&w.wave.to_le_bytes());
    }
    if let Some(parent) = root.witness_path().parent() {
        std::fs::create_dir_all(parent).map_err(|e| GateError::new(90, e.to_string()))?;
    }
    std::fs::write(root.witness_path(), raw).map_err(|e| GateError::new(91, e.to_string()))
}

pub fn read_witness_blob(root: &Root) -> Result<(u32, Vec<WitnessKey>), GateError> {
    let path = root.witness_path();
    if !path.exists() {
        return Ok((0, Vec::new()));
    }
    let raw = std::fs::read(&path).map_err(|e| GateError::new(92, e.to_string()))?;
    if raw.len() < 11 || &raw[..4] != b"GWHN" {
        return Ok((0, Vec::new()));
    }
    let seal_epoch = u32::from_le_bytes(raw[5..9].try_into().unwrap());
    let count = u16::from_le_bytes(raw[9..11].try_into().unwrap()) as usize;
    let mut off = 11;
    let mut witnesses = Vec::new();
    for _ in 0..count {
        if off >= raw.len() {
            break;
        }
        let tag_len = raw[off] as usize;
        off += 1;
        if off + tag_len + 4 > raw.len() {
            break;
        }
        let tag = String::from_utf8_lossy(&raw[off..off + tag_len]).to_string();
        off += tag_len;
        let wave = u32::from_le_bytes(raw[off..off + 4].try_into().unwrap());
        off += 4;
        witnesses.push(WitnessKey { tag, wave });
    }
    Ok((seal_epoch, witnesses))
}
''')

Path('fuse/fuse.rs').write_text(r'''
use crate::model::{Event, Row};

pub fn row_key(row: &Row) -> String {
    format!("{}:{}", row.tag, row.wave)
}

pub fn event_key(ev: &Event) -> String {
    format!("{}:{}", ev.tag, ev.wave)
}

pub fn merge_rows(base: &[Row], replay: &[Row]) -> Vec<Row> {
    let mut merged: Vec<Row> = base.to_vec();
    for row in replay {
        let key = row_key(row);
        let mut found = false;
        for slot in merged.iter_mut() {
            if row_key(slot) == key {
                found = true;
                if slot.state != "sent" {
                    *slot = row.clone();
                } else if row.state == "sent" {
                    *slot = row.clone();
                }
            }
        }
        if !found {
            merged.push(row.clone());
        }
    }
    merged
}

pub fn merge_journal(prior: &[Event], replay: &[Event]) -> Vec<Event> {
    let mut out = prior.to_vec();
    for ev in replay {
        if out.iter().any(|e| event_key(e) == event_key(ev)) {
            continue;
        }
        out.push(ev.clone());
    }
    out.sort_by_key(|e| e.slot);
    out
}

pub fn seen_fire(events: &[Event], tag: &str, wave: u32) -> bool {
    events
        .iter()
        .any(|e| e.phase == "fire" && e.tag == tag && e.wave == wave)
}
''')

Path('prime/prime.rs').write_text(r'''
use crate::carry::read_carry_tab;
use crate::errors::GateError;
use crate::model::Ctx;
use crate::seal::read_witness_blob;
use crate::span::{load_meta, load_rows, load_witnesses, parse_events, read_anchor, read_ckpt_text};

pub fn step_d(ctx: &mut Ctx) -> Result<(), GateError> {
    if ctx.root.durable_path().exists() {
        ctx.rows = load_rows(&ctx.root)?;
    }
    if ctx.root.ckpt_path().exists() {
        let text = read_ckpt_text(&ctx.root)?;
        let meta = load_meta(&text)?;
        ctx.wave = meta.wave;
        ctx.slot = meta.slot;
        ctx.gate_open = meta.gate_open;
        ctx.backing_up = meta.backing_up;
        ctx.stash_epoch = meta.stash_epoch;
        ctx.seal_epoch = meta.seal_epoch;
        ctx.barrier_gen = meta.barrier_gen;
        ctx.witnesses = load_witnesses(&text);
        ctx.events = parse_events(&text);
    }
    let (file_seal, file_witnesses) = read_witness_blob(&ctx.root)?;
    if file_seal > 0 {
        ctx.seal_epoch = file_seal;
    }
    if !file_witnesses.is_empty() {
        ctx.witnesses = file_witnesses;
    }
    ctx.carries = read_carry_tab(&ctx.root)?;
    if let Some(anchor) = read_anchor(&ctx.root)? {
        ctx.wave = anchor.wave;
        ctx.slot = anchor.slot;
        ctx.gate_open = anchor.gate_open;
        ctx.backing_up = anchor.backing_up;
        ctx.stash_epoch = anchor.stash_epoch;
        ctx.seal_epoch = anchor.seal_epoch;
        ctx.barrier_gen = anchor.barrier_gen;
        ctx.rows = anchor.rows;
        ctx.events = anchor.events;
        ctx.witnesses = anchor.witnesses;
        ctx.carries = anchor.carries;
    }
    Ok(())
}
''')

Path('src/apply.rs').write_text(r'''
use crate::coil::pass_o;
use crate::errors::GateError;
use crate::loom::op_m;
use crate::model::{Ctx, Event};
use crate::seal::accept_eligible;

pub fn accept_stashed(ctx: &mut Ctx) -> usize {
    if !ctx.backing_up {
        return 0;
    }
    let mut promote = Vec::new();
    for (idx, row) in ctx.rows.iter().enumerate() {
        if accept_eligible(ctx, row) {
            promote.push(idx);
        }
    }
    let mut count = 0usize;
    for idx in promote {
        ctx.rows[idx].state = "wait".to_string();
        count += 1;
    }
    count
}

pub fn dispatch_waiting(ctx: &mut Ctx) -> Result<(), GateError> {
    let picked = op_m(ctx, &ctx.rows)?;
    let mut evs: Vec<Event> = Vec::new();
    for row in picked {
        ctx.slot = ctx.slot.saturating_add(1);
        evs.push(Event {
            tag: row.tag.clone(),
            wave: row.wave,
            phase: "fire".to_string(),
            slot: ctx.slot,
        });
    }
    let _ = pass_o(ctx, &evs);
    Ok(())
}
''')

Path('loom/loom.rs').write_text(r'''
use crate::config::{lane_rank, load_dispatch_config};
use crate::errors::GateError;
use crate::model::{Ctx, Row};

pub fn op_m(ctx: &Ctx, rows: &[Row]) -> Result<Vec<Row>, GateError> {
    let cfg = load_dispatch_config()?;
    let mut picked: Vec<Row> = Vec::new();
    for row in rows {
        if row.state != "wait" {
            continue;
        }
        if row.lane == "pre" && !ctx.backing_up {
            continue;
        }
        picked.push(row.clone());
    }
    picked.sort_by(|a, b| {
        lane_rank(&cfg.lane_order, &a.lane)
            .cmp(&lane_rank(&cfg.lane_order, &b.lane))
            .then(a.weight.cmp(&b.weight))
            .then(a.tag.cmp(&b.tag))
            .then(a.wave.cmp(&b.wave))
    });
    Ok(picked)
}
''')

Path('ring/ring.rs').write_text(r'''
use crate::errors::GateError;
use crate::fuse::merge_rows;
use crate::model::{Ctx, Row, Snap};

pub fn fold_n(base: &Ctx, snap: Snap) -> Result<Vec<Row>, GateError> {
    Ok(merge_rows(&base.rows, &snap.rows))
}
''')

Path('coil/coil.rs').write_text(r'''
use crate::fuse::seen_fire;
use crate::model::{Ctx, Event};

pub fn pass_o(ctx: &mut Ctx, evs: &[Event]) -> usize {
    let mut count = 0usize;
    for ev in evs {
        if seen_fire(&ctx.events, &ev.tag, ev.wave) {
            continue;
        }
        if let Some(row) = ctx
            .rows
            .iter_mut()
            .find(|r| r.tag == ev.tag && r.wave == ev.wave)
        {
            if row.state == "wait" {
                row.state = "sent".to_string();
                count += 1;
            }
            ctx.events.push(ev.clone());
        }
    }
    count
}
''')

Path('vault/vault.rs').write_text(r'''
use crate::model::{Ctx, Event, Mode};

pub fn step_p(ctx: &mut Ctx, mode: Mode) -> Vec<Event> {
    if matches!(mode, Mode::Cycle { .. }) {
        ctx.gate_open = true;
    }
    Vec::new()
}
''')

Path('span/span.rs').write_text(r'''
use crate::carry::write_carry_tab;
use crate::errors::GateError;
use crate::model::{CarryKey, Event, Mode, Root, Row, WitnessKey};
use crate::seal::write_witness_blob;

#[derive(Clone, Debug)]
pub struct Anchor {
    pub rows: Vec<Row>,
    pub events: Vec<Event>,
    pub wave: u32,
    pub slot: u32,
    pub gate_open: bool,
    pub backing_up: bool,
    pub stash_epoch: u32,
    pub seal_epoch: u32,
    pub barrier_gen: u32,
    pub witnesses: Vec<WitnessKey>,
    pub carries: Vec<CarryKey>,
}

pub fn cast_q(
    root: &Root,
    rows: &[Row],
    events: &[crate::model::Event],
    mode: Mode,
    gate_open: bool,
    backing_up: bool,
    wave: u32,
    slot: u32,
    stash_epoch: u32,
    seal_epoch: u32,
    barrier_gen: u32,
    witnesses: &[WitnessKey],
    carries: &[CarryKey],
) -> Result<(), GateError> {
    let durable = serde_rows(rows);
    crate::io::write_json(&root.durable_path(), &durable)?;
    write_carry_tab(root, carries)?;
    write_anchor(root, rows, events, gate_open, backing_up, wave, slot, stash_epoch, seal_epoch, barrier_gen, witnesses, carries)?;
    if let Mode::Cycle { partial: true } = mode {
        return Ok(());
    }
    let ev_body: Vec<String> = events
        .iter()
        .map(|ev| {
            format!(
                "{{\"tag\":\"{}\",\"wave\":{},\"phase\":\"{}\",\"slot\":{}}}",
                esc(&ev.tag),
                ev.wave,
                esc(&ev.phase),
                ev.slot
            )
        })
        .collect();
    let witness_body: Vec<String> = witnesses
        .iter()
        .map(|w| format!("{{\"tag\":\"{}\",\"wave\":{}}}", esc(&w.tag), w.wave))
        .collect();
    let ckpt = format!(
        "{{\"wave\":{wave},\"slot\":{slot},\"gate_open\":{gate_open},\"backing_up\":{backing_up},\"stash_epoch\":{stash_epoch},\"seal_epoch\":{seal_epoch},\"barrier_gen\":{barrier_gen},\"witnesses\":[{}],\"rows\":[{}],\"events\":[{}]}}",
        witness_body.join(","),
        rows.iter()
            .map(|r| format!("\"{}:{}\"", esc(&r.tag), r.wave))
            .collect::<Vec<_>>()
            .join(","),
        ev_body.join(",")
    );
    crate::io::write_json(&root.ckpt_path(), &ckpt)?;
    write_witness_blob(root, seal_epoch, witnesses)
}

fn write_anchor(
    root: &Root,
    rows: &[Row],
    events: &[Event],
    gate_open: bool,
    backing_up: bool,
    wave: u32,
    slot: u32,
    stash_epoch: u32,
    seal_epoch: u32,
    barrier_gen: u32,
    witnesses: &[WitnessKey],
    carries: &[CarryKey],
) -> Result<(), GateError> {
    let mut lines = Vec::new();
    lines.push(format!(
        "meta|{wave}|{slot}|{gate_open}|{backing_up}|{stash_epoch}|{seal_epoch}|{barrier_gen}"
    ));
    for row in rows {
        lines.push(format!(
            "row|{}|{}|{}|{}|{}|{}|{}",
            esc_pipe(&row.tag),
            esc_pipe(&row.lane),
            row.weight,
            esc_pipe(&row.state),
            row.wave,
            row.stash_gen,
            row.seed_origin
        ));
    }
    for ev in events {
        lines.push(format!(
            "event|{}|{}|{}|{}",
            esc_pipe(&ev.tag),
            ev.wave,
            esc_pipe(&ev.phase),
            ev.slot
        ));
    }
    for w in witnesses {
        lines.push(format!("witness|{}|{}", esc_pipe(&w.tag), w.wave));
    }
    for c in carries {
        lines.push(format!("carry|{}|{}|{}", esc_pipe(&c.tag), c.wave, c.barrier_gen));
    }
    crate::io::write_json(&root.anchor_path(), &(lines.join("\n") + "\n"))
}

pub fn read_anchor(root: &Root) -> Result<Option<Anchor>, GateError> {
    if !root.anchor_path().exists() {
        return Ok(None);
    }
    let text = crate::io::read_json(&root.anchor_path())?;
    let mut anchor = Anchor {
        rows: Vec::new(),
        events: Vec::new(),
        wave: 0,
        slot: 0,
        gate_open: false,
        backing_up: false,
        stash_epoch: 0,
        seal_epoch: 0,
        barrier_gen: 0,
        witnesses: Vec::new(),
        carries: Vec::new(),
    };
    let mut saw_meta = false;
    for line in text.lines() {
        let parts: Vec<&str> = line.split('|').collect();
        if parts.is_empty() {
            continue;
        }
        match parts[0] {
            "meta" if parts.len() == 8 => {
                anchor.wave = parts[1].parse().unwrap_or(0);
                anchor.slot = parts[2].parse().unwrap_or(0);
                anchor.gate_open = parts[3] == "true";
                anchor.backing_up = parts[4] == "true";
                anchor.stash_epoch = parts[5].parse().unwrap_or(0);
                anchor.seal_epoch = parts[6].parse().unwrap_or(0);
                anchor.barrier_gen = parts[7].parse().unwrap_or(0);
                saw_meta = true;
            }
            "row" if parts.len() == 8 => anchor.rows.push(Row {
                tag: parts[1].to_string(),
                lane: parts[2].to_string(),
                weight: parts[3].parse().unwrap_or(0),
                state: parts[4].to_string(),
                wave: parts[5].parse().unwrap_or(0),
                stash_gen: parts[6].parse().unwrap_or(0),
                seed_origin: parts[7] == "true",
            }),
            "event" if parts.len() == 5 => anchor.events.push(Event {
                tag: parts[1].to_string(),
                wave: parts[2].parse().unwrap_or(0),
                phase: parts[3].to_string(),
                slot: parts[4].parse().unwrap_or(0),
            }),
            "witness" if parts.len() == 3 => anchor.witnesses.push(WitnessKey {
                tag: parts[1].to_string(),
                wave: parts[2].parse().unwrap_or(0),
            }),
            "carry" if parts.len() == 4 => anchor.carries.push(CarryKey {
                tag: parts[1].to_string(),
                wave: parts[2].parse().unwrap_or(0),
                barrier_gen: parts[3].parse().unwrap_or(0),
            }),
            _ => {}
        }
    }
    if saw_meta {
        Ok(Some(anchor))
    } else {
        Ok(None)
    }
}

fn serde_rows(rows: &[Row]) -> String {
    let body: Vec<String> = rows
        .iter()
        .map(|r| {
            format!(
                "{{\"tag\":\"{}\",\"lane\":\"{}\",\"weight\":{},\"state\":\"{}\",\"wave\":{},\"stash_gen\":{},\"seed_origin\":{}}}",
                esc(&r.tag),
                esc(&r.lane),
                r.weight,
                esc(&r.state),
                r.wave,
                r.stash_gen,
                r.seed_origin
            )
        })
        .collect();
    format!("[{}]", body.join(","))
}

fn esc(s: &str) -> String {
    s.replace('\\', "\\\\").replace('"', "\\\"")
}

fn esc_pipe(s: &str) -> String {
    s.replace('|', "")
}

pub fn read_ckpt_text(root: &Root) -> Result<String, GateError> {
    crate::io::read_json(&root.ckpt_path())
}

pub struct Meta {
    pub wave: u32,
    pub slot: u32,
    pub gate_open: bool,
    pub backing_up: bool,
    pub stash_epoch: u32,
    pub seal_epoch: u32,
    pub barrier_gen: u32,
}

pub fn load_meta(text: &str) -> Result<Meta, GateError> {
    Ok(Meta {
        wave: read_key(text, "wave")?.parse().unwrap_or(1),
        slot: read_key(text, "slot")?.parse().unwrap_or(0),
        gate_open: read_key(text, "gate_open")? == "true",
        backing_up: read_key(text, "backing_up")? == "true",
        stash_epoch: read_key(text, "stash_epoch").unwrap_or_else(|_| "0".to_string()).parse().unwrap_or(0),
        seal_epoch: read_key(text, "seal_epoch").unwrap_or_else(|_| "0".to_string()).parse().unwrap_or(0),
        barrier_gen: read_key(text, "barrier_gen").unwrap_or_else(|_| "0".to_string()).parse().unwrap_or(0),
    })
}

pub fn load_witnesses(text: &str) -> Vec<WitnessKey> {
    let mut out = Vec::new();
    if let Some(start) = text.find("\"witnesses\":[") {
        let rest = &text[start + 13..];
        if let Some(end) = rest.find(']') {
            let body = &rest[..end];
            for chunk in body.split("},{") {
                let chunk = chunk.trim_matches(&['{', '}', ',', ' '][..]);
                if chunk.is_empty() {
                    continue;
                }
                if let (Ok(tag), Ok(wave)) = (read_key(chunk, "tag"), read_key(chunk, "wave")) {
                    out.push(WitnessKey {
                        tag,
                        wave: wave.parse().unwrap_or(0),
                    });
                }
            }
        }
    }
    out
}

pub fn load_rows(root: &Root) -> Result<Vec<Row>, GateError> {
    let text = crate::io::read_json(&root.durable_path())?;
    parse_rows(&text)
}

pub fn parse_events(text: &str) -> Vec<crate::model::Event> {
    let mut out = Vec::new();
    if let Some(start) = text.find("\"events\":[") {
        let rest = &text[start + 10..];
        if let Some(end) = rest.find(']') {
            let body = &rest[..end];
            for chunk in body.split("},{") {
                let chunk = chunk.trim_matches(&['{', '}', ',', ' '][..]);
                if chunk.is_empty() {
                    continue;
                }
                if let (Ok(tag), Ok(wave), Ok(phase), Ok(slot)) = (
                    read_key(chunk, "tag"),
                    read_key(chunk, "wave"),
                    read_key(chunk, "phase"),
                    read_key(chunk, "slot"),
                ) {
                    out.push(crate::model::Event {
                        tag,
                        wave: wave.parse().unwrap_or(0),
                        phase,
                        slot: slot.parse().unwrap_or(0),
                    });
                }
            }
        }
    }
    out
}

fn parse_rows(text: &str) -> Result<Vec<Row>, GateError> {
    let trimmed = text.trim();
    if !trimmed.starts_with('[') {
        return Err(GateError::new(30, "bad durable"));
    }
    let mut rows = Vec::new();
    for chunk in trimmed.trim_matches(&['[', ']'][..]).split("},{") {
        let chunk = chunk.trim_matches(&['{', '}', ',', ' '][..]);
        if chunk.is_empty() {
            continue;
        }
        rows.push(parse_row(chunk)?);
    }
    Ok(rows)
}

fn parse_row(chunk: &str) -> Result<Row, GateError> {
    let tag = read_key(chunk, "tag")?;
    let lane = read_key(chunk, "lane")?;
    let weight: u32 = read_key(chunk, "weight")?.parse().unwrap_or(0);
    let state = read_key(chunk, "state")?;
    let wave: u32 = read_key(chunk, "wave")?.parse().unwrap_or(0);
    let stash_gen: u32 = read_key(chunk, "stash_gen")
        .unwrap_or_else(|_| wave.to_string())
        .parse()
        .unwrap_or(wave);
    let seed_origin = read_key(chunk, "seed_origin").unwrap_or_else(|_| "true".to_string()) == "true";
    Ok(Row {
        tag,
        lane,
        weight,
        state,
        wave,
        stash_gen,
        seed_origin,
    })
}

fn read_key(chunk: &str, key: &str) -> Result<String, GateError> {
    let needle = format!("\"{key}\":\"");
    if let Some(start) = chunk.find(&needle) {
        let rest = &chunk[start + needle.len()..];
        let end = rest.find('"').unwrap_or(rest.len());
        return Ok(rest[..end].to_string());
    }
    let needle = format!("\"{key}\":");
    if let Some(start) = chunk.find(&needle) {
        let rest = &chunk[start + needle.len()..];
        let end = rest.find(',').unwrap_or(rest.len());
        return Ok(rest[..end].trim().to_string());
    }
    Err(GateError::new(31, format!("missing {key}")))
}
''')

Path('mesh/mesh.rs').write_text(r'''
use crate::model::{Ctx, DispatchObs, RowObs, View};

fn report_row(row: &crate::model::Row) -> String {
    if row.state == "stashed" {
        "wait".to_string()
    } else {
        row.state.clone()
    }
}

pub fn mark_r(ctx: &Ctx) -> View {
    let mut row_obs: Vec<RowObs> = Vec::new();
    for row in &ctx.rows {
        row_obs.push(RowObs {
            tag: row.tag.clone(),
            lane: row.lane.clone(),
            state: report_row(row),
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
''')

Path('src/rebuild.rs').write_text(r'''
use crate::carry::merge_carries;
use crate::errors::GateError;
use crate::fuse::merge_journal;
use crate::model::{Ctx, Mode, Snap};
use crate::ring::fold_n;
use crate::seal::{merge_witness, witness_partial};
use crate::vault::step_p;

pub fn reload_after_cycle(ctx: &mut Ctx, partial: bool, snap: Snap) -> Result<(), GateError> {
    let prior_events = ctx.events.clone();
    ctx.rows = fold_n(ctx, snap.clone())?;
    ctx.gate_open = true;
    ctx.stash_epoch = snap.stash_epoch;
    ctx.seal_epoch = snap.seal_epoch;
    ctx.barrier_gen = snap.barrier_gen;
    ctx.witnesses = merge_witness(&ctx.witnesses, &snap.witnesses);
    ctx.carries = merge_carries(&ctx.carries, &snap.carries);
    let startup = step_p(ctx, Mode::Cycle { partial });
    for ev in startup {
        ctx.slot = ev.slot;
        ctx.events.push(ev);
    }
    if partial {
        witness_partial(ctx);
    }
    ctx.events = merge_journal(&prior_events, &snap.events);
    Ok(())
}
''')

Path('ops/cmd_flush.rs').write_text(r'''
use crate::apply::{accept_stashed, dispatch_waiting};
use crate::checks::validate_root;
use crate::errors::GateError;
use crate::model::{Ctx, Mode};
use crate::prime::step_d;
use crate::render::publish_ctx;
use crate::stow::persist;

pub fn run(ctx: &mut Ctx, again: bool) -> Result<(), GateError> {
    validate_root(&ctx.root)?;
    step_d(ctx)?;
    if !ctx.backing_up {
        return Err(GateError::new(60, "backing down"));
    }
    if again {
        publish_ctx(ctx)?;
        return Ok(());
    }
    accept_stashed(ctx);
    dispatch_waiting(ctx)?;
    publish_ctx(ctx)?;
    persist(ctx, Mode::Sweep { again })?;
    Ok(())
}
''')

Path('src/render.rs').write_text(r'''
use crate::errors::GateError;
use crate::mesh::mark_r;
use crate::model::{Ctx, View};

pub fn write_products(root: &crate::model::Root, view: &View) -> Result<(), GateError> {
    let row_lines: Vec<String> = view.row_obs.iter().map(|r| r.to_json()).collect();
    let dispatch_lines: Vec<String> = view.dispatch_obs.iter().map(|d| d.to_json()).collect();
    crate::io::write_jsonl(&root.row_obs_path(), &row_lines)?;
    crate::io::write_jsonl(&root.dispatch_obs_path(), &dispatch_lines)?;
    Ok(())
}

pub fn publish_ctx(ctx: &Ctx) -> Result<(), GateError> {
    let view = mark_r(ctx);
    write_products(&ctx.root, &view)
}
''')

Path('src/io.rs').write_text(r'''
use std::fs;
use std::path::Path;

use crate::errors::GateError;
use crate::model::Root;

pub fn ensure_state(root: &Root) -> Result<(), GateError> {
    fs::create_dir_all(root.state_dir()).map_err(|e| GateError::new(2, e.to_string()))
}

pub fn read_seed_rows(root: &Root) -> Result<Vec<(String, String, u32)>, GateError> {
    let text = fs::read_to_string(root.seed_file()).map_err(|e| GateError::new(3, e.to_string()))?;
    let mut out = Vec::new();
    for line in text.lines() {
        let line = line.trim();
        if line.is_empty() {
            continue;
        }
        let parts: Vec<&str> = line.split('|').collect();
        if parts.len() != 3 {
            continue;
        }
        let weight: u32 = parts[2].parse().unwrap_or(0);
        out.push((parts[0].to_string(), parts[1].to_string(), weight));
    }
    Ok(out)
}

pub fn write_jsonl(path: &Path, lines: &[String]) -> Result<(), GateError> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).map_err(|e| GateError::new(5, e.to_string()))?;
    }
    let body = if lines.is_empty() {
        String::new()
    } else {
        let mut body = String::new();
        for line in lines {
            body.push_str(line);
            body.push('\n');
        }
        body
    };
    fs::write(path, body).map_err(|e| GateError::new(4, e.to_string()))
}

pub fn write_json(path: &Path, body: &str) -> Result<(), GateError> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).map_err(|e| GateError::new(5, e.to_string()))?;
    }
    fs::write(path, body).map_err(|e| GateError::new(6, e.to_string()))
}

pub fn read_json(path: &Path) -> Result<String, GateError> {
    fs::read_to_string(path).map_err(|e| GateError::new(7, e.to_string()))
}
''')

Path('ops/cmd_rewind.rs').write_text(r'''
use crate::checks::validate_root;
use crate::errors::GateError;
use crate::model::{Ctx, Mode, Snap};
use crate::prime::step_d;
use crate::rebuild::reload_after_cycle;
use crate::render::publish_ctx;
use crate::seal::write_witness_blob;
use crate::span::load_rows;
use crate::stow::persist;

pub fn run(ctx: &mut Ctx, partial: bool) -> Result<(), GateError> {
    validate_root(&ctx.root)?;
    step_d(ctx)?;
    persist(ctx, Mode::Cycle { partial })?;
    let snap = Snap {
        rows: load_rows(&ctx.root)?,
        wave: ctx.wave,
        gate_open: ctx.gate_open,
        backing_up: ctx.backing_up,
        stash_epoch: ctx.stash_epoch,
        seal_epoch: ctx.seal_epoch,
        barrier_gen: ctx.barrier_gen,
        witnesses: ctx.witnesses.clone(),
        carries: ctx.carries.clone(),
        events: ctx.events.clone(),
    };
    reload_after_cycle(ctx, partial, snap)?;
    write_witness_blob(&ctx.root, ctx.seal_epoch, &ctx.witnesses)?;
    publish_ctx(ctx)?;
    persist(ctx, Mode::Cycle { partial })?;
    Ok(())
}
''')

Path('src/stow.rs').write_text(r'''
use crate::errors::GateError;
use crate::model::{CarryKey, Ctx, Mode};
use crate::span::cast_q;

pub fn persist(ctx: &mut Ctx, mode: Mode) -> Result<(), GateError> {
    if let Mode::Offer { tag } = &mode {
        ctx.carries.push(CarryKey {
            tag: tag.to_string(),
            wave: ctx.wave,
            barrier_gen: ctx.seal_epoch,
        });
    }
    if matches!(mode, Mode::Raise) {
        ctx.barrier_gen = if ctx.seal_epoch > 0 {
            ctx.seal_epoch
        } else {
            ctx.stash_epoch
        };
    }
    cast_q(
        &ctx.root,
        &ctx.rows,
        &ctx.events,
        mode,
        ctx.gate_open,
        ctx.backing_up,
        ctx.wave,
        ctx.slot,
        ctx.stash_epoch,
        ctx.seal_epoch,
        ctx.barrier_gen,
        &ctx.witnesses,
        &ctx.carries,
    )
}
''')
PYFIX
CARGO_TARGET_DIR=/tmp/gatectl-build cargo build
