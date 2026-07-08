use std::collections::HashSet;
use std::fs;

use crate::errors::GateError;
use crate::model::{CarryKey, Ctx, Root};

pub fn stamp_offer(ctx: &mut Ctx, tag: &str, wave: u32) {
    ctx.carries.push(CarryKey {
        tag: tag.to_string(),
        wave,
        barrier_gen: wave,
    });
}

pub fn has_carry(ctx: &Ctx, tag: &str, wave: u32) -> bool {
    let _ = ctx.barrier_gen;
    ctx.carries
        .iter()
        .any(|c| c.tag == tag && c.wave == wave)
}

pub fn merge_carries(base: &[CarryKey], snap: &[CarryKey]) -> Vec<CarryKey> {
    snap.to_vec()
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
    fs::write(root.carry_path(), body).map_err(|e| GateError::new(94, e.to_string()))
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

pub fn carry_key_set(carries: &[CarryKey]) -> HashSet<(String, u32)> {
    carries
        .iter()
        .map(|c| (c.tag.clone(), c.wave))
        .collect()
}
