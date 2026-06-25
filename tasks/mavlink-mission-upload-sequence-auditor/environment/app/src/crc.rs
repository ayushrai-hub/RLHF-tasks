fn crc_accumulate(data: u8, crc: u16) -> u16 {
    let mut tmp = (data as u16) ^ (crc & 0x00ff);
    tmp = (tmp ^ (tmp << 4)) & 0x00ff;
    (crc >> 8) ^ (tmp << 8) ^ (tmp << 3) ^ (tmp >> 4)
}

pub fn x25_crc(data: &[u8], crc_extra: Option<u8>) -> u16 {
    let mut crc = 0xffffu16;
    for &b in data {
        crc = crc_accumulate(b, crc);
    }
    if let Some(extra) = crc_extra {
        crc = crc_accumulate(extra, crc);
    }
    crc
}

pub fn waypoint_crc_input(
    version: u8,
    record_type: u8,
    upload_id: &[u8],
    seq: u16,
    lat_e7: i32,
    lon_e7: i32,
    alt_mm: i32,
    frame: u8,
    flags: u8,
) -> Vec<u8> {
    let mut body = Vec::new();
    body.push(version);
    body.push(record_type);
    body.push(upload_id.len() as u8);
    body.extend_from_slice(upload_id);
    body.extend_from_slice(&seq.to_be_bytes());
    body.extend_from_slice(&lat_e7.to_be_bytes());
    body.extend_from_slice(&lon_e7.to_be_bytes());
    body.extend_from_slice(&alt_mm.to_be_bytes());
    body.push(frame);
    body.push(flags);
    body
}

pub fn footer_crc_input(
    version: u8,
    record_type: u8,
    upload_id: &[u8],
    expected_count: u16,
) -> Vec<u8> {
    let mut body = Vec::new();
    body.push(version);
    body.push(record_type);
    body.push(upload_id.len() as u8);
    body.extend_from_slice(upload_id);
    body.extend_from_slice(&expected_count.to_be_bytes());
    body
}
