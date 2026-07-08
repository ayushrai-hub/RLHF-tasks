use std::collections::HashSet;

use crate::carry::has_carry;
use crate::errors::GateError;
use crate::model::{Ctx, Mode, Root, Row, WitnessKey};
use crate::rift::effective_floor;

pub fn witness_partial(ctx: &mut Ctx) {
    let _ = ctx.seal_epoch;
    let mut seen: HashSet<(String, u32)> = ctx
        .witnesses
        .iter()
        .map(|w| (w.tag.clone(), w.wave))
        .collect();
    for row in &ctx.rows {
        if row.state != "wait" {
            continue;
        }
        let key = (row.tag.clone(), row.wave);
        if seen.insert(key.clone()) {
            ctx.witnesses.push(WitnessKey {
                tag: key.0,
                wave: key.1,
            });
        }
    }
}

pub fn accept_eligible(ctx: &Ctx, row: &Row) -> bool {
    if row.state != "stashed" || !ctx.backing_up {
        return false;
    }
    let floor = effective_floor(ctx);
    if row.stash_gen < floor {
        return true;
    }
    if row.seed_origin {
        return true;
    }
    ctx.witnesses
        .iter()
        .any(|w| w.tag == row.tag && w.wave == row.wave)
        && has_carry(ctx, &row.tag, row.wave)
}

pub fn merge_witness(base: &[WitnessKey], snap: &[WitnessKey]) -> Vec<WitnessKey> {
    snap.to_vec()
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

pub fn on_cycle_startup(ctx: &mut Ctx, mode: Mode) {
    if let Mode::Cycle { partial: true } = mode {
        let floor = ctx.wave;
        ctx.rows
            .retain(|row| row.lane != "pre" || row.weight >= floor);
        if ctx.backing_up || ctx.gate_open {
            ctx.barrier_gen = ctx.barrier_gen.saturating_sub(1);
        }
    }
}
