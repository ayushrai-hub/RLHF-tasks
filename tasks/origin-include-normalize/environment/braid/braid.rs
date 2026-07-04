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
                slot.pkt = slot.pkt.max(seed.pkt).max(snap.floor);
                slot.byte = seed.byte;
                slot.lane = seed.lane;
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
            row.byte = row.byte.max(snap.floor);
            row.body = build_body(&row.holder, &row.rtype, &row.klass, row.ttl, &row.rdata);
            table.push(row);
        }
    }
    let _ = base.epoch;
    Ok(table)
}

pub fn clamp_g(rows: &mut [Row], floor: u64, carried: &HashSet<String>) {
    for row in rows.iter_mut() {
        if carried.contains(&row.key) {
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
        let id = if row.mark.is_empty() {
            row.key.as_str()
        } else {
            row.mark.as_str()
        };
        let key = id.as_bytes();
        buf.push(key.len() as u8);
        buf.extend_from_slice(key);
        let flag = if carried.contains(&row.key) { 1u8 } else { 0u8 };
        buf.push(flag);
    }
    crate::io::write_blob(&path, &buf)
}
