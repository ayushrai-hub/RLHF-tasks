use crate::errors::Err;
use crate::model::{Ctx, ReplayRow};

pub fn hydrate(ctx: &mut Ctx) -> Result<(), Err> {
    ctx.replay.clear();
    let path = ctx.root.state_dir().join("material.bin");
    if !path.is_file() {
        return Ok(());
    }
    let raw = std::fs::read(&path).map_err(|e| Err::new(80, e.to_string()))?;
    if raw.len() < 7 || &raw[0..4] != b"ZNMT" {
        return Ok(());
    }
    let count = u16::from_le_bytes([raw[5], raw[6]]) as usize;
    let mut off = 7usize;
    for _ in 0..count {
        if off >= raw.len() {
            break;
        }
        let id_len = raw[off] as usize;
        off += 1;
        if off + id_len + 16 > raw.len() {
            break;
        }
        let key = String::from_utf8_lossy(&raw[off..off + id_len]).to_string();
        off += id_len;
        let pkt = u64::from_le_bytes(raw[off..off + 8].try_into().unwrap());
        off += 8;
        let byte = u64::from_le_bytes(raw[off..off + 8].try_into().unwrap());
        off += 8;
        let body_len = raw[off] as usize;
        off += 1;
        if off + body_len > raw.len() {
            break;
        }
        let body = String::from_utf8_lossy(&raw[off..off + body_len]).to_string();
        off += body_len;
        let anchor = String::new();
        ctx.replay.insert(
            key,
            ReplayRow {
                pkt,
                byte,
                body,
                anchor,
            },
        );
    }
    Ok(())
}
