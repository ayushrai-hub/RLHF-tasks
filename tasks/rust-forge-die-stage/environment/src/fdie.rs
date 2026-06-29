use std::fs;
use std::path::Path;

const MAGIC_V1: &[u8; 4] = b"FDIE";
const MAGIC_V2: &[u8; 4] = b"FD2E";
const MAGIC_V3: &[u8; 4] = b"FD3E";

pub fn payload_checksum(data: &[u8]) -> u32 {
    data.iter().fold(0u32, |acc, b| acc.wrapping_add(*b as u32))
}

#[derive(Debug, Clone)]
pub struct FdiePayload {
    pub die_id: String,
    pub tonnage: u64,
    pub source_format: String,
    pub revision: Option<u64>,
    pub digest_hex: String,
}

pub fn parse_v1_payload(text: &str) -> Result<FdiePayload, String> {
    let (die_id, tonnage_raw) = text
        .split_once('|')
        .ok_or_else(|| "fdie payload missing tonnage separator".to_string())?;
    if die_id.is_empty() {
        return Err("fdie payload missing die id".into());
    }
    let tonnage = tonnage_raw
        .parse::<u64>()
        .map_err(|e| format!("invalid tonnage: {e}"))?;
    Ok(FdiePayload {
        die_id: die_id.to_string(),
        tonnage,
        source_format: "v1".into(),
        revision: None,
        digest_hex: String::new(),
    })
}

pub fn read_fdie_block(path: &Path) -> Result<(FdiePayload, u32), String> {
    let bytes = fs::read(path).map_err(|e| e.to_string())?;
    if bytes.len() < 8 {
        return Err("fdie block too short".into());
    }
    if &bytes[0..4] == MAGIC_V1 {
        read_fdie_v1(&bytes, path)
    } else if &bytes[0..4] == MAGIC_V2 {
        read_fdie_v2(&bytes, path)
    } else if &bytes[0..4] == MAGIC_V3 {
        read_fdie_v3(&bytes, path)
    } else {
        Err("bad fdie magic".into())
    }
}

fn read_fdie_v1(bytes: &[u8], path: &Path) -> Result<(FdiePayload, u32), String> {
    let len = u32::from_le_bytes(bytes[4..8].try_into().unwrap()) as usize;
    if bytes.len() < 8 + len + 4 {
        return Err("fdie block truncated".into());
    }
    let payload = &bytes[8..8 + len];
    let stored = u32::from_le_bytes(bytes[8 + len..8 + len + 4].try_into().unwrap());
    let expected = payload_checksum(payload);
    if stored != expected {
        return Err(format!(
            "checksum mismatch for {}: stored={stored} expected={expected}",
            path.display()
        ));
    }
    let text = String::from_utf8(payload.to_vec()).map_err(|e| e.to_string())?;
    let mut parsed = parse_v1_payload(&text)?;
    parsed.digest_hex = format!("{expected:08x}");
    Ok((parsed, expected))
}

fn read_fdie_v2(bytes: &[u8], path: &Path) -> Result<(FdiePayload, u32), String> {
    if bytes.len() < 10 {
        return Err("fdie v2 block truncated".into());
    }
    let header_len = u16::from_le_bytes(bytes[4..6].try_into().unwrap()) as usize;
    if bytes.len() < 6 + header_len + 4 {
        return Err("fdie v2 block truncated".into());
    }
    let header = &bytes[6..6 + header_len];
    let payload_len = u32::from_le_bytes(bytes[6 + header_len..6 + header_len + 4].try_into().unwrap())
        as usize;
    if bytes.len() < 6 + header_len + 4 + payload_len + 4 {
        return Err("fdie v2 block truncated".into());
    }
    let payload = &bytes[6 + header_len + 4..6 + header_len + 4 + payload_len];
    let stored = u32::from_le_bytes(
        bytes[6 + header_len + 4 + payload_len..6 + header_len + 4 + payload_len + 4]
            .try_into()
            .unwrap(),
    );
    let mut checksum_input = Vec::new();
    checksum_input.extend_from_slice(header);
    checksum_input.extend_from_slice(&(payload_len as u32).to_le_bytes());
    checksum_input.extend_from_slice(payload);
    let expected = payload_checksum(&checksum_input);
    if stored != expected {
        return Err(format!(
            "checksum mismatch for {}: stored={stored} expected={expected}",
            path.display()
        ));
    }
    let header_json: serde_json::Value =
        serde_json::from_slice(header).map_err(|e| format!("invalid v2 header: {e}"))?;
    let payload_json: serde_json::Value =
        serde_json::from_slice(payload).map_err(|e| format!("invalid v2 payload: {e}"))?;
    let die_id = header_json
        .get("die_id")
        .and_then(|v| v.as_str())
        .ok_or_else(|| "v2 header missing die_id".to_string())?
        .to_string();
    let nominal = header_json
        .get("nominal_tonnage")
        .and_then(|v| v.as_i64())
        .ok_or_else(|| "v2 header missing nominal_tonnage".to_string())?;
    if nominal < 0 {
        return Err("negative tonnage".into());
    }
    let revision = header_json.get("revision").and_then(|v| v.as_u64());
    let measured = payload_json.get("measured_tonnage").and_then(|v| v.as_i64());
    if let Some(m) = measured {
        if m < 0 {
            return Err("negative tonnage".into());
        }
    }
    let tonnage = measured.unwrap_or(nominal) as u64;
    Ok((
        FdiePayload {
            die_id,
            tonnage,
            source_format: "v2".into(),
            revision,
            digest_hex: format!("{expected:08x}"),
        },
        expected,
    ))
}

fn read_fdie_v3(bytes: &[u8], path: &Path) -> Result<(FdiePayload, u32), String> {
    if bytes.len() < 8 {
        return Err("fdie v3 block truncated".into());
    }
    let header_len = u16::from_le_bytes(bytes[4..6].try_into().unwrap()) as usize;
    let header = &bytes[6..6 + header_len];
    let mut offset = 6 + header_len;
    if bytes.len() < offset + 2 {
        return Err("fdie v3 block truncated".into());
    }
    let chunk_count = u16::from_le_bytes(bytes[offset..offset + 2].try_into().unwrap()) as usize;
    offset += 2;
    let mut digest_input = Vec::new();
    digest_input.extend_from_slice(header);
    digest_input.extend_from_slice(&(chunk_count as u16).to_le_bytes());
    let mut chunk_payload = Vec::new();
    for _ in 0..chunk_count {
        if bytes.len() < offset + 4 {
            return Err("fdie v3 block truncated".into());
        }
        let chunk_len = u32::from_le_bytes(bytes[offset..offset + 4].try_into().unwrap()) as usize;
        offset += 4;
        if bytes.len() < offset + chunk_len {
            return Err("fdie v3 block truncated".into());
        }
        let chunk = &bytes[offset..offset + chunk_len];
        digest_input.extend_from_slice(chunk);
        chunk_payload.extend_from_slice(chunk);
        offset += chunk_len;
    }
    if bytes.len() < offset + 32 {
        return Err("fdie v3 block truncated".into());
    }
    let stored = &bytes[offset..offset + 32];
    let expected = crate::digest::sha256_hex(&digest_input);
    let expected_bytes = hex::decode(&expected).map_err(|e| e.to_string())?;
    if stored != expected_bytes.as_slice() {
        return Err(format!("footer digest mismatch for {}", path.display()));
    }
    let header_json: serde_json::Value =
        serde_json::from_slice(header).map_err(|e| format!("invalid v3 header: {e}"))?;
    let payload_json: serde_json::Value = serde_json::from_slice(&chunk_payload)
        .map_err(|e| format!("invalid v3 payload: {e}"))?;
    let die_id = header_json
        .get("die_id")
        .and_then(|v| v.as_str())
        .ok_or_else(|| "v3 header missing die_id".to_string())?
        .to_string();
    let nominal = header_json
        .get("nominal_tonnage")
        .and_then(|v| v.as_i64())
        .ok_or_else(|| "v3 header missing nominal_tonnage".to_string())?;
    let scale_milli = header_json
        .get("scale_milli")
        .and_then(|v| v.as_i64())
        .unwrap_or(1000);
    let revision = header_json.get("revision").and_then(|v| v.as_u64());
    let measured = payload_json.get("measured_tonnage").and_then(|v| v.as_i64());
    let delta = payload_json
        .get("tonnage_delta")
        .and_then(|v| v.as_i64())
        .unwrap_or(0);
    let base = measured.unwrap_or(nominal + delta);
    if base < 0 {
        return Err("negative tonnage".into());
    }
    let tonnage = ((base / 1000) * scale_milli) as u64;
    let checksum = u32::from_le_bytes(expected_bytes[0..4].try_into().unwrap());
    Ok((
        FdiePayload {
            die_id,
            tonnage,
            source_format: "v3".into(),
            revision,
            digest_hex: expected,
        },
        checksum,
    ))
}

pub fn die_path(data_root: &str, die_id: &str) -> String {
    format!("{data_root}/{die_id}.bin")
}

mod hex {
    pub fn decode(s: &str) -> Result<Vec<u8>, String> {
        if s.len() % 2 != 0 {
            return Err("invalid hex".into());
        }
        (0..s.len())
            .step_by(2)
            .map(|i| u8::from_str_radix(&s[i..i + 2], 16).map_err(|e| e.to_string()))
            .collect()
    }
}
