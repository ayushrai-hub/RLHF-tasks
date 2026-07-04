use crate::types::DecodeRow;
use std::fs::{self, File};
use std::io::{BufWriter, Write};
use std::path::Path;

const CRC24Q_POLY: u32 = 0x1864CFB;

pub fn crc24q(data: &[u8]) -> u32 {
    let mut crc = 0u32;
    for &byte in data {
        crc ^= (byte as u32) << 16;
        for _ in 0..8 {
            if crc & 0x800000 != 0 {
                crc = ((crc << 1) ^ CRC24Q_POLY) & 0xFFFFFF;
            } else {
                crc = (crc << 1) & 0xFFFFFF;
            }
        }
    }
    crc
}

fn read_u16_be(data: &[u8], off: usize) -> Option<u16> {
    if off + 2 > data.len() {
        return None;
    }
    Some(u16::from_be_bytes([data[off], data[off + 1]]))
}

fn read_u32_be(data: &[u8], off: usize) -> Option<u32> {
    if off + 4 > data.len() {
        return None;
    }
    Some(u32::from_be_bytes([data[off], data[off + 1], data[off + 2], data[off + 3]]))
}

fn read_u64_be(data: &[u8], off: usize) -> Option<u64> {
    if off + 8 > data.len() {
        return None;
    }
    Some(u64::from_be_bytes([
        data[off],
        data[off + 1],
        data[off + 2],
        data[off + 3],
        data[off + 4],
        data[off + 5],
        data[off + 6],
        data[off + 7],
    ]))
}

fn parse_msm1077(payload: &[u8]) -> Result<DecodeRow, String> {
    if payload.len() < 2 {
        return Err("payload too short".into());
    }
    let msg = read_u16_be(payload, 0).ok_or("missing msg type")?;
    if msg != 1077 {
        return Err(format!("unsupported message type {msg}"));
    }
    let mut off = 2;
    let station_id = read_u16_be(payload, off).ok_or("truncated station_id")?;
    off += 2;
    let mp_len = payload[off] as usize;
    off += 1;
    if off + mp_len > payload.len() {
        return Err("truncated mountpoint".into());
    }
    let mountpoint = String::from_utf8(payload[off..off + mp_len].to_vec())
        .map_err(|_| "invalid mountpoint utf8".to_string())?;
    off += mp_len;
    let sequence = read_u32_be(payload, off).ok_or("truncated sequence")?;
    off += 4;
    let epoch_ms = read_u64_be(payload, off).ok_or("truncated epoch")?;
    off += 8;
    if off >= payload.len() {
        return Err("truncated obs_count".into());
    }
    let obs_count = payload[off] as usize;
    off += 1;

    let mut observable_sum = 0.0f64;
    for _ in 0..obs_count {
        if off + 10 > payload.len() {
            return Err("truncated observable".into());
        }
        let scale_exp = payload[off + 1] as i8;
        let range_raw = read_u32_be(payload, off + 2).ok_or("truncated range")?;
        let divisor = 10f64.powi(scale_exp.max(0) as i32);
        observable_sum += range_raw as f64 / divisor;
        off += 10;
    }

    Ok(DecodeRow {
        station_id,
        mountpoint,
        sequence,
        epoch_ms,
        observable_sum,
        valid: true,
    })
}

pub fn run(capture_path: &str, ledger_path: &str) -> Result<(), String> {
    let data = fs::read(capture_path).map_err(|e| e.to_string())?;
    if let Some(parent) = Path::new(ledger_path).parent() {
        fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    }

    let mut rows: Vec<String> = Vec::new();
    let mut pos = 0usize;
    while pos < data.len() {
        if data[pos] != 0xD3 {
            return Err(format!("bad preamble at offset {pos}"));
        }
        if pos + 3 > data.len() {
            return Err("truncated header".into());
        }
        let length = (((data[pos + 1] & 0x03) as usize) << 8) | (data[pos + 2] as usize);
        let frame_end = pos + 3 + length + 3;
        if frame_end > data.len() {
            return Err("truncated frame".into());
        }
        let payload = &data[pos + 3..pos + 3 + length];
        let crc_bytes = &data[pos + 3 + length..frame_end];
        let expected_crc = ((crc_bytes[0] as u32) << 16)
            | ((crc_bytes[1] as u32) << 8)
            | (crc_bytes[2] as u32);

        let actual_crc = crc24q(&data[pos..pos + 3 + length]);
        if actual_crc != expected_crc {
            return Err(format!("crc mismatch at offset {pos}"));
        }

        let row = parse_msm1077(payload)?;
        rows.push(serde_json::to_string(&row).map_err(|e| e.to_string())?);
        pos = frame_end;
    }

    let mut ledger_writer = BufWriter::new(
        File::create(ledger_path).map_err(|e| e.to_string())?,
    );
    for line in rows {
        writeln!(ledger_writer, "{line}").map_err(|e| e.to_string())?;
    }
    ledger_writer.flush().map_err(|e| e.to_string())?;
    Ok(())
}

pub fn encode_frame(
    station_id: u16,
    mountpoint: &str,
    sequence: u32,
    epoch_ms: u64,
    observables: &[(u8, i8, u32, u32)],
) -> Vec<u8> {
    let mut payload = Vec::new();
    payload.extend_from_slice(&1077u16.to_be_bytes());
    payload.extend_from_slice(&station_id.to_be_bytes());
    let mp = mountpoint.as_bytes();
    payload.push(mp.len() as u8);
    payload.extend_from_slice(mp);
    payload.extend_from_slice(&sequence.to_be_bytes());
    payload.extend_from_slice(&epoch_ms.to_be_bytes());
    payload.push(observables.len() as u8);
    for (sv_id, scale_exp, range_raw, phase_raw) in observables {
        payload.push(*sv_id);
        payload.push(*scale_exp as u8);
        payload.extend_from_slice(&range_raw.to_be_bytes());
        payload.extend_from_slice(&phase_raw.to_be_bytes());
    }

    let len = payload.len();
    let mut frame = Vec::new();
    frame.push(0xD3);
    frame.push(((len >> 8) & 0x03) as u8);
    frame.push((len & 0xFF) as u8);
    frame.extend_from_slice(&payload);
    let crc = crc24q(&frame);
    frame.push(((crc >> 16) & 0xFF) as u8);
    frame.push(((crc >> 8) & 0xFF) as u8);
    frame.push((crc & 0xFF) as u8);
    frame
}
