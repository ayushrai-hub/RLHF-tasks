use std::fs;
use std::io::Write;
use std::path::Path;

use crate::errors::Err;
use crate::model::Row;

pub fn ensure_dir(p: &Path) -> Result<(), Err> {
    fs::create_dir_all(p).map_err(|e| Err::new(10, e.to_string()))
}

pub fn clear_jsonl(p: &Path) -> Result<(), Err> {
    if p.exists() {
        fs::remove_file(p).map_err(|e| Err::new(11, e.to_string()))?;
    }
    Ok(())
}

pub fn append_jsonl(p: &Path, lines: &[String]) -> Result<(), Err> {
    let mut f = fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(p)
        .map_err(|e| Err::new(12, e.to_string()))?;
    for line in lines {
        writeln!(f, "{line}").map_err(|e| Err::new(13, e.to_string()))?;
    }
    Ok(())
}

pub fn read_scope_seed(path: &Path) -> Result<Vec<Row>, Err> {
    let raw = fs::read(path).map_err(|e| Err::new(20, e.to_string()))?;
    if raw.len() < 7 || &raw[0..4] != b"ZNLD" {
        return Err(Err::new(21, "bad scope seed magic"));
    }
    let count = u16::from_le_bytes([raw[5], raw[6]]) as usize;
    let mut off = 7usize;
    let mut out = Vec::new();
    for lane in 0..count {
        if off >= raw.len() {
            break;
        }
        let id_len = raw[off] as usize;
        off += 1;
        if off + id_len + 16 > raw.len() {
            return Err(Err::new(22, "truncated scope seed"));
        }
        let key = String::from_utf8_lossy(&raw[off..off + id_len]).to_string();
        off += id_len;
        let pkt = u64::from_le_bytes(raw[off..off + 8].try_into().unwrap());
        off += 8;
        let byte = u64::from_le_bytes(raw[off..off + 8].try_into().unwrap());
        off += 8;
        out.push(Row {
            key,
            mark: String::new(),
            holder: String::new(),
            rtype: String::new(),
            klass: String::new(),
            ttl: 0,
            rdata: String::new(),
            body: String::new(),
            pkt,
            byte,
            lane: lane as u32,
            visit_ord: 0,
            anchor: "scope".to_string(),
            src_rel: "scope".to_string(),
        });
    }
    Ok(out)
}

pub fn write_blob(path: &Path, data: &[u8]) -> Result<(), Err> {
    fs::write(path, data).map_err(|e| Err::new(30, e.to_string()))
}

pub fn read_text(path: &Path) -> Result<String, Err> {
    fs::read_to_string(path).map_err(|e| Err::new(31, e.to_string()))
}

pub fn copy_tree(src: &Path, dst: &Path) -> Result<(), Err> {
    if !src.is_dir() {
        return Err(Err::new(32, "missing fixture tree"));
    }
    if dst.exists() {
        fs::remove_dir_all(dst).map_err(|e| Err::new(33, e.to_string()))?;
    }
    copy_rec(src, dst)
}

fn copy_rec(src: &Path, dst: &Path) -> Result<(), Err> {
    ensure_dir(dst)?;
    for ent in fs::read_dir(src).map_err(|e| Err::new(34, e.to_string()))? {
        let ent = ent.map_err(|e| Err::new(35, e.to_string()))?;
        let ty = ent.file_type().map_err(|e| Err::new(36, e.to_string()))?;
        let name = ent.file_name();
        let to = dst.join(name);
        if ty.is_dir() {
            copy_rec(&ent.path(), &to)?;
        } else {
            fs::copy(ent.path(), &to).map_err(|e| Err::new(37, e.to_string()))?;
        }
    }
    Ok(())
}

pub fn write_text(path: &Path, text: &str) -> Result<(), Err> {
    fs::write(path, text).map_err(|e| Err::new(38, e.to_string()))
}
