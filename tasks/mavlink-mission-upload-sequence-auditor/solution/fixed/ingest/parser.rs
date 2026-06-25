use crate::crc::{footer_crc_input, waypoint_crc_input, x25_crc};
use crate::domain::{Footer, Waypoint};

const MAGIC: [u8; 2] = [0x4d, 0x51];
const TYPE_WAYPOINT: u8 = 0x01;
const TYPE_FOOTER: u8 = 0xfe;

pub fn parse_log(raw: &[u8]) -> Result<(Vec<Waypoint>, Footer), String> {
    let mut i = 0usize;
    let mut waypoints = Vec::new();
    let mut footer: Option<Footer> = None;

    while i < raw.len() {
        if i + 2 <= raw.len() && raw[i..i + 2] == MAGIC {
            if i + 4 > raw.len() {
                return Err("truncated record".into());
            }
            let version = raw[i + 2];
            let record_type = raw[i + 3];
            if version != 1 {
                return Err("unsupported version".into());
            }
            if record_type == TYPE_WAYPOINT {
                let wp = parse_waypoint(&raw[i..])?;
                let step = waypoint_record_len(&wp.upload_id);
                waypoints.push(wp);
                i += step;
            } else if record_type == TYPE_FOOTER {
                footer = Some(parse_footer(&raw[i..])?);
                break;
            } else {
                return Err(format!("unknown record type {record_type}"));
            }
        } else {
            i += 1;
        }
    }

    let foot = footer.ok_or_else(|| "missing footer".to_string())?;
    Ok((waypoints, foot))
}

fn waypoint_record_len(upload_id: &str) -> usize {
    2 + 1 + 1 + 1 + upload_id.len() + 2 + 4 + 4 + 4 + 1 + 1 + 2
}

fn parse_waypoint(raw: &[u8]) -> Result<Waypoint, String> {
    if raw.len() < 10 {
        return Err("short waypoint".into());
    }
    let version = raw[2];
    let record_type = raw[3];
    let id_len = raw[4] as usize;
    if raw.len() < 5 + id_len + 16 {
        return Err("short waypoint payload".into());
    }
    let upload_id = std::str::from_utf8(&raw[5..5 + id_len])
        .map_err(|_| "invalid upload_id".to_string())?
        .to_string();
    let mut off = 5 + id_len;
    let seq = u16::from_be_bytes([raw[off], raw[off + 1]]);
    off += 2;
    let lat_e7 = i32::from_be_bytes([raw[off], raw[off + 1], raw[off + 2], raw[off + 3]]);
    off += 4;
    let lon_e7 = i32::from_be_bytes([raw[off], raw[off + 1], raw[off + 2], raw[off + 3]]);
    off += 4;
    let alt_mm = i32::from_be_bytes([raw[off], raw[off + 1], raw[off + 2], raw[off + 3]]);
    off += 4;
    let frame = raw[off];
    let flags = raw[off + 1];
    off += 2;
    let crc = u16::from_be_bytes([raw[off], raw[off + 1]]);

    let body = waypoint_crc_input(
        version,
        record_type,
        upload_id.as_bytes(),
        seq,
        lat_e7,
        lon_e7,
        alt_mm,
        frame,
        flags,
    );
    let extra = if flags & 0x01 != 0 { Some(0x4d) } else { None };
    if x25_crc(&body, extra) != crc {
        return Err("waypoint crc mismatch".into());
    }

    Ok(Waypoint {
        upload_id,
        seq,
        lat_e7,
        lon_e7,
        alt_mm,
        frame,
        flags,
    })
}

fn parse_footer(raw: &[u8]) -> Result<Footer, String> {
    if raw.len() < 8 {
        return Err("short footer".into());
    }
    let version = raw[2];
    let record_type = raw[3];
    let id_len = raw[4] as usize;
    if raw.len() < 5 + id_len + 4 {
        return Err("short footer payload".into());
    }
    let upload_id = std::str::from_utf8(&raw[5..5 + id_len])
        .map_err(|_| "invalid footer upload_id".to_string())?
        .to_string();
    let mut off = 5 + id_len;
    let expected_count = u16::from_be_bytes([raw[off], raw[off + 1]]);
    off += 2;
    let crc = u16::from_be_bytes([raw[off], raw[off + 1]]);

    let body = footer_crc_input(version, record_type, upload_id.as_bytes(), expected_count);
    if x25_crc(&body, None) != crc {
        return Err("footer crc mismatch".into());
    }

    Ok(Footer {
        upload_id,
        expected_count,
    })
}
